from __future__ import annotations

from typing import Any

from tools.legal_api import call_legal_api


def extract_legal_information(
    citation_ids: list[str] | None = None,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    return call_legal_api(
        "extract_legal_information",
        "/rag/extract",
        {
            "citation_ids": citation_ids or [],
            "fields": fields or [
                "subject", "conduct", "rights", "obligations", "deadline", "penalty", "exceptions"
            ],
        },
    )
