from typing import Any, Optional

from .java_client import JavaServiceError, java_request
import json

def create_session(user_id: int, scene: str, title: Optional[str] = None) -> dict[str, Any]:
    """
    创建聊天会话。
    Java: POST /chat/sessions?userId=xxx
    """
    payload: dict[str, Any] = {
        "scene": scene,
        "title": title,
    }
    data = java_request(
        "POST",
        "/chat/sessions",
        params={"userId": user_id},
        json_body=payload,
    )
    if not isinstance(data, dict):
        raise JavaServiceError("unexpected create_session response: not an object", response_body=data)
    return data


def add_message(
    session_id: int,
    role: str,
    content: str,
    metadata_json: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    往会话里追加一条消息。
    Java: POST /chat/sessions/{sessionId}/messages
    """
    payload: dict[str, Any] = {
        "role": role,
        "content": content,
        "metadata_json": (
            json.dumps(metadata_json, ensure_ascii=False)
            if metadata_json is not None
            else None
        ),
    }
    data = java_request(
        "POST",
        f"/chat/sessions/{session_id}/messages",
        json_body=payload,
    )
    if not isinstance(data, dict):
        raise JavaServiceError("unexpected add_message response: not an object", response_body=data)
    return data


def list_messages(session_id: int) -> list[dict[str, Any]]:
    """
    拉取某个会话的历史消息，后面前端刷新恢复聊天框会用。
    Java: GET /chat/sessions/{sessionId}/messages
    """
    data = java_request("GET", f"/chat/sessions/{session_id}/messages")
    if not isinstance(data, list):
        raise JavaServiceError("unexpected list_messages response: not a list", response_body=data)
    return data

def get_session(session_id: int) -> dict[str, Any]:
    """
    获取会话详情，包含 state_json。
    Java: GET /chat/sessions/{id}
    """
    data = java_request("GET", f"/chat/sessions/{session_id}")
    if not isinstance(data, dict):
        raise JavaServiceError("unexpected get_session response: not an object", response_body=data)
    return data


def update_session_state(session_id: int, state: dict[str, Any]) -> dict[str, Any]:
    """
    更新会话 state_json。
    注意：这里传的是完整合并后的 state，不做局部 patch。
    Java: PATCH /chat/sessions/{id}/state
    """
    payload = {
        "state_json": json.dumps(state, ensure_ascii=False)
    }
    data = java_request(
        "PATCH",
        f"/chat/sessions/{session_id}/state",
        json_body=payload,
    )
    if not isinstance(data, dict):
        raise JavaServiceError("unexpected update_session_state response: not an object", response_body=data)
    return data