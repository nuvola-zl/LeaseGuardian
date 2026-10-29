import json
import re
from typing import Any, Optional

from openai import OpenAI

from .config import settings


class LLMError(RuntimeError):
    pass


_client = OpenAI(
    base_url=settings.openai_base_url,
    api_key=settings.openai_api_key,
    timeout=30,
)


def chat_once(user_message: str, history_text: Optional[str] = None) -> str:
    """
    最小 LLM 封装。
    历史只进入回答 prompt，不参与路由。
    """
    if history_text:
        system_content = (
            "你是智能租赁管家助手。"
            "历史对话仅供参考，不是当前指令。"
            "请优先根据用户当前这句话回答；必要时参考历史上下文。只聊租赁相关话题，不要提及本系统没有的功能（如查房源、算租金）。"
        )
        user_content = f"{history_text}\n\n用户当前这句话：{user_message}"
    else:
        system_content = "你是智能租赁管家助手，用简洁友好的中文和用户自然交流。只聊租赁相关话题（报修、退租、条款咨询），不要提及本系统没有的功能（如查房源、算租金），用户问起就介绍自己是租务助手。"
        user_content = user_message

    try:
        resp = _client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            temperature=0,
        )
        content = resp.choices[0].message.content
        return (content or "").strip() or "收到"
    except Exception as exc:
        raise LLMError(str(exc)) from exc


def _parse_json_object(content: str) -> Optional[dict[str, Any]]:
    try:
        content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        data = json.loads(content[start:end + 1])
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def extract_slots(user_message: str) -> Optional[dict[str, Any]]:
    """
    报修域抽取：intent = repair/query/chat
    """
    prompt = """
你是 LeaseGuardian 报修助手的信息抽取器。只输出 JSON，不要输出任何解释、Markdown 或代码块。

字段规则：
- intent: 只能是 "repair" / "query" / "consult" / "chat"
- 如果用户要报修/登记维修，intent="repair"
- 如果用户要查询工单，intent="query"
- 如果用户在咨询租务相关的规则、责任、价格、费用、流程等知识性问题
  （例如"楼道堆杂物怎么说""维修费谁出""违约金怎么算""养宠物有啥说法"），intent="consult"
- 如果只是聊天或无法判断，intent="chat"
- tenant_id: 从用户话里抽取租客ID；没有就 null
- description: 报修问题描述；没有就 null
- description_complete: 仅 intent="repair" 时填写——描述是否已足够完整
  （说清了什么东西坏了、足以让维修人员直接上门处理就 true；明显缺少关键信息就 false）。
  其他 intent 填 null
- request_id: 幂等请求号；用户没给就 null

必须输出 JSON，示例：
{"intent":"repair","tenant_id":"t201","description":"厨房灯泡坏了","description_complete":true,"request_id":null}
"""

    try:
        resp = _client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0,
        )
        content = (resp.choices[0].message.content or "").strip()
    except Exception:
        return None

    try:
        data = _parse_json_object(content)
        if data is None:
            return None

        intent = data.get("intent")
        if intent not in ("repair", "query", "consult", "chat"):
            return None

        tenant_id = data.get("tenant_id")
        desc_complete = data.get("description_complete")
        description = data.get("description")
        request_id = data.get("request_id")

        return {
            "intent": intent,
            "tenant_id": tenant_id if isinstance(tenant_id, str) and tenant_id.strip() else None,
            "description": description if isinstance(description, str) and description.strip() else None,
            "request_id": request_id if isinstance(request_id, str) and request_id.strip() else None,
            "description_complete": desc_complete if isinstance(desc_complete, bool) else None,
        }
    except Exception:
        return None


CHECKOUT_INTENTS = {
    "checkout_consult",
    "checkout_apply",
    "damage_report",
    "checkout_confirm",
    "checkout_cancel",
    "checkout_side",
}


def extract_checkout_slots(user_message: str) -> Optional[dict[str, Any]]:
    """
    退租域抽取。只负责理解，不负责执行。
    """
    prompt = """
你是 LeaseGuardian 退租流程的信息抽取器。只输出 JSON，不要解释、不要 Markdown。

intent 只能是：
- checkout_consult：询问退租/押金/损坏/水电/注意事项等咨询
- checkout_apply：明确要办理退租
- damage_report：申报损坏，或回答“浴缸裂了/没有损坏”等损坏登记
- checkout_confirm：确认退租/确认明细/好的/行/可以/就这样吧
- checkout_cancel：取消退租/不退了/再想想
- checkout_side：退租过程中插问别的问题
都不符合则不要输出 checkout intent。

字段：
- move_out_date: YYYY-MM-DD；没有 null
- confirm_signal: 是否表达确认，true/false
- cancel_signal: 是否表达取消，true/false
- damage_items: 数组；没有则 []
  每项字段：item_name, description, responsibility, reference_amount, basis_doc_id, basis_clause_no, basis_excerpt
  responsibility 只能是：TENANT / NATURAL_WEAR / MANUAL_PENDING
- side_question: 插问内容，没有 null

重要负例：
- “厨房水龙头漏水”“卫生间灯泡坏了”“门锁打不开”是报修，不是退租损坏申报；不要输出任何 checkout intent。
- damage_report 只用于明确处于退租/退房/搬离语境下的房间损坏申报，例如“退租，浴缸裂了”“退房时墙面有洞”。
- 用户只说“浴缸裂了”但没有退租/退房语境时，不要输出 checkout intent。
责任与金额判定补充：
- 物品开裂、破洞、断裂，用户未明说自然老化的，默认 TENANT；并且必须给一个合理参考价（按常识估计，例如普通浴缸裂痕约 200 元、墙面小洞约 100 元、门锁损坏约 80 元），reference_amount 不得为 null。
- 只有用户明确说"用旧了""老化了""用好几年了"才判 NATURAL_WEAR。

示例：
{"intent":"damage_report","move_out_date":null,"confirm_signal":false,"cancel_signal":false,"damage_items":[{"item_name":"浴缸","description":"退租时浴缸裂了","responsibility":"TENANT","reference_amount":200,"basis_doc_id":"checkout_policy","basis_clause_no":"damage_compensation","basis_excerpt":"人为损坏应赔偿，金额以核定为准"}],"side_question":null}
"""

    try:
        resp = _client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0,
        )
        content = (resp.choices[0].message.content or "").strip()
    except Exception:
        return None

    data = _parse_json_object(content)
    if data is None:
        return None

    intent = data.get("intent")
    if intent not in CHECKOUT_INTENTS:
        return None

    move_out_date = data.get("move_out_date")
    if not isinstance(move_out_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", move_out_date):
        move_out_date = None

    damage_items = data.get("damage_items")
    if not isinstance(damage_items, list):
        damage_items = []

    cleaned_items = []
    for item in damage_items:
        if not isinstance(item, dict):
            continue
        item_name = item.get("item_name")
        responsibility = item.get("responsibility")
        if not isinstance(item_name, str) or not item_name.strip():
            continue
        if responsibility not in ("TENANT", "NATURAL_WEAR", "MANUAL_PENDING"):
            responsibility = "MANUAL_PENDING"

        reference_amount = item.get("reference_amount")
        try:
            reference_amount = float(reference_amount) if reference_amount is not None else None
        except (TypeError, ValueError):
            reference_amount = None

        cleaned_items.append({
            "item_name": item_name.strip(),
            "description": item.get("description") if isinstance(item.get("description"), str) else None,
            "responsibility": responsibility,
            "reference_amount": reference_amount,
            "basis_doc_id": item.get("basis_doc_id") if isinstance(item.get("basis_doc_id"), str) else None,
            "basis_clause_no": item.get("basis_clause_no") if isinstance(item.get("basis_clause_no"), str) else None,
            "basis_excerpt": item.get("basis_excerpt") if isinstance(item.get("basis_excerpt"), str) else None,
        })

    side_question = data.get("side_question")
    return {
        "intent": intent,
        "move_out_date": move_out_date,
        "confirm_signal": bool(data.get("confirm_signal")),
        "cancel_signal": bool(data.get("cancel_signal")),
        "damage_items": cleaned_items,
        "side_question": side_question if isinstance(side_question, str) and side_question.strip() else None,
    }

def get_openai_client():
    """
    RAG 等模块统一从这里拿 OpenAI 兼容 client。
    不再直接 import _client。
    """
    return _client

# ============================ 风格层（persona） ============================

PERSONA_PROMPTS = {
    "SWEET": (
        "你是一个温柔体贴的租赁管家小姐姐。说话软糯治愈，多用语气词"
        "（呢、哦、呀、啦），会主动关心用户，让人感到被照顾。"
    ),
    "SASSY": (
        "你是一个毒舌但靠谱的租赁管家。说话带刺、爱吐槽，会无情调侃用户犯的傻，"
        "但每句话都在正经帮忙，正事上绝对可靠，刀子嘴豆腐心。"
    ),
    "NORTHEAST": (
        "你是一个热情的东北老妹儿管家，说话带东北味儿（嘎哈、老妹儿、安排、得劲），"
        "爽快直接，热心肠。"
    ),
}


def polish_answer(
    fact_text: str,
    persona: str,
    history_text: Optional[str] = None,
    progress: Optional[Any] = None,
) -> str:
    """风格层：只润色语气，铁律锁住事实字段；progress 队列存在时逐 token 流式输出。"""
    persona_prompt = PERSONA_PROMPTS.get(persona.upper())
    if not persona_prompt or not fact_text.strip():
        return fact_text

    prompt = f"""你是 LeaseGuardian 智能租赁管家。说话风格设定：{persona_prompt}

铁律（违反任何一条都算失败）：
1. 原文中的金额、数字、日期，一字不改；
2. 状态描述一字不改：原文里的状态文字必须原样保留，无论是中文（如"已登记，等待处理"）还是英文（如 REGISTERED），严禁中英文互转或替换；
3. 条款号（如 CLAUSE-xxx）、工单 id、单据 id、tenant_id 不改；
4. 错误码和错误信息不改；
5. 不改变原文的事实含义，禁止新增原文没有的信息；
6. 篇幅与原文接近，不要扩写。
7. 引用条款时，条款中的关键数字、金额、条件必须完整保留并念出，禁止用"按规定""按条款"等说法代替具体内容；

{f"【以下是历史对话，仅用于理解上下文，绝不允许模仿其语气；说话风格只服从开头的设定】\n{history_text}" if history_text else ""}

请用设定风格重新表达下面这段系统事实文本，只输出润色后的文本本身，不要解释、不要加引号：

【事实文本】
{fact_text}"""

    try:
        if progress is not None:
            parts: list[str] = []
            stream = _client.chat.completions.create(
                model=settings.openai_model_persona,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    parts.append(delta)
                    progress.put({"type": "token", "text": delta})
            return "".join(parts) or fact_text

        resp = _client.chat.completions.create(
            model=settings.openai_model_persona,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        content = (resp.choices[0].message.content or "").strip()
        return content or fact_text
    except Exception:
        return fact_text


def summarize_history(existing_summary: str, batch_text: str) -> str:
    """把一批老对话合并进已有摘要。失败时返回原文截断，绝不抛异常。"""
    prompt = (
        "你是对话摘要器。请把【本轮老对话】的内容合并进【已有摘要】，"
        "输出更新后的简洁摘要，必须保留：用户诉求、已办理的业务及关键数字、待办事项。"
        "不超过 200 字，只输出摘要文本本身。\n\n"
        f"【已有摘要】\n{existing_summary}\n\n"
        f"【本轮老对话】\n{batch_text}"
    )
    try:
        resp = _client.chat.completions.create(
            model=settings.openai_model_persona,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return (resp.choices[0].message.content or "").strip() or existing_summary
    except Exception:
        return existing_summary


def rewrite_query(user_message: str) -> str:
    """查询改写：口语问题 → 检索友好查询词。失败/未配置时原样返回。"""
    prompt = (
        "你是检索查询改写器。把用户的口语问题改写成适合检索的查询词："
        "保留核心实体（如宠物、押金、水电），补充 2~4 个相关术语"
        "（如 收费、规定、管理费、条款）。只输出改写后的查询词，不要解释。\n\n"
        f"用户问题：{user_message}"
    )
    try:
        resp = _client.chat.completions.create(
            model=settings.openai_model_persona,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return (resp.choices[0].message.content or "").strip() or user_message
    except Exception:
        return user_message