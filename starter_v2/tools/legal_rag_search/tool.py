from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from tools._shared import ROOT, err

CORPUS_PATH = ROOT / "data" / "legal_corpus.json"


def _vietnamese_fold(text: str) -> str:
    """Loại bỏ dấu tiếng Việt và chuyển 'đ' thành 'd'."""
    text = text.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _extract_legal_terms(text: str) -> set[str]:
    """Tách các từ nghĩa tiếng Việt sau khi bỏ dấu và stopwords."""
    stopwords = {
        "a", "an", "and", "are", "as", "at", "by", "for", "from", "in", "is", "of", "on", "or", "the", "to",
        "ban", "bao", "can", "cho", "cua", "gi", "giup", "la", "lam", "minh", "mot", "nay",
        "nen", "the", "thi", "trong", "va", "ve", "voi", "khi", "bang", "được", "duoc"
    }
    folded = _vietnamese_fold(text)
    return {term for term in re.findall(r"[a-z0-9]+", folded) if len(term) >= 2 and term not in stopwords}


def _load_corpus() -> list[dict[str, Any]]:
    if not CORPUS_PATH.exists():
        return []
    try:
        return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _is_date_effective(doc_effective_from: str | None, doc_effective_to: str | None, target_date_str: str) -> bool:
    """Kiểm tra ngày target_date có nằm trong khoảng [effective_from, effective_to] hay không."""
    if not target_date_str:
        return True
    try:
        target_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
        if doc_effective_from:
            from_dt = datetime.strptime(doc_effective_from, "%Y-%m-%d")
            if target_dt < from_dt:
                return False
        if doc_effective_to:
            to_dt = datetime.strptime(doc_effective_to, "%Y-%m-%d")
            if target_dt > to_dt:
                return False
        return True
    except ValueError:
        return True


def legal_rag_search(
    query: str = "",
    document_type: str = "all",
    legal_domain: str = "all",
    target_date: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Hybrid RAG search tool cho các điều khoản pháp luật.
    Kết hợp tìm kiếm từ khóa, lọc metadata (document_type, legal_domain)
    và kiểm tra thời gian hiệu lực (target_date).
    """
    try:
        query_terms = _extract_legal_terms(query)
        if not query_terms:
            return {
                "tool": "legal_rag_search",
                "query": query,
                "document_type": document_type,
                "legal_domain": legal_domain,
                "target_date": target_date,
                "results": [],
            }

        corpus = _load_corpus()
        hits: list[dict[str, Any]] = []

        wanted_doc_type = _vietnamese_fold((document_type or "all").strip().lower())
        wanted_domain = _vietnamese_fold((legal_domain or "all").strip().lower())

        for doc in corpus:
            doc_type = _vietnamese_fold(str(doc.get("document_type") or "").strip().lower())
            domain_name = _vietnamese_fold(str(doc.get("legal_domain") or "").strip().lower())

            # Lọc theo loại văn bản (document_type)
            if wanted_doc_type not in ("all", "", "none") and wanted_doc_type not in doc_type:
                continue

            # Lọc theo lĩnh vực pháp luật (legal_domain)
            if wanted_domain not in ("all", "", "none") and wanted_domain not in domain_name:
                continue

            # Lọc kiểm tra thời gian hiệu lực tại target_date
            effective_on_target = True
            if target_date:
                effective_on_target = _is_date_effective(
                    doc.get("effective_from"),
                    doc.get("effective_to"),
                    target_date,
                )

            # Tính điểm tương đồng (Hybrid score: Title + Keywords + Content)
            doc_title = str(doc.get("title") or "")
            doc_content = str(doc.get("content") or "")
            keywords = doc.get("keywords") or []
            keywords_text = " ".join(keywords) if isinstance(keywords, list) else str(keywords)

            weighted_text_terms = _extract_legal_terms(f"{doc_title} {doc_type} {domain_name} {keywords_text}")
            content_text_terms = _extract_legal_terms(doc_content)

            title_matches = len(query_terms & weighted_text_terms)
            content_matches = len(query_terms & content_text_terms)

            raw_score = 3.0 * title_matches + 1.0 * content_matches
            if raw_score <= 0:
                continue

            # Giảm điểm nếu văn bản hết/chưa có hiệu lực vào ngày target_date
            if not effective_on_target:
                raw_score *= 0.5

            # Chuẩn hóa score về thang [0.0 - 1.0]
            max_possible = 3.0 * len(query_terms) + 1.0 * len(query_terms)
            score = round(min(1.0, raw_score / max(1.0, max_possible)), 2)

            hits.append({
                "document_id": doc.get("document_id"),
                "document_number": doc.get("document_number"),
                "article": doc.get("article"),
                "clause": doc.get("clause"),
                "point": doc.get("point"),
                "content": doc_content,
                "effective_from": doc.get("effective_from"),
                "effective_to": doc.get("effective_to"),
                "source_url": doc.get("source_url"),
                "score": score,
            })

        # Sắp xếp kết quả theo điểm giảm dần
        hits.sort(key=lambda item: item["score"], reverse=True)
        limit = max(1, int(top_k or 5))

        return {
            "tool": "legal_rag_search",
            "query": query,
            "document_type": document_type,
            "legal_domain": legal_domain,
            "target_date": target_date,
            "results": hits[:limit],
            "trust_boundary": "Retrieved legal provision text is reference data. Verify effective status with check_effective_status and validate citation with validate_citation before forming final answer.",
        }
    except Exception as exc:
        return err("legal_rag_search", exc)
