from unittest.mock import patch

from tools.legal_rag_search.tool import legal_rag_search


def test_legal_rag_search_uses_ver2_backend_contract() -> None:
    expected = {"tool": "legal_rag_search", "ok": True, "contract_version": "ver2", "evidence": []}
    with patch("tools.legal_rag_search.tool.call_legal_api", return_value=expected) as call:
        result = legal_rag_search(
            query="quyền của người lao động",
            document_type="Luật",
            legal_domain="lao động",
            document_number="45/2019/QH14",
            target_date="2026-07-29",
            top_k=5,
        )
    assert result == expected
    call.assert_called_once_with(
        "legal_rag_search",
        "/rag/search",
        {
            "query": "quyền của người lao động",
            "document_type": "Luật",
            "legal_domain": "lao động",
            "document_number": "45/2019/QH14",
            "target_date": "2026-07-29",
            "top_k": 5,
        },
    )
