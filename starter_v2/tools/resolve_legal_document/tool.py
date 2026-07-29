from __future__ import annotations

from typing import Any

from tools.legal_api import call_legal_api


def resolve_legal_document(
    query: str = "",
    target_date: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    return call_legal_api(
        "resolve_legal_document",
        "/rag/documents/resolve",
        {"query": query, "target_date": target_date, "limit": limit},
    )
