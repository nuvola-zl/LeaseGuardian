from typing import Any, Optional

from .core import (
    invalidate_domain_cache,
    retrieve_clauses,
    retrieve_first_clause,
)


def retrieve_repair_clauses(query: str, top_k: int = 2) -> list[dict[str, Any]]:
    return retrieve_clauses(query, domain="repair", top_k=top_k)


def retrieve_first_repair_clause(query: str) -> Optional[dict[str, Any]]:
    return retrieve_first_clause(query, domain="repair")


def invalidate_cache() -> None:
    invalidate_domain_cache("repair")