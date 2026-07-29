from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools._shared import ROOT, err

CORPUS_PATH = ROOT / "data" / "legal_corpus.json"


def _load_corpus() -> list[dict[str, Any]]:
    if not CORPUS_PATH.exists():
        return []
    try:
        return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _normalize_code(val: str | None) -> str:
    if val is None:
        return ""
    return str(val).strip().lower()


def get_legal_provision(
    document_id: str = "",
    article: str = "",
    clause: str | None = None,
    point: str | None = None,
) -> dict[str, Any]:
    """
    Lấy chính xác nội dung quy định theo Văn bản - Điều - Khoản - Điểm.
    Ưu tiên tool này khi người dùng cung cấp rõ mã văn bản và số Điều-Khoản-Điểm.
    """
    try:
        norm_doc_id = _normalize_code(document_id)
        norm_article = _normalize_code(article)
        norm_clause = _normalize_code(clause)
        norm_point = _normalize_code(point)

        if not norm_doc_id or not norm_article:
            return {
                "tool": "get_legal_provision",
                "found": False,
                "document_id": document_id,
                "article": article,
                "clause": clause,
                "point": point,
                "message": "Cần cung cấp ít nhất document_id và article để tra cứu chính xác.",
            }

        corpus = _load_corpus()

        for doc in corpus:
            doc_id = _normalize_code(doc.get("document_id"))
            doc_number = _normalize_code(doc.get("document_number"))
            
            # Khớp document_id hoặc document_number
            if norm_doc_id != doc_id and norm_doc_id != doc_number:
                continue

            # Khớp Điều (Article)
            if _normalize_code(doc.get("article")) != norm_article:
                continue

            # Khớp Khoản (Clause) nếu được chỉ định
            if norm_clause and _normalize_code(doc.get("clause")) != norm_clause:
                continue

            # Khớp Điểm (Point) nếu được chỉ định
            if norm_point and _normalize_code(doc.get("point")) != norm_point:
                continue

            # Tìm thấy khớp hoàn toàn
            return {
                "tool": "get_legal_provision",
                "found": True,
                "document_id": doc.get("document_id"),
                "document_number": doc.get("document_number"),
                "article": str(doc.get("article")),
                "clause": str(doc.get("clause")) if doc.get("clause") is not None else None,
                "point": str(doc.get("point")) if doc.get("point") is not None else None,
                "content": doc.get("content", ""),
                "effective_from": doc.get("effective_from"),
                "effective_to": doc.get("effective_to"),
                "source_url": doc.get("source_url"),
                "page": doc.get("page", 1),
                "trust_boundary": "Exact provision text retrieved. Check effective status with check_effective_status if applicable.",
            }

        # Không tìm thấy khớp
        return {
            "tool": "get_legal_provision",
            "found": False,
            "document_id": document_id,
            "article": article,
            "clause": clause,
            "point": point,
            "message": f"Không tìm thấy quy định cho {document_id} Điều {article}"
                       + (f" Khoản {clause}" if clause else "")
                       + (f" Điểm {point}" if point else "") + ".",
        }

    except Exception as exc:
        return err("get_legal_provision", exc)
