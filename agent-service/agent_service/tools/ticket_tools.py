from typing import Any, Optional

from .java_client import JavaServiceError, java_request

_TICKETS_PATH = "/tickets"


def _require_text(value: Optional[str], field_name: str) -> str:
    if value is None or not str(value).strip():
        raise ValueError(f"{field_name} is required")
    return str(value).strip()


def _require_int(value: Any, field_name: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def create_ticket(
    tenant_id: int,
    description: str,
    request_id: Optional[str] = None,
) -> dict[str, Any]:
    tenant_id = _require_int(tenant_id, "tenant_id")
    description = _require_text(description, "description")

    payload: dict[str, Any] = {
        "tenant_id": tenant_id,
        "description": description,
    }
    if request_id:
        payload["request_id"] = request_id

    data = java_request("POST", _TICKETS_PATH, json_body=payload)
    if not isinstance(data, dict):
        raise JavaServiceError("unexpected create_ticket response: not an object", response_body=data)
    return data


def get_ticket(ticket_id: int) -> dict[str, Any]:
    data = java_request("GET", f"{_TICKETS_PATH}/{ticket_id}")
    if not isinstance(data, dict):
        raise JavaServiceError("unexpected get_ticket response: not an object", response_body=data)
    return data


def list_tickets(tenant_id: Optional[int] = None) -> list[dict[str, Any]]:
    params = None
    if tenant_id is not None:
        params = {"tenant_id": _require_int(tenant_id, "tenant_id")}
    data = java_request("GET", _TICKETS_PATH, params=params)
    if not isinstance(data, list):
        raise JavaServiceError("unexpected list_tickets response: not a list", response_body=data)
    return data


def update_ticket_status(ticket_id: int, status: str) -> dict[str, Any]:
    status = _require_text(status, "status")
    data = java_request(
        "PATCH",
        f"{_TICKETS_PATH}/{ticket_id}/status",
        json_body={"status": status},
    )
    if not isinstance(data, dict):
        raise JavaServiceError("unexpected update_ticket_status response: not an object", response_body=data)
    return data