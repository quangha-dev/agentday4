from __future__ import annotations

import sys
from pathlib import Path

# Tự động thêm thư mục starter_v0 vào sys.path để có thể chạy trực tiếp bằng python3
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from tools.legal_rag_search.tool import legal_rag_search


def test_t01_legal_rag_search_relevant_query():
    """T01: Câu hỏi đúng lĩnh vực -> Trả về điều khoản liên quan trong top 5."""
    res = legal_rag_search(
        query="Mức phạt khi vượt đèn đỏ bằng xe máy?",
        document_type="nghị định",
        legal_domain="giao thông",
        target_date="2026-07-29",
        top_k=5,
    )
    assert res.get("error") is None, f"Error: {res.get('error')}"
    assert res.get("tool") == "legal_rag_search"
    results = res.get("results", [])
    assert len(results) > 0, "No results returned for relevant query"
    top_hit = results[0]
    assert top_hit["document_id"] == "ND_168_2024"
    assert top_hit["article"] == "7"
    assert top_hit["clause"] == "7"
    assert top_hit["point"] == "c"
    assert top_hit["score"] > 0.0
    print("PASS: T01 - legal_rag_search_relevant_query")


def test_t02_legal_rag_search_no_data_query():
    """T02: Câu hỏi không có trong dữ liệu -> Trả danh sách rỗng, không tự tạo nội dung."""
    res = legal_rag_search(
        query="Quy định về du hành vũ trụ bằng vệ tinh cá nhân?",
        legal_domain="không gian",
    )
    assert res.get("error") is None
    results = res.get("results", [])
    assert results == [], "Expected empty results for out-of-domain query"
    print("PASS: T02 - legal_rag_search_no_data_query")


def test_t03_legal_rag_search_effective_date_filter():
    """T03: Có ngày áp dụng -> Lọc hoặc ưu tiên văn bản đúng thời gian hiệu lực."""
    # ND_100_2019 hết hiệu lực vào 2024-12-31; năm 2026 áp dụng ND_168_2024
    res_2026 = legal_rag_search(
        query="vượt đèn đỏ",
        target_date="2026-07-29",
        top_k=5,
    )
    assert res_2026.get("error") is None
    results_2026 = res_2026.get("results", [])
    assert len(results_2026) > 0
    assert results_2026[0]["document_id"] == "ND_168_2024"
    print("PASS: T03 - legal_rag_search_effective_date_filter")


if __name__ == "__main__":
    print("Running tests for Tool 1 (legal_rag_search)...")
    test_t01_legal_rag_search_relevant_query()
    test_t02_legal_rag_search_no_data_query()
    test_t03_legal_rag_search_effective_date_filter()
    print("ALL TESTS PASSED SUCCESSFULLY!")
