from __future__ import annotations

import sys
from pathlib import Path

# Tự động thêm thư mục starter_v0 vào sys.path để hỗ trợ chạy trực tiếp từ terminal
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from tools.get_legal_provision.tool import get_legal_provision


def test_t04_get_legal_provision_exists():
    """T04: Điều-Khoản-Điểm tồn tại -> Trả đúng nguyên văn và metadata (found = True)."""
    res = get_legal_provision(
        document_id="ND_168_2024",
        article="7",
        clause="7",
        point="c",
    )
    assert res.get("error") is None
    assert res.get("tool") == "get_legal_provision"
    assert res.get("found") is True
    assert res.get("document_id") == "ND_168_2024"
    assert res.get("article") == "7"
    assert res.get("clause") == "7"
    assert res.get("point") == "c"
    assert "4.000.000" in res.get("content", "")
    print("PASS: T04 - get_legal_provision_exists")


def test_t04_get_legal_provision_by_doc_number():
    """T04 b: Tra cứu theo số hiệu văn bản (168/2024/NĐ-CP)."""
    res = get_legal_provision(
        document_id="168/2024/NĐ-CP",
        article="7",
        clause="7",
        point="c",
    )
    assert res.get("error") is None
    assert res.get("found") is True
    assert res.get("article") == "7"
    print("PASS: T04b - get_legal_provision_by_doc_number")


def test_t05_get_legal_provision_not_found():
    """T05: Điều/Khoản không tồn tại -> found = False."""
    res = get_legal_provision(
        document_id="ND_168_2024",
        article="99",
        clause="1",
    )
    assert res.get("error") is None
    assert res.get("tool") == "get_legal_provision"
    assert res.get("found") is False
    print("PASS: T05 - get_legal_provision_not_found")


if __name__ == "__main__":
    print("Running tests for Tool 2 (get_legal_provision)...")
    test_t04_get_legal_provision_exists()
    test_t04_get_legal_provision_by_doc_number()
    test_t05_get_legal_provision_not_found()
    print("ALL TESTS PASSED SUCCESSFULLY FOR TOOL 2!")
