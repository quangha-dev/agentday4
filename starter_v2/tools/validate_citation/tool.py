from __future__ import annotations

from typing import Any

from tools.legal_api import call_legal_api


def validate_citation(
    claims: list[dict[str, Any]] | None = None,
    target_date: str = "",
) -> dict[str, Any]:
    """Validate claims against immutable citation IDs stored in SQL/Qdrant."""
    if not claims:
        return {
            "tool": "validate_citation",
            "ok": False,
            "contract_version": "ver2",
            "valid": False,
            "target_date": target_date,
            "results": [],
            "errors": ["Cần ít nhất một claim gắn với citation_id từ tool tra cứu."],
        }
    return call_legal_api(
        "validate_citation",
        "/rag/citations/validate",
        {"claims": claims, "target_date": target_date},
    )
