from unittest.mock import patch

from tools.check_effective_status.tool import check_effective_status


def test_check_effective_status_passes_target_date() -> None:
    with patch("tools.check_effective_status.tool.call_legal_api", return_value={"ok": True}) as call:
        check_effective_status("doc-id", "2026-07-29", article="7")
    call.assert_called_once_with(
        "check_effective_status",
        "/rag/effective-status",
        {
            "document_id": "doc-id",
            "target_date": "2026-07-29",
            "article": "7",
            "clause": None,
            "point": None,
        },
    )
