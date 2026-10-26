import re
from typing import Any, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from .rag.repair_rag import retrieve_repair_clauses
from .llm import chat_once, extract_checkout_slots, extract_slots, polish_answer
from .tools.checkout_rag import retrieve_checkout_clauses, retrieve_first_checkout_clause
from .tools.checkout_tools import (
    checkout_add_damage,
    checkout_cancel,
    checkout_confirm,
    checkout_create,
    checkout_current,
    checkout_generate_settlement,
    checkout_settlement_detail,
    checkout_update_move_out,
)
from .tools.identity_tool import get_current_user
from .tools.java_client import JavaServiceError
from .tools.ticket_tools import create_ticket, list_tickets


class AgentState(TypedDict):
    message: str
    answer: str

    token: Optional[str]
    user_context: Optional[dict[str, Any]]

    route: str
    identity_status: str
    identity_error: Optional[str]
    history_text: Optional[str]
    last_ticket_id: Optional[int]

    description: Optional[str]
    request_id: Optional[str]

    scene: Optional[str]
    persona: Optional[str]
    progress: Optional[Any]
    ticket: Optional[dict[str, Any]]
    tickets: Optional[list[dict[str, Any]]]

    checkout_intent: Optional[str]
    move_out_date: Optional[str]
    damage_items: list[dict[str, Any]]
    confirm_signal: bool
    cancel_signal: bool
    side_question: Optional[str]

    active_lease: Optional[dict[str, Any]]
    termination_case: Optional[dict[str, Any]]
    missing_slots: list[str]
    checkout_detail: Optional[dict[str, Any]]
    checkout_error: Optional[str]
    checkout_next: str


# ============================ 常量 ============================

LOCATION_WORDS = ("厨房", "卫生间", "浴室", "卧室", "客厅", "阳台", "门口", "门锁", "窗户", "水龙头", "灯泡", "空调")

CHECKOUT_CONTEXT_WORDS = (
    "退租", "退房", "搬离", "结算", "押金", "到期", "赔偿",
    "退租单", "剩余租金", "不住了", "确认退租", "取消退租",
)

REPAIR_STRONG_WORDS = ("水龙头", "漏水", "灯泡", "门锁", "空调", "马桶", "下水道", "热水器")

CONFIRM_WORDS = ("确认", "好的", "好", "行", "可以", "就这样", "没问题")
EXPLICIT_CHECKOUT_WORDS = ("我要退租", "申请退租", "确认退租", "取消退租", "办理退租")
CANCEL_WORDS = ("取消", "不退了", "反悔", "先不退", "再想想")

DATE_RE = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})|(\d{4})年(\d{1,2})月(\d{1,2})[日号]?")

def _extract_date(message: str) -> Optional[str]:
    m = DATE_RE.search(message)
    if not m:
        return None
    if m.group(1):
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return f"{int(m.group(4)):04d}-{int(m.group(5)):02d}-{int(m.group(6)):02d}"

TICKET_STATUS_CN = {
    "REGISTERED": "已登记，等待处理",
    "PROCESSING": "处理中",
    "DONE": "已完成",
    "CANCELLED": "已取消",
}


# ============================ 基础工具 ============================

def cget(d: dict, *names: str, default=None):
    """双兼容读取：Java 全局 SNAKE_CASE，本地代码历史上用过 camelCase，都认。"""
    for n in names:
        if isinstance(d, dict) and d.get(n) is not None:
            return d[n]
    return default

def _emit_progress(state: dict, step: str) -> None:
    q = state.get("progress")
    if q is not None:
        q.put({"type": "status", "step": step})


def _split_kv(segment: str) -> Optional[tuple[str, str]]:
    segment = segment.strip()
    if not segment:
        return None
    for sep in ("=", ":", "："):
        if sep in segment:
            key, value = segment.split(sep, 1)
            if key.strip():
                return key.strip(), value.strip()
    return None


def _parse_pairs(body: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for segment in body.replace("；", ";").split(";"):
        kv = _split_kv(segment)
        if kv:
            result[kv[0].strip().lower()] = kv[1].strip()
    return result


def _clean_body(message: str, prefix_len: int) -> str:
    body = message.strip()[prefix_len:].strip()
    if body.startswith((":", "：")):
        body = body[1:].strip()
    return body


def parse_repair_command(message: str) -> Optional[dict[str, Any]]:
    if not message or not message.strip().startswith("报修"):
        return None
    pairs = _parse_pairs(_clean_body(message, 2))
    description = pairs.get("description") or pairs.get("desc") or pairs.get("问题") or pairs.get("描述")
    request_id = pairs.get("request_id") or pairs.get("request") or pairs.get("幂等号")
    if not description:
        return None
    return {"description": description, "request_id": request_id or None}


def parse_query_command(message: str) -> bool:
    return bool(message and message.strip().startswith("查工单"))


def needs_clarify(description: Optional[str]) -> bool:
    if not description or not description.strip():
        return True
    desc = description.strip()
    if len(desc) < 4:
        return True
    return not any(word in desc for word in LOCATION_WORDS)


def _current_user_id(state: AgentState) -> int:
    return int(state["user_context"]["user_id"])


def _extract_active_lease(user_context: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not user_context:
        return None
    lease = user_context.get("lease") or user_context.get("active_lease")
    return lease if isinstance(lease, dict) else None


def _load_active_case(token: Optional[str]) -> Optional[dict[str, Any]]:
    """understand 阶段预查活跃退租单；查不到/失败都返回 None（走无单逻辑）。"""
    if not token:
        return None
    try:
        user_context = get_current_user(token)
        return checkout_current(int(user_context["user_id"]))
    except Exception:
        return None


def _map_java_error(exc: JavaServiceError) -> str:
    if exc.http_status == 401:
        return "登录已失效，请重新登录。"
    if exc.http_status == 404:
        if exc.code == "A02002":
            return "您当前没有生效中的租约，无需办理退租。"
        return "没有查到对应单据。"
    if exc.http_status == 409:
        msg = str(exc)
        if "pending manual review" in msg:
            return "还有损坏项待人工核定，暂时不能确认退租。"
        if "version mismatch" in msg or "changed concurrently" in msg:
            return "单据状态已更新，请重新查看最新明细后再确认。"
        return "当前状态已变化，请重新查看退租进度。"
    if exc.http_status and exc.http_status >= 500:
        return "系统开小差了，请稍后再试。"
    return str(exc)


def _money(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _fallback_damage_basis() -> tuple[str, str, str]:
    """优先走 RAG；检索失败才用兜底文案。"""
    clause = retrieve_first_checkout_clause("人为损坏 赔偿 责任 自然老化")
    if clause:
        return clause["doc_id"], clause["clause_no"], clause["text"][:200]
    return (
        "checkout_policy",
        "CLAUSE-DAMAGE",
        "人为损坏应赔偿，自然老化不赔；金额以人工核定为准。",
    )


def _format_settlement_detail(detail: dict[str, Any]) -> str:
    case = cget(detail, "checkoutCase", "checkout_case", default={}) or {}
    bill = detail.get("bill")
    items = cget(detail, "billItems", "bill_items", default=[]) or []
    damages = cget(detail, "damageItems", "damage_items", default=[]) or []

    if not bill:
        return "结算明细还没生成。"

    lines = ["退租结算明细："]
    for item in items:
        direction = item.get("direction")
        sign = "+" if direction == "REFUND" else "-"
        extra = ""
        if cget(item, "itemCode", "item_code") == "UNUSED_RENT":
            extra = f"（{cget(item, 'months', default=0)} 个月 × {_money(cget(item, 'monthlyRent', 'monthly_rent'))}）"
        lines.append(f"{sign} {cget(item, 'itemName', 'item_name', default='')}{extra}: {_money(item.get('amount'))}")

    lines.append(f"应退总额: {_money(bill.get('amount'))}")

    pending = cget(case, "hasPendingDamage", "has_pending_damage", default=False) or any(
        d.get("reviewStatus") == "PENDING" or d.get("review_status") == "PENDING" for d in damages
    )
    if pending:
        lines.append("注意：有损坏项待人工核定，暂时不能确认退租。")
    else:
        lines.append("确认后 1-3 个工作日到账（演示数据）；确认前可免费取消。")

    return "\n".join(lines)


def _normalize_damage(item: dict[str, Any]) -> dict[str, Any]:
    basis_doc_id = item.get("basis_doc_id")
    basis_clause_no = item.get("basis_clause_no")
    basis_excerpt = item.get("basis_excerpt")
    if item.get("responsibility") == "TENANT" and (not basis_doc_id or not basis_clause_no or not basis_excerpt):
        basis_doc_id, basis_clause_no, basis_excerpt = _fallback_damage_basis()
    return {
        "item_name": item["item_name"],
        "description": item.get("description"),
        "responsibility": item["responsibility"],
        "reference_amount": item.get("reference_amount"),
        "basis_doc_id": basis_doc_id,
        "basis_clause_no": basis_clause_no,
        "basis_excerpt": basis_excerpt,
    }


def has_checkout_context(message: str) -> bool:
    return any(w in message for w in CHECKOUT_CONTEXT_WORDS)

REPAIR_CONSULT_WORDS = (
    "谁承担", "谁出钱", "责任", "费用", "多少钱", "参考价", "价格",
    "自然老化", "人为损坏",
)


def is_repair_consult(message: str) -> bool:
    """
    报修域的政策/价格咨询：
    - 问维修责任
    - 问维修参考价
    但不抢退租域的押金/赔偿/结算问题。
    """
    return (not has_checkout_context(message)) and any(w in message for w in REPAIR_CONSULT_WORDS)

# ============================ 报修域节点 ============================

def understand_node(state: AgentState) -> dict[str, Any]:
    _emit_progress(state, "understanding")
    message = state["message"].strip()
    active_case = _load_active_case(state.get("token"))
    scene_checkout = (state.get("scene") or "").upper() == "CHECKOUT"

    if parse_query_command(message):
        return {"route": "query"}

    rule_repair = parse_repair_command(message)
    if rule_repair:
        if needs_clarify(rule_repair["description"]):
            return {"route": "clarify"}
        return {
            "route": "repair",
            "description": rule_repair["description"],
            "request_id": rule_repair["request_id"],
        }
    # 报修政策/价格咨询：不进 identity，不需要登录
    if is_repair_consult(message):
        return {"route": "repair_consult"}

    strong_repair = any(w in message for w in REPAIR_STRONG_WORDS) and not has_checkout_context(message)
    explicit_checkout_signal = any(w in message for w in EXPLICIT_CHECKOUT_WORDS)
    checkout_allowed = (
            active_case is not None
            or has_checkout_context(message)
            or explicit_checkout_signal
            or scene_checkout
    )

    # 第一层：LLM 抽取
    checkout_slots = extract_checkout_slots(message) if checkout_allowed else None
    if checkout_slots:
        if checkout_slots["move_out_date"] is None:
            date_str = _extract_date(message)
            if date_str:
                checkout_slots["move_out_date"] = date_str
        return {
            "route": "checkout",
            "checkout_intent": checkout_slots["intent"],
            "move_out_date": checkout_slots["move_out_date"],
            "damage_items": checkout_slots["damage_items"],
            "confirm_signal": checkout_slots["confirm_signal"],
            "cancel_signal": checkout_slots["cancel_signal"],
            "side_question": checkout_slots["side_question"],
        }

    # 第二层：本地规则兜底（进入条件：有活跃单，或明确退租表达）
    if not strong_repair and (
            active_case is not None
            or explicit_checkout_signal
            or scene_checkout
    ):
        base = {
            "route": "checkout",
            "checkout_intent": "damage_report",
            "move_out_date": None,
            "damage_items": [],
            "confirm_signal": False,
            "cancel_signal": False,
            "side_question": None,
        }
        if any(w in message for w in CANCEL_WORDS):
            return {**base, "checkout_intent": "checkout_cancel", "cancel_signal": True}
        if any(w in message for w in CONFIRM_WORDS):
            return {**base, "checkout_intent": "checkout_confirm", "confirm_signal": True}
        date_str = _extract_date(message)
        if date_str:
            return {**base, "checkout_intent": "checkout_apply", "move_out_date": date_str}
        return base

    # 第三层：报修/查询/闲聊
    slots = extract_slots(message)
    if slots and slots.get("intent") == "repair":
        description = slots.get("description")
        if needs_clarify(description):
            return {"route": "clarify"}
        return {
            "route": "repair",
            "description": description.strip(),
            "request_id": slots.get("request_id"),
        }
    if slots and slots.get("intent") == "query":
        return {"route": "query"}
    return {"route": "chat"}


def route_after_understand(state: AgentState) -> str:
    return state["route"]


def chat_node(state: AgentState) -> dict[str, Any]:
    return {
        "answer": chat_once(
            state["message"],
            history_text=state.get("history_text"),
        )
    }


def clarify_node(state: AgentState) -> dict[str, Any]:
    return {"answer": "可以报修。请补充一句具体问题和位置，例如：厨房水龙头漏水、卫生间门锁坏了。"}


def identity_node(state: AgentState) -> dict[str, Any]:
    _emit_progress(state, "verifying")
    if state.get("user_context"):
        return {"identity_status": "ok", "identity_error": None}
    token = state.get("token")
    if not token:
        return {"identity_status": "unauthorized", "identity_error": "missing bearer token"}
    try:
        user_context = get_current_user(token)
        return {"identity_status": "ok", "user_context": user_context, "identity_error": None}
    except JavaServiceError as exc:
        if exc.http_status == 401:
            return {"identity_status": "unauthorized", "identity_error": str(exc)}
        return {"identity_status": "error", "identity_error": str(exc)}
    except ValueError as exc:
        return {"identity_status": "unauthorized", "identity_error": str(exc)}


def route_after_identity(state: AgentState) -> str:
    status = state.get("identity_status")
    if status == "ok":
        if state["route"] == "repair":
            return "create"
        if state["route"] == "checkout":
            return "checkout"
        return "query"
    if status == "unauthorized":
        return "unauthorized"
    return "error"


def auth_node(state: AgentState) -> dict[str, Any]:
    return {"answer": "请先登录后再办理租务；登录后我会自动识别当前用户，不需要你手动提供 tenant_id。"}


def error_node(state: AgentState) -> dict[str, Any]:
    return {"answer": f"身份服务暂时异常：{state.get('identity_error') or 'unknown error'}"}


def create_ticket_node(state: AgentState) -> dict[str, Any]:
    _emit_progress(state, "creating")
    ticket = create_ticket(
        tenant_id=_current_user_id(state),
        description=state["description"],
        request_id=state["request_id"],
    )
    return {
        "ticket": ticket,
        "last_ticket_id": int(ticket["id"]),
    }

def list_tickets_node(state: AgentState) -> dict[str, Any]:
    tickets = list_tickets(tenant_id=_current_user_id(state))
    return {"tickets": tickets}


# ============================ checkout 域节点 ============================

def checkout_context_node(state: AgentState) -> dict[str, Any]:
    _emit_progress(state, "querying")
    if state.get("identity_status") != "ok":
        return {"checkout_error": "identity not ok", "checkout_next": "answer"}

    tenant_id = _current_user_id(state)
    try:
        termination_case = checkout_current(tenant_id)
        active_lease = _extract_active_lease(state.get("user_context"))
        return {
            "termination_case": termination_case,
            "active_lease": active_lease,
            "missing_slots": [] if termination_case else ["case"],
            "checkout_next": "router",
        }
    except JavaServiceError as exc:
        return {
            "checkout_error": str(exc),
            "answer": _map_java_error(exc),
            "checkout_next": "answer",
        }


def route_after_checkout_context(state: AgentState) -> str:
    if state.get("identity_status") != "ok":
        return "unauthorized"
    return state.get("checkout_next") or "router"


def checkout_router_node(state: AgentState) -> dict[str, Any]:
    case = state.get("termination_case")
    intent = state.get("checkout_intent")
    lease = state.get("active_lease") or {}

    if lease.get("status") == "EXPIRED":
        return {"checkout_next": "answer", "answer": "您的合同已到期，无需退租流程。"}

    if case is None:
        if intent == "checkout_consult" or state.get("side_question"):
            return {"checkout_next": "consult"}
        if intent in {"checkout_apply", "damage_report"}:
            return {"checkout_next": "start"}
        return {"checkout_next": "answer", "answer": "当前没有进行中的退租单；如果你想退租，我可以直接帮你发起。"}

    status = case.get("status")
    if status not in ("APPLYING", "AWAITING_CONFIRM"):
        return {"checkout_next": "answer", "answer": "该退租流程已结束。"}

    case_move_out = cget(case, "moveOutDate", "move_out_date")

    # 取消永远最高优先
    if state.get("cancel_signal") or intent == "checkout_cancel":
        return {"checkout_next": "cancel"}

    if status == "APPLYING":
        if state.get("move_out_date"):
            return {"checkout_next": "slot"}
        if intent == "checkout_consult" or state.get("side_question"):
            return {"checkout_next": "consult", "resume_prompt": True}
        if case_move_out is None:
            return {"checkout_next": "slot"}
        if intent == "checkout_confirm":
            return {"checkout_next": "answer", "answer": "结算明细还没出，我算好了给您过目。"}
        return {"checkout_next": "damage"}

    # AWAITING_CONFIRM
    if state.get("confirm_signal") or intent == "checkout_confirm":
        return {"checkout_next": "confirm"}
    if intent == "damage_report" or state.get("damage_items"):
        return {"checkout_next": "damage"}
    if intent == "checkout_consult" or state.get("side_question"):
        return {"checkout_next": "consult", "resume_prompt": True}
    return {"checkout_next": "answer", "answer": "结算明细已出，您确认退租吗？确认前也可以免费取消。"}


def route_after_checkout_router(state: AgentState) -> str:
    return state.get("checkout_next") or "answer"


def checkout_consult_node(state: AgentState) -> dict[str, Any]:
    _emit_progress(state, "processing")
    message = state.get("message") or ""
    case = state.get("termination_case")

    if "水电" in message:
        query = "水电 欠费 结算 扣减"
    elif "押金" in message:
        query = "押金 退还 扣除"
    elif "损坏" in message or "赔偿" in message:
        query = "人为损坏 自然老化 赔偿 责任"
    elif "到期" in message:
        query = "到期 未退 EXPIRED"
    elif "取消" in message or "不退" in message:
        query = "确认前 免费取消 反悔"
    else:
        query = "退租 流程 搬离日 结算 确认"

    hits = retrieve_checkout_clauses(query, top_k=1)
    if hits:
        h = hits[0]
        excerpt = h["text"].splitlines()[1].strip() if len(h["text"].splitlines()) > 1 else h["text"][:80]
        body = f"{h['title']}：{excerpt}（依据 {h['doc_id']} {h['clause_no']}）"
    else:
        body = "退租流程是：发起退租、确认搬离日、登记损坏、出具结算明细，最后由您确认；确认前可免费取消。"

    if case and case.get("status") in ("APPLYING", "AWAITING_CONFIRM"):
        answer = f"{body}\n刚才的退租流程还在进行中，您要继续吗？"
    else:
        answer = f"{body}\n需要帮您办理退租吗？"

    return {"answer": answer}


def checkout_start_node(state: AgentState) -> dict[str, Any]:
    _emit_progress(state, "processing")
    tenant_id = _current_user_id(state)
    move_out_date = state.get("move_out_date")

    try:
        case = checkout_create(tenant_id, move_out_date)
    except JavaServiceError as exc:
        if exc.http_status == 409:
            try:
                case = checkout_current(tenant_id)
            except JavaServiceError:
                return {"answer": _map_java_error(exc)}
            if case is None:
                return {"answer": _map_java_error(exc)}
        else:
            return {"answer": _map_java_error(exc)}

    if cget(case, "moveOutDate", "move_out_date") is None:
        return {
            "termination_case": case,
            "answer": "已开始受理退租。您打算哪天搬离？直接告诉我日期就行，比如 3 月 15 日。",
        }

    return {
        "termination_case": case,
        "answer": "退租单已创建。办理前需要登记一下：房间内有物品损坏吗？没有就说“没有”。",
    }


def checkout_slot_node(state: AgentState) -> dict[str, Any]:
    _emit_progress(state, "processing")
    tenant_id = _current_user_id(state)
    case = state.get("termination_case")
    if not case:
        return {"answer": "当前没有进行中的退租单。"}

    move_out_date = state.get("move_out_date")
    if not move_out_date:
        return {"answer": "您打算哪天搬离？直接告诉我日期就行，比如 3 月 15 日。"}

    try:
        updated = checkout_update_move_out(tenant_id, case["id"], move_out_date)
        return {
            "termination_case": updated,
            "answer": "已记录搬离日。房间内是否有物品损坏？没有就说“没有”。",
        }
    except JavaServiceError as exc:
        return {"answer": _map_java_error(exc)}


def checkout_damage_node(state: AgentState) -> dict[str, Any]:
    _emit_progress(state, "processing")
    tenant_id = _current_user_id(state)
    case = state.get("termination_case")
    if not case:
        return {"answer": "当前没有进行中的退租单。"}

    if cget(case, "moveOutDate", "move_out_date") is None:
        return {"answer": "请先告诉我您打算哪天搬离，比如 3 月 15 日。"}

    try:
        for raw in state.get("damage_items") or []:
            item = _normalize_damage(raw)
            checkout_add_damage(
                tenant_id=tenant_id,
                case_id=case["id"],
                item_name=item["item_name"],
                description=item["description"],
                responsibility=item["responsibility"],
                reference_amount=item["reference_amount"],
                basis_doc_id=item["basis_doc_id"],
                basis_clause_no=item["basis_clause_no"],
                basis_excerpt=item["basis_excerpt"],
            )

        checkout_generate_settlement(tenant_id, case["id"])
        detail = checkout_settlement_detail(tenant_id, case["id"])
        return {
            "checkout_detail": detail,
            "answer": _format_settlement_detail(detail),
        }
    except JavaServiceError as exc:
        return {"answer": _map_java_error(exc)}


def checkout_settlement_node(state: AgentState) -> dict[str, Any]:
    _emit_progress(state, "processing")
    tenant_id = _current_user_id(state)
    case = state.get("termination_case")
    if not case:
        return {"answer": "当前没有进行中的退租单。"}

    try:
        checkout_generate_settlement(tenant_id, case["id"])
        detail = checkout_settlement_detail(tenant_id, case["id"])
        return {
            "checkout_detail": detail,
            "answer": _format_settlement_detail(detail),
        }
    except JavaServiceError as exc:
        return {"answer": _map_java_error(exc)}


def checkout_confirm_node(state: AgentState) -> dict[str, Any]:
    _emit_progress(state, "processing")
    tenant_id = _current_user_id(state)
    case = state.get("termination_case")

    if not case:
        return {"answer": "当前没有进行中的退租单。"}
    if case.get("status") != "AWAITING_CONFIRM":
        return {"answer": "当前没有待确认的退租结算。"}

    version = int(cget(case, "settlementVersion", "settlement_version", default=0))
    try:
        checkout_confirm(tenant_id, case["id"], version)
        return {"answer": "退租完成，房间已释放，模拟退款将在 1-3 个工作日到账。"}
    except JavaServiceError as exc:
        return {"answer": _map_java_error(exc)}


def checkout_cancel_node(state: AgentState) -> dict[str, Any]:
    _emit_progress(state, "processing")
    tenant_id = _current_user_id(state)
    case = state.get("termination_case")

    if not case:
        return {"answer": "当前没有进行中的退租单。"}

    try:
        checkout_cancel(tenant_id, case["id"])
        return {"answer": "退租已取消，本次不收取费用；租约已恢复生效。"}
    except JavaServiceError as exc:
        return {"answer": _map_java_error(exc)}

def repair_consult_node(state: AgentState) -> dict[str, Any]:
    message = state.get("message") or ""

    if any(w in message for w in ("责任", "谁承担", "谁出钱", "自然老化", "人为损坏")):
        query = "人为损坏 自然老化 维修责任"
    elif "水龙头" in message:
        query = "水龙头维修参考价"
    elif "浴缸" in message:
        query = "浴缸维修参考价"
    elif any(w in message for w in ("多少钱", "费用", "参考价", "价格")):
        query = "维修 参考价 费用"
    else:
        query = "维修 责任 参考价"

    hits = retrieve_repair_clauses(query, top_k=1)
    if hits:
        h = hits[0]
        lines = [ln.strip() for ln in h["text"].splitlines() if ln.strip()]
        excerpt = lines[1] if len(lines) > 1 else h["text"][:80]
        answer = f"{h['title']}：{excerpt}（依据 {h['doc_id']} {h['clause_no']}）"
    else:
        answer = "我暂时没查到对应维修条款；如果你要报修，可以直接描述具体问题。"

    if any(w in message for w in REPAIR_STRONG_WORDS):
        answer += "\n如果你是要报修，请告诉我具体位置和问题，例如：厨房水龙头漏水。"

    return {"answer": answer}
# ============================ 出口 ============================

def answer_node(state: AgentState) -> dict[str, Any]:
    if state.get("ticket"):
        ticket = state["ticket"]
        status_cn = TICKET_STATUS_CN.get(str(ticket.get("status", "")).upper(), "已登记")
        return {
            "answer": f"已创建报修工单：编号 {ticket.get('id')}，当前状态：{status_cn}。"
        }

    if state.get("tickets") is not None:
        tickets = state["tickets"]
        lines = [f"查到 {len(tickets)} 条工单："]
        for t in tickets[:5]:
            status_cn = TICKET_STATUS_CN.get(str(t.get("status", "")).upper(), "已登记")
            lines.append(f"· 编号 {t.get('id')}：{t.get('description')}（{status_cn}）")
        return {"answer": "\n".join(lines)}

    return {"answer": state["answer"]}

def persona_node(state: AgentState) -> dict[str, Any]:
    """风格层：有 persona 走流式润色（逐 token 推队列），失败或无 persona 原样返回。"""
    answer = state.get("answer") or ""
    persona = state.get("persona")
    if not answer or not persona:
        return {"answer": answer}
    _emit_progress(state, "polishing")
    return {
        "answer": polish_answer(
            answer,
            persona,
            state.get("history_text"),
            progress=state.get("progress"),
        )
    }


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("understand_node", understand_node)
    graph.add_node("clarify_node", clarify_node)
    graph.add_node("identity_node", identity_node)
    graph.add_node("auth_node", auth_node)
    graph.add_node("error_node", error_node)
    graph.add_node("chat_node", chat_node)
    graph.add_node("create_ticket_node", create_ticket_node)
    graph.add_node("list_tickets_node", list_tickets_node)
    graph.add_node("answer_node", answer_node)
    graph.add_node("persona_node", persona_node)
    graph.add_node("repair_consult_node", repair_consult_node)

    graph.add_node("checkout_context_node", checkout_context_node)
    graph.add_node("checkout_router_node", checkout_router_node)
    graph.add_node("checkout_consult_node", checkout_consult_node)
    graph.add_node("checkout_start_node", checkout_start_node)
    graph.add_node("checkout_slot_node", checkout_slot_node)
    graph.add_node("checkout_damage_node", checkout_damage_node)
    graph.add_node("checkout_settlement_node", checkout_settlement_node)
    graph.add_node("checkout_confirm_node", checkout_confirm_node)
    graph.add_node("checkout_cancel_node", checkout_cancel_node)

    graph.add_edge(START, "understand_node")
    graph.add_conditional_edges(
        "understand_node",
        route_after_understand,
        {
            "clarify": "clarify_node",
            "repair": "identity_node",
            "query": "identity_node",
            "repair_consult": "repair_consult_node",
            "checkout": "identity_node",
            "chat": "chat_node",
        },
    )

    graph.add_conditional_edges(
        "identity_node",
        route_after_identity,
        {
            "create": "create_ticket_node",
            "query": "list_tickets_node",
            "checkout": "checkout_context_node",
            "unauthorized": "auth_node",
            "error": "error_node",
        },
    )

    graph.add_conditional_edges(
        "checkout_context_node",
        route_after_checkout_context,
        {
            "router": "checkout_router_node",
            "unauthorized": "auth_node",
            "error": "error_node",
            "answer": "answer_node",
        },
    )

    graph.add_conditional_edges(
        "checkout_router_node",
        route_after_checkout_router,
        {
            "consult": "checkout_consult_node",
            "start": "checkout_start_node",
            "slot": "checkout_slot_node",
            "damage": "checkout_damage_node",
            "settlement": "checkout_settlement_node",
            "confirm": "checkout_confirm_node",
            "cancel": "checkout_cancel_node",
            "answer": "answer_node",
        },
    )

    graph.add_edge("clarify_node", "answer_node")
    graph.add_edge("auth_node", "answer_node")
    graph.add_edge("repair_consult_node", "answer_node")
    graph.add_edge("error_node", "answer_node")
    graph.add_edge("chat_node", "answer_node")
    graph.add_edge("create_ticket_node", "answer_node")
    graph.add_edge("list_tickets_node", "answer_node")

    graph.add_edge("checkout_consult_node", "answer_node")
    graph.add_edge("checkout_start_node", "answer_node")
    graph.add_edge("checkout_slot_node", "answer_node")
    graph.add_edge("checkout_damage_node", "answer_node")
    graph.add_edge("checkout_settlement_node", "answer_node")
    graph.add_edge("checkout_confirm_node", "answer_node")
    graph.add_edge("checkout_cancel_node", "answer_node")

    # 出口：所有答案统一过风格层，再到终点
    graph.add_edge("answer_node", "persona_node")
    graph.add_edge("persona_node", END)

    return graph.compile()


agent_graph = build_graph()