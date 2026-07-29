from __future__ import annotations

import sys
from pathlib import Path

# Tự động thêm thư mục starter_v0 vào sys.path để hỗ trợ chạy trực tiếp từ terminal
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from tools.extract_legal_information.tool import extract_legal_information


def test_t09_extract_legal_information_penalty():
    """T09: Trích xuất thông tin có mức phạt -> Trích đúng minimum, maximum và VND."""
    provisions = [
        {
            "citation_id": "CIT_01",
            "content": "Xử phạt người điều khiển xe mô tô, xe gắn máy vi phạm quy tắc giao thông đường bộ: Phạt tiền từ 4.000.000 đồng đến 6.000.000 đồng đối với người điều khiển xe thực hiện hành vi vi phạm không chấp hành tín hiệu đèn giao thông."
        }
    ]

    res = extract_legal_information(provisions=provisions)
    assert res.get("error") is None
    assert res.get("tool") == "extract_legal_information"
    assert res.get("evidence_ids") == ["CIT_01"]

    penalty = res.get("penalty")
    assert penalty is not None
    assert penalty.get("minimum") == 4000000
    assert penalty.get("maximum") == 6000000
    assert penalty.get("currency") == "VND"
    print("PASS: T09 - extract_legal_information_penalty")


def test_t10_extract_legal_information_no_deadline():
    """T10: Không có thông tin thời hạn -> trả deadline = None."""
    provisions = [
        {
            "citation_id": "CIT_02",
            "content": "Phạt tiền từ 800.000 đồng đến 1.000.000 đồng đối với hành vi vi phạm."
        }
    ]

    res = extract_legal_information(provisions=provisions)
    assert res.get("error") is None
    assert res.get("deadline") is None
    print("PASS: T10 - extract_legal_information_no_deadline")


if __name__ == "__main__":
    print("Running tests for Tool 5 (extract_legal_information)...")
    test_t09_extract_legal_information_penalty()
    test_t10_extract_legal_information_no_deadline()
    print("ALL TESTS PASSED SUCCESSFULLY FOR TOOL 5!")
