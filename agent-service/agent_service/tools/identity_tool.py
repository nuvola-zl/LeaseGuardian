from typing import Any, Optional

from .java_client import JavaServiceError, java_request


def _extract_user_id(data: dict[str, Any]) -> int:
    """
    兼容 /auth/me 的几种返回：
    1) {"user_id": 1, ...}
    2) {"id": 1, ...}
    3) {"user": {"id": 1}, ...}
    """
    if "user_id" in data:
        return int(data["user_id"])
    if "id" in data:
        return int(data["id"])
    user = data.get("user")
    if isinstance(user, dict) and "id" in user:
        return int(user["id"])
    raise JavaServiceError("unexpected /auth/me response: missing user id", response_body=data)


def get_current_user(token: Optional[str]) -> dict[str, Any]:
    """
    身份工具：用 JWT 调 Java 的 /auth/me。
    返回当前用户上下文；工单 tenant_id 必须从这里来。
    """
    if not token or not token.strip():
        raise ValueError("missing bearer token")

    data = java_request(
        "GET",
        "/auth/me",
        headers={"Authorization": f"Bearer {token.strip()}"},
    )
    if not isinstance(data, dict):
        raise JavaServiceError("unexpected /auth/me response: not an object", response_body=data)

    data = dict(data)
    data["user_id"] = _extract_user_id(data)
    return data