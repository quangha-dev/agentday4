from __future__ import annotations

from typing import Any

from security import inspect_request


def audit_question(text: str = "") -> dict[str, Any]:
    decision = inspect_request(text)
    payload = decision.to_dict()
    # Avoid echoing a potentially hostile prompt back into model context.
    payload.pop("normalized_text", None)
    return {"tool": "question_guard", **payload}
