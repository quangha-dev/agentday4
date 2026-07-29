from __future__ import annotations

from typing import Any

from tools.legal_api import call_legal_api


def compare_legal_versions(
    old_document_id: str = "",
    new_document_id: str = "",
    article: str | None = None,
    clause: str | None = None,
    point: str | None = None,
) -> dict[str, Any]:
    """Compare two persisted document versions at the same structural location."""
    result = call_legal_api(
        "compare_legal_versions",
        "/rag/compare",
        {
            "old_document_id": old_document_id,
            "new_document_id": new_document_id,
            "article": article,
            "clause": clause,
            "point": point,
        },
    )
    old = result.get("old_document") or {}
    new = result.get("new_document") or {}
    result.setdefault("old_content", old.get("content", ""))
    result.setdefault("new_content", new.get("content", ""))
    result.setdefault("old_effective_to", old.get("effective_to"))
    result.setdefault("new_effective_from", new.get("effective_from"))
    return result
