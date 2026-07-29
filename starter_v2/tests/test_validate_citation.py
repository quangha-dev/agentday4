from unittest.mock import patch

from tools.validate_citation.tool import validate_citation


def test_validate_citation_rejects_empty_claims_locally() -> None:
    result = validate_citation([], "2026-07-29")
    assert result["ok"] is False
    assert result["valid"] is False


def test_validate_citation_passes_claims_to_backend() -> None:
    claims = [{"claim": "Nội dung", "citation_id": "citation-1"}]
    with patch("tools.validate_citation.tool.call_legal_api", return_value={"ok": True, "valid": True}) as call:
        result = validate_citation(claims, "2026-07-29")
    assert result["valid"] is True
    call.assert_called_once_with(
        "validate_citation",
        "/rag/citations/validate",
        {"claims": claims, "target_date": "2026-07-29"},
    )
