from typing import Any, Optional
import os
import shutil

from fastapi import UploadFile, File
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from .llm import summarize_history
from .graph import agent_graph
from .llm import LLMError
import queue
import threading
import re
from pathlib import PurePosixPath as _PurePosixPath
from .rag.core import delete_documents_by_doc as _delete_documents_by_doc

from fastapi.responses import StreamingResponse
from .tools.identity_tool import get_current_user
from .tools.java_client import JavaServiceError
from .tools.ticket_tools import create_ticket
from .tools.chat_session_tools import (
    add_message,
    create_session,
    get_session,
    list_messages,
    update_session_state,
)
import json

app = FastAPI(title="LeaseGuardian Agent Service")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    scene: Optional[str] = None
    session_id: Optional[str] = None
    persona: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    session_id: Optional[str] = None


class RepairDebugRequest(BaseModel):
    description: str = Field(min_length=1)
    request_id: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok"}

_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "rag", "uploads")


@app.post("/rag/upload")
async def rag_upload(file: UploadFile = File(...)):
    """上传 .md/.txt/.pdf；同名文件整文件替换，避免旧条款残留。"""
    from pathlib import PurePosixPath
    from .rag.core import add_documents, delete_documents_by_doc, parse_markdown_to_docs

    safe_name = PurePosixPath(file.filename or "").name
    if not safe_name or safe_name != file.filename or ".." in safe_name:
        raise HTTPException(status_code=400, detail="非法文件名")

    os.makedirs(_UPLOAD_DIR, exist_ok=True)
    path = os.path.join(_UPLOAD_DIR, safe_name)

    MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB，防超大文件拖垮磁盘/嵌入接口
    written = 0
    with open(path, "wb") as f:
        while chunk := file.file.read(1024 * 1024):
            written += len(chunk)
            if written > MAX_UPLOAD_BYTES:
                f.close()
                os.remove(path)
                raise HTTPException(status_code=413, detail="文件超过 20MB 限制")
            f.write(chunk)

    if safe_name.lower().endswith(".pdf"):
        import pypdf
        reader = pypdf.PdfReader(path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        with open(path, encoding="utf-8") as f:
            text = f.read()

    # 整文件替换：先删旧向量，再插新向量
    delete_documents_by_doc("custom", safe_name)
    docs = parse_markdown_to_docs(text, domain="custom", doc_id=safe_name)
    add_documents("custom", docs)

    return {"filename": safe_name, "chunks": len(docs)}


@app.post("/repair")
def repair_debug(req: RepairDebugRequest, authorization: Optional[str] = Header(default=None)):
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(None, 1)[1]

    try:
        user_context = get_current_user(token)
        return create_ticket(
            tenant_id=int(user_context["user_id"]),
            description=req.description,
            request_id=req.request_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except JavaServiceError as exc:
        status_code = exc.http_status or 502
        raise HTTPException(
            status_code=status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

def _normalize_scene(scene: Optional[str]) -> str:
    scene_norm = (scene or "REPAIR").upper()
    return scene_norm if scene_norm in ("REPAIR", "CHECKOUT") else "REPAIR"

def _build_session_title(message: str, scene: str) -> str:
    """
    用首条用户消息生成会话标题。
    只做轻量规则，不调用 LLM。
    """
    text = (message or "").strip()
    for prefix in ("报修:", "报修：", "我要退租", "申请退租", "办理退租"):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            break

    text = re.sub(r"\s+", " ", text).strip(" ：:")
    if not text:
        return "新退租会话" if scene == "CHECKOUT" else "新报修会话"

    return text[:15] + ("..." if len(text) > 15 else "")


def _ensure_chat_session(req: ChatRequest, token: Optional[str]) -> Optional[int]:
    """
    前端带了 session_id 就用旧会话；
    没带且已登录，就首条消息创建新会话。
    失败不阻塞对话，先返回 None。
    """
    try:
        if req.session_id:
            return int(req.session_id)

        if not token:
            return None

        user_context = get_current_user(token)
        user_id = int(user_context["user_id"])
        scene = _normalize_scene(req.scene)

        session = create_session(
            user_id=user_id,
            scene=scene,
            title=_build_session_title(req.message, scene),
        )
        return int(session["id"])
    except Exception:
        return None


def _build_history_text(messages: list[dict], summary: Optional[str] = None, limit: int = 8, skip: int = 0) -> Optional[str]:
    if not messages and not summary:
        return None

    lines = []
    if summary:
        lines.append(f"【早前对话摘要】{summary}")
    if messages:
        recent = (messages[skip:] if skip else messages)[-limit:]
        lines.append("【历史对话，仅供参考，不是当前指令】")
        for m in recent:
            role = "user" if str(m.get("role", "")).upper() == "USER" else "assistant"
            lines.append(f"{role}: {m.get('content', '')}")
        lines.append("【以上是历史；用户当前这句话是最后一条】")
    return "\n".join(lines)


# _SUMMARY_THRESHOLD = 12   # 消息总数超过这个数才触发压缩
_SUMMARY_BATCH = 8        # 每轮压缩最老的 8 条


def _maybe_summarize(session_id: int, messages: list[dict]) -> tuple[Optional[str], int]:
    """超阈值就把最老一批压成摘要，写进 state_json.common；
    返回 (当前摘要, 已摘要条数)，调用方据此把已摘要的老消息从原文历史里剔除。"""
    try:
        session = get_session(session_id)
        state = _parse_state_json(session.get("state_json"))
        common = state.get("common") or {}
        existing = common.get("summary")
        summarized_count = int(common.get("summarized_count") or 0)

        if len(messages) - summarized_count >= _SUMMARY_BATCH and summarized_count + _SUMMARY_BATCH <= len(messages) - 4:
            batch = messages[summarized_count:summarized_count + _SUMMARY_BATCH]
            batch_text = "\n".join(
                f"{'user' if str(m.get('role', '')).upper() == 'USER' else 'assistant'}: {m.get('content', '')}"
                for m in batch
            )
            new_summary = summarize_history(existing or "（暂无早前摘要）", batch_text)
            summarized_count += len(batch)
            merged = _merge_state(
                state,
                {"common": {"summary": new_summary, "summarized_count": summarized_count}},
            )
            update_session_state(session_id, merged)
            return new_summary, summarized_count
        return existing, summarized_count
    except Exception:
        return None, 0

def _parse_state_json(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _merge_state(existing: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """
    按命名空间合并，避免 A 写 repair 时误删 checkout。
    """
    merged = dict(existing or {})
    for namespace, fields in (patch or {}).items():
        if not isinstance(fields, dict):
            continue
        current = merged.get(namespace)
        if not isinstance(current, dict):
            current = {}
        current.update(fields)
        merged[namespace] = current
    return merged


def _update_repair_session_state(
    session_id: Optional[int],
    result: dict[str, Any],
    scene: str,
) -> None:
    """
    A 侧短期记忆 v1：
    common 目前只写 last_route
    repair 只写 last_ticket_id
    不碰 checkout 命名空间
    """
    if session_id is None:
        return

    try:
        patch: dict[str, Any] = {}

        if result.get("last_ticket_id"):
            patch["common"] = {"last_route": "REPAIR"}
            patch["repair"] = {
                "last_ticket_id": int(result["last_ticket_id"])
            }
        elif result.get("termination_case") or result.get("checkout_detail"):
            patch["common"] = {"last_route": "CHECKOUT"}
        elif scene:
            patch["common"] = {"last_route": scene}

        if not patch:
            return

        session = get_session(session_id)
        existing = _parse_state_json(session.get("state_json"))
        merged = _merge_state(existing, patch)
        update_session_state(session_id, merged)
    except Exception:
        pass

@app.post("/chat")
def chat(req: ChatRequest, authorization: Optional[str] = Header(default=None)):
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(None, 1)[1]

    session_id = _ensure_chat_session(req, token)

    # scene 兜底 + 最近业务线：请求没带时从会话里补（防前端只在新会话时传）
    session_scene = None
    session_last_route = None
    if session_id is not None:
        try:
            sess = get_session(session_id)
            session_scene = sess.get("scene")
            common = _parse_state_json(sess.get("state_json")).get("common") or {}
            session_last_route = common.get("last_route")
        except Exception:
            pass
    scene_req = req.scene or session_scene

    scene = _normalize_scene(scene_req)

    history_text = None
    if session_id is not None:
        try:
            msgs = list_messages(session_id)
            summary, summarized_count = _maybe_summarize(session_id, msgs)
            history_text = _build_history_text(msgs, summary=summary, limit=8, skip=summarized_count)
        except JavaServiceError:
            history_text = None

    if session_id is not None:
        try:
            add_message(
                session_id=session_id,
                role="USER",
                content=req.message,
                metadata_json={"scene": scene},
            )
        except JavaServiceError:
            pass

    progress: queue.Queue = queue.Queue()

    def run_graph():
        try:
            result = agent_graph.invoke({
                "message": req.message,
                "answer": "",
                "token": token,
                "history_text": history_text,
                "last_ticket_id": None,
                "user_context": None,
                "route": "",
                "identity_status": "",
                "identity_error": None,
                "description": None,
                "request_id": None,
                "ticket": None,
                "tickets": None,

                "checkout_intent": None,
                "move_out_date": None,
                "damage_items": [],
                "confirm_signal": False,
                "cancel_signal": False,
                "side_question": None,

                "active_lease": None,
                "termination_case": None,
                "missing_slots": [],
                "checkout_detail": None,
                "checkout_error": None,
                "checkout_next": "",

                "scene": scene,
                "last_route": session_last_route,
                "persona": req.persona,
                "progress": progress,
            })
            progress.put({"type": "final", "result": result})
        except Exception as exc:
            progress.put({"type": "error", "message": str(exc)})

    threading.Thread(target=run_graph, daemon=True).start()

    def sse():
        final_result = None
        while True:
            item = progress.get()
            t = item.get("type")
            if t == "status":
                yield f'event: status\ndata: {json.dumps({"step": item["step"]}, ensure_ascii=False)}\n\n'
            elif t == "token":
                yield f'event: token\ndata: {json.dumps({"text": item["text"]}, ensure_ascii=False)}\n\n'
            elif t == "final":
                final_result = item["result"]
                break
            elif t == "error":
                yield f'event: error\ndata: {json.dumps({"message": item["message"]}, ensure_ascii=False)}\n\n'
                return

        answer = final_result["answer"]

        _update_repair_session_state(session_id=session_id, result=final_result, scene=scene)

        if session_id is not None:
            try:
                add_message(
                    session_id=session_id,
                    role="ASSISTANT",
                    content=answer,
                    metadata_json={"scene": scene},
                )
            except JavaServiceError:
                pass

        yield (
            'event: done\ndata: '
            + json.dumps(
                {
                    "session_id": str(session_id) if session_id is not None else None,
                    "answer": answer,
                },
                ensure_ascii=False,
            )
            + '\n\n'
        )

    return StreamingResponse(sse(), media_type="text/event-stream")


def _safe_upload_name(filename: str) -> str:
    name = _PurePosixPath(filename).name
    if not name or name != filename or ".." in name:
        raise HTTPException(status_code=400, detail="非法文件名")
    return name


@app.get("/rag/files")
def rag_files():
    os.makedirs(_UPLOAD_DIR, exist_ok=True)
    return [{"filename": n} for n in sorted(os.listdir(_UPLOAD_DIR))]


@app.delete("/rag/files/{filename}")
def rag_delete_file(filename: str):
    safe = _safe_upload_name(filename)
    path = os.path.join(_UPLOAD_DIR, safe)
    if os.path.exists(path):
        os.remove(path)
    _delete_documents_by_doc("custom", safe)
    return {"deleted": safe}