from __future__ import annotations

from typing import Any

from tools.legal_api import call_legal_api


def legal_rag_search(
    query: str = "",
    document_type: str = "all",
    legal_domain: str = "all",
    document_number: str | None = None,
    target_date: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """Retrieve citation-ready legal chunks from the OCR system's Qdrant collection."""
    return call_legal_api(
        "legal_rag_search",
        "/rag/search",
        {
            "query": query,
            "document_type": document_type,
            "legal_domain": legal_domain,
            "document_number": document_number,
            "target_date": target_date,
            "top_k": top_k,
        },
    )
