from unittest.mock import patch

from tools.get_legal_provision.tool import get_legal_provision


def test_get_legal_provision_passes_exact_structure() -> None:
    with patch("tools.get_legal_provision.tool.call_legal_api", return_value={"ok": True}) as call:
        get_legal_provision("doc-id", "7", "2", "a")
    call.assert_called_once_with(
        "get_legal_provision",
        "/rag/provision",
        {"document_id": "doc-id", "article": "7", "clause": "2", "point": "a"},
    )
