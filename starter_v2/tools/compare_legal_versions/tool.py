from __future__ import annotations

import difflib
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


def _find_provision(corpus: list[dict[str, Any]], doc_id_or_num: str, article: str | None = None, clause: str | None = None, point: str | None = None) -> dict[str, Any] | None:
    norm_target_id = _normalize_code(doc_id_or_num)
    norm_art = _normalize_code(article)
    norm_cl = _normalize_code(clause)
    norm_pt = _normalize_code(point)

    for doc in corpus:
        d_id = _normalize_code(doc.get("document_id"))
        d_num = _normalize_code(doc.get("document_number"))

        if norm_target_id == d_id or norm_target_id == d_num:
            if norm_art and _normalize_code(doc.get("article")) != norm_art:
                continue
            if norm_cl and _normalize_code(doc.get("clause")) != norm_cl:
                continue
            if norm_pt and _normalize_code(doc.get("point")) != norm_pt:
                continue
            return doc

    # Nếu tìm theo article/clause/point không thấy, trả về doc chính đầu tiên của mã văn bản đó
    for doc in corpus:
        d_id = _normalize_code(doc.get("document_id"))
        d_num = _normalize_code(doc.get("document_number"))
        if norm_target_id == d_id or norm_target_id == d_num:
            return doc

    return None


def _compute_diff_changes(old_text: str, new_text: str) -> list[dict[str, Any]]:
    """Phân tích và trích xuất các khối thay đổi (added, deleted, modified)."""
    if not old_text and not new_text:
        return []
    if not old_text:
        return [{"type": "added", "old_text": "", "new_text": new_text}]
    if not new_text:
        return [{"type": "deleted", "old_text": old_text, "new_text": ""}]
    if old_text == new_text:
        return []

    old_words = old_text.split()
    new_words = new_text.split()

    matcher = difflib.SequenceMatcher(None, old_words, new_words)
    changes: list[dict[str, Any]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "replace":
            changes.append({
                "type": "modified",
                "old_text": " ".join(old_words[i1:i2]),
                "new_text": " ".join(new_words[j1:j2]),
            })
        elif tag == "delete":
            changes.append({
                "type": "deleted",
                "old_text": " ".join(old_words[i1:i2]),
                "new_text": "",
            })
        elif tag == "insert":
            changes.append({
                "type": "added",
                "old_text": "",
                "new_text": " ".join(new_words[j1:j2]),
            })

    return changes


def compare_legal_versions(
    old_document_id: str = "",
    new_document_id: str = "",
    article: str | None = None,
    clause: str | None = None,
    point: str | None = None,
) -> dict[str, Any]:
    """
    So sánh quy định cũ và mới giữa 2 phiên bản văn bản pháp luật,
    xác định chi tiết nội dung được sửa đổi, bổ sung hoặc bãi bỏ.
    """
    try:
        if not old_document_id or not new_document_id:
            return {
                "tool": "compare_legal_versions",
                "error": "MissingParameters",
                "message": "Bắt buộc cung cấp cả old_document_id và new_document_id để so sánh.",
            }

        corpus = _load_corpus()

        old_doc = _find_provision(corpus, old_document_id, article, clause, point)
        new_doc = _find_provision(corpus, new_document_id, article, clause, point)

        old_content = old_doc.get("content", "") if old_doc else ""
        new_content = new_doc.get("content", "") if new_doc else ""

        old_eff_to = old_doc.get("effective_to") if old_doc else None
        new_eff_from = new_doc.get("effective_from") if new_doc else None

        changes = _compute_diff_changes(old_content, new_content)

        summary_parts = []
        if not old_doc:
            summary_parts.append(f"Không tìm thấy dữ liệu cho văn bản cũ '{old_document_id}'.")
        if not new_doc:
            summary_parts.append(f"Không tìm thấy dữ liệu cho văn bản mới '{new_document_id}'.")

        if old_doc and new_doc:
            if not changes:
                summary_parts.append("Không có thay đổi về mặt nội dung giữa hai phiên bản quy định.")
            else:
                summary_parts.append(f"Đã phát hiện {len(changes)} điểm thay đổi giữa quy định cũ và quy định mới.")

        summary = " ".join(summary_parts)

        return {
            "tool": "compare_legal_versions",
            "old_document_id": old_document_id,
            "new_document_id": new_document_id,
            "article": article,
            "clause": clause,
            "point": point,
            "old_content": old_content,
            "new_content": new_content,
            "changes": changes,
            "summary": summary,
            "old_effective_to": old_eff_to,
            "new_effective_from": new_eff_from,
            "trust_boundary": "Legal version diff calculated from reference text. Use exact provisions in formal citations.",
        }

    except Exception as exc:
        return err("compare_legal_versions", exc)
