from __future__ import annotations

import sys
from pathlib import Path

# Tự động thêm thư mục starter_v0 vào sys.path để hỗ trợ chạy trực tiếp từ terminal
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from tools.validate_citation.tool import validate_citation


def test_t11_validate_citation_valid():
    """T11: Citation tồn tại, khớp nội dung và còn hiệu lực -> valid = True."""
    claims = [
        {
            "claim": "Hành vi này bị phạt từ 4 đến 6 triệu đồng.",
            "citation_id": "CIT_01"
        }
    ]
    res = validate_citation(claims=claims, target_date="2026-07-29")
    assert res.get("error") is None
    assert res.get("tool") == "validate_citation"
    assert res.get("valid") is True
    assert len(res.get("errors", [])) == 0
    print("PASS: T11 - validate_citation_valid")


def test_t12_validate_citation_invalid_expired():
    """T12: Citation bị hết hiệu lực tại target_date (ND_100_2019 vào năm 2026) -> valid = False."""
    claims = [
        {
            "claim": "Hành vi này bị phạt từ 800.000 đến 1.000.000 đồng.",
            "citation_id": "CIT_02"  # CIT_02 là ND_100_2019 (hết hiệu lực từ 2024-12-31)
        }
    ]
    res = validate_citation(claims=claims, target_date="2026-07-29")
    assert res.get("error") is None
    assert res.get("valid") is False
    assert len(res.get("errors", [])) > 0
    print("PASS: T12 - validate_citation_invalid_expired")


def test_t12_validate_citation_missing_id():
    """T12 b: Citation ID không tồn tại -> valid = False."""
    claims = [
        {
            "claim": "Một khẳng định không có căn cứ.",
            "citation_id": "CIT_NON_EXISTENT"
        }
    ]
    res = validate_citation(claims=claims, target_date="2026-07-29")
    assert res.get("error") is None
    assert res.get("valid") is False
    assert any("không tồn tại" in err for err in res.get("errors", []))
    print("PASS: T12b - validate_citation_missing_id")


if __name__ == "__main__":
    print("Running tests for Tool 6 (validate_citation)...")
    test_t11_validate_citation_valid()
    test_t12_validate_citation_invalid_expired()
    test_t12_validate_citation_missing_id()
    print("ALL TESTS PASSED SUCCESSFULLY FOR TOOL 6!")
