from __future__ import annotations

from typing import Any

from tools.legal_api import call_legal_api


def get_legal_provision(
    document_id: str = "",
    article: str = "",
    clause: str | None = None,
    point: str | None = None,
) -> dict[str, Any]:
    """Resolve one exact Article/Clause/Point from the parsed legal hierarchy."""
    return call_legal_api(
        "get_legal_provision",
        "/rag/provision",
        {"document_id": document_id, "article": article, "clause": clause, "point": point},
    )
