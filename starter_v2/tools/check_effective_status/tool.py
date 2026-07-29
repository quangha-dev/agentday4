from __future__ import annotations

from typing import Any

from tools.legal_api import call_legal_api


def check_effective_status(
    document_id: str = "",
    target_date: str = "",
    article: str | None = None,
    clause: str | None = None,
    point: str | None = None,
) -> dict[str, Any]:
    """Check document/version effectiveness using metadata persisted during OCR ingest."""
    return call_legal_api(
        "check_effective_status",
        "/rag/effective-status",
        {
            "document_id": document_id,
            "target_date": target_date,
            "article": article,
            "clause": clause,
            "point": point,
        },
    )
