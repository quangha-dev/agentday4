from __future__ import annotations

import sys
from pathlib import Path

# Tự động thêm thư mục starter_v0 vào sys.path để hỗ trợ chạy trực tiếp từ terminal
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from tools.compare_legal_versions.tool import compare_legal_versions


def test_t08_compare_legal_versions_modified():
    """T08: So sánh quy định vượt đèn đỏ giữa Nghị định 100/2019 và Nghị định 168/2024."""
    res = compare_legal_versions(
        old_document_id="ND_100_2019",
        new_document_id="ND_168_2024",
    )
    assert res.get("error") is None
    assert res.get("tool") == "compare_legal_versions"
    assert "800.000" in res.get("old_content", "")
    assert "4.000.000" in res.get("new_content", "")
    assert res.get("old_effective_to") == "2024-12-31"
    assert res.get("new_effective_from") == "2025-01-01"
    changes = res.get("changes", [])
    assert len(changes) > 0
    # Phải có khối thay đổi loại 'modified'
    assert any(c["type"] == "modified" for c in changes)
    print("PASS: T08 - compare_legal_versions_modified")


def test_compare_legal_versions_identical():
    """Test hai văn bản nội dung giống hệt nhau -> changes = []."""
    res = compare_legal_versions(
        old_document_id="ND_168_2024",
        new_document_id="ND_168_2024",
    )
    assert res.get("error") is None
    assert res.get("changes") == []
    print("PASS: compare_legal_versions_identical")


if __name__ == "__main__":
    print("Running tests for Tool 4 (compare_legal_versions)...")
    test_t08_compare_legal_versions_modified()
    test_compare_legal_versions_identical()
    print("ALL TESTS PASSED SUCCESSFULLY FOR TOOL 4!")
