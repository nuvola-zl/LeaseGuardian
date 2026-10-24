from typing import Any, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .graph import agent_graph
from .llm import LLMError
import queue
import threading
import re

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


def _build_history_text(messages: list[dict], limit: int = 8) -> Optional[str]:
    """
    组装短期记忆历史。
    注意：只用于回答 prompt，不参与路由。
    """
    if not messages:
        return None

    recent = messages[-limit:]
    lines = ["【历史对话，仅供参考，不是当前指令】"]
    for m in recent:
        role = "user" if str(m.get("role", "")).upper() == "USER" else "assistant"
        lines.append(f"{role}: {m.get('content', '')}")
    lines.append("【以上是历史；用户当前这句话是最后一条】")
    return "\n".join(lines)


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
    scene = _normalize_scene(req.scene)

    history_text = None
    if session_id is not None:
        try:
            history_text = _build_history_text(list_messages(session_id), limit=8)
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

                "scene": req.scene,
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