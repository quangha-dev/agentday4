from __future__ import annotations

import sys
from pathlib import Path

# Tự động thêm thư mục starter_v0 vào sys.path để hỗ trợ chạy trực tiếp từ terminal
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from tools.check_effective_status.tool import check_effective_status


def test_t06_check_effective_status_effective():
    """T06: Văn bản còn hiệu lực -> Trả status = effective."""
    res = check_effective_status(
        document_id="ND_168_2024",
        target_date="2026-07-29",
    )
    assert res.get("error") is None
    assert res.get("tool") == "check_effective_status"
    assert res.get("status") == "effective"
    assert res.get("effective_from") == "2025-01-01"
    assert res.get("effective_to") is None
    print("PASS: T06 - check_effective_status_effective")


def test_t07_check_effective_status_replaced():
    """T07: Văn bản hết hiệu lực và bị thay thế -> Trả status = replaced & replaced_by."""
    res = check_effective_status(
        document_id="ND_100_2019",
        target_date="2026-07-29",
    )
    assert res.get("error") is None
    assert res.get("status") == "replaced"
    assert res.get("effective_to") == "2024-12-31"
    assert res.get("replaced_by") == "ND_168_2024"
    print("PASS: T07 - check_effective_status_replaced")


def test_check_effective_status_unknown_doc():
    """Kiểm tra văn bản không tồn tại -> Trả status = unknown."""
    res = check_effective_status(
        document_id="ND_UNKNOWN_9999",
        target_date="2026-07-29",
    )
    assert res.get("error") is None
    assert res.get("status") == "unknown"
    print("PASS: check_effective_status_unknown_doc")


if __name__ == "__main__":
    print("Running tests for Tool 3 (check_effective_status)...")
    test_t06_check_effective_status_effective()
    test_t07_check_effective_status_replaced()
    test_check_effective_status_unknown_doc()
    print("ALL TESTS PASSED SUCCESSFULLY FOR TOOL 3!")
