from unittest.mock import patch

from tools.extract_legal_information.tool import extract_legal_information


def test_extract_uses_only_persisted_citation_ids() -> None:
    with patch("tools.extract_legal_information.tool.call_legal_api", return_value={"ok": True}) as call:
        extract_legal_information(["citation-1"], ["penalty", "deadline"])
    call.assert_called_once_with(
        "extract_legal_information",
        "/rag/extract",
        {"citation_ids": ["citation-1"], "fields": ["penalty", "deadline"]},
    )
