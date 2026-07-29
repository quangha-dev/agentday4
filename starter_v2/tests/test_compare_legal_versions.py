from unittest.mock import patch

from tools.compare_legal_versions.tool import compare_legal_versions


def test_compare_versions_uses_backend_evidence() -> None:
    backend = {
        "ok": True,
        "old_document": {"content": "cũ", "effective_to": "2025-01-01"},
        "new_document": {"content": "mới", "effective_from": "2025-01-02"},
    }
    with patch("tools.compare_legal_versions.tool.call_legal_api", return_value=backend):
        result = compare_legal_versions("old-id", "new-id", article="1")
    assert result["old_content"] == "cũ"
    assert result["new_content"] == "mới"
    assert result["old_effective_to"] == "2025-01-01"
    assert result["new_effective_from"] == "2025-01-02"
