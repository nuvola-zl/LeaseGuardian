from typing import Any, Optional
from ..rag.core import (
    invalidate_domain_cache,
    retrieve_clauses,
    retrieve_first_clause,
)


def retrieve_checkout_clauses(query: str, top_k: int = 2) -> list[dict[str, Any]]:
    return retrieve_clauses(query, domain="checkout", top_k=top_k, extra_domains=["custom"])


def retrieve_first_checkout_clause(query: str) -> Optional[dict[str, Any]]:
    return retrieve_first_clause(query, domain="checkout")


def invalidate_cache() -> None:
    invalidate_domain_cache("checkout")

