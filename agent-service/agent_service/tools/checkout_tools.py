import uuid
from typing import Any, Optional

from .java_client import java_request


def new_request_id() -> str:
    return uuid.uuid4().hex


def checkout_current(tenant_id: int) -> Optional[dict[str, Any]]:
    return java_request(
        "GET",
        "/checkout/cases/current",
        params={"tenantId": tenant_id},
    )


def checkout_create(tenant_id: int, move_out_date: Optional[str] = None) -> dict[str, Any]:
    return java_request(
        "POST",
        "/checkout/cases",
        params={"tenantId": tenant_id},
        json_body={
            "request_id": new_request_id(),
            "move_out_date": move_out_date,
        },
    )


def checkout_update_move_out(tenant_id: int, case_id: int, move_out_date: str) -> dict[str, Any]:
    return java_request(
        "POST",
        f"/checkout/cases/{case_id}/move-out-date",
        params={"tenantId": tenant_id},
        json_body={
            "request_id": new_request_id(),
            "move_out_date": move_out_date,
        },
    )


def checkout_add_damage(
    tenant_id: int,
    case_id: int,
    item_name: str,
    description: Optional[str],
    responsibility: str,
    reference_amount: Optional[float],
    basis_doc_id: Optional[str],
    basis_clause_no: Optional[str],
    basis_excerpt: Optional[str],
) -> dict[str, Any]:
    return java_request(
        "POST",
        f"/checkout/cases/{case_id}/damages",
        params={"tenantId": tenant_id},
        json_body={
            "request_id": new_request_id(),
            "item_name": item_name,
            "description": description,
            "responsibility": responsibility,
            "reference_amount": reference_amount,
            "basis_doc_id": basis_doc_id,
            "basis_clause_no": basis_clause_no,
            "basis_excerpt": basis_excerpt,
        },
    )


def checkout_settlement_detail(tenant_id: int, case_id: int) -> dict[str, Any]:
    return java_request(
        "GET",
        f"/checkout/cases/{case_id}/settlement-detail",
        params={"tenantId": tenant_id},
    )


def checkout_generate_settlement(tenant_id: int, case_id: int) -> dict[str, Any]:
    return java_request(
        "POST",
        f"/checkout/cases/{case_id}/settlement",
        params={"tenantId": tenant_id},
        json_body={"request_id": new_request_id()},
    )


def checkout_confirm(tenant_id: int, case_id: int, settlement_version: int) -> dict[str, Any]:
    return java_request(
        "POST",
        f"/checkout/cases/{case_id}/confirm",
        params={"tenantId": tenant_id},
        json_body={
            "request_id": new_request_id(),
            "settlement_version": settlement_version,
        },
    )


def checkout_cancel(tenant_id: int, case_id: int) -> dict[str, Any]:
    return java_request(
        "POST",
        f"/checkout/cases/{case_id}/cancel",
        params={"tenantId": tenant_id},
        json_body={"request_id": new_request_id()},
    )