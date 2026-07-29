from __future__ import annotations

import json
from datetime import datetime
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


def _normalize_str(val: str | None) -> str:
    if val is None:
        return ""
    return str(val).strip().lower()


def check_effective_status(
    document_id: str = "",
    target_date: str = "",
    article: str | None = None,
    clause: str | None = None,
    point: str | None = None,
) -> dict[str, Any]:
    """
    Xác định trạng thái hiệu lực pháp lý của văn bản/điều khoản tại mốc thời gian target_date.
    Trạng thái chuẩn: not_yet_effective, effective, partially_effective, expired, replaced, unknown.
    """
    try:
        norm_doc_id = _normalize_str(document_id)
        if not norm_doc_id:
            return {
                "tool": "check_effective_status",
                "document_id": document_id,
                "target_date": target_date,
                "status": "unknown",
                "message": "Thiếu tham số document_id bắt buộc.",
            }

        target_date_str = (target_date or datetime.now().strftime("%Y-%m-%d")).strip()
        try:
            target_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
        except ValueError:
            target_dt = datetime.now()
            target_date_str = target_dt.strftime("%Y-%m-%d")

        corpus = _load_corpus()
        matched_docs: list[dict[str, Any]] = []

        for doc in corpus:
            d_id = _normalize_str(doc.get("document_id"))
            d_num = _normalize_str(doc.get("document_number"))

            if norm_doc_id == d_id or norm_doc_id == d_num:
                # Nếu có lọc Điều-Khoản-Điểm
                if article and _normalize_str(doc.get("article")) != _normalize_str(article):
                    continue
                if clause and _normalize_str(doc.get("clause")) != _normalize_str(clause):
                    continue
                if point and _normalize_str(doc.get("point")) != _normalize_str(point):
                    continue
                matched_docs.append(doc)

        if not matched_docs:
            return {
                "tool": "check_effective_status",
                "document_id": document_id,
                "target_date": target_date_str,
                "status": "unknown",
                "effective_from": None,
                "effective_to": None,
                "amended_by": [],
                "replaced_by": None,
                "notes": f"Không tìm thấy dữ liệu cho văn bản '{document_id}'.",
            }

        # Sử dụng bản ghi trùng khớp đầu tiên
        doc = matched_docs[0]
        eff_from_str = doc.get("effective_from")
        eff_to_str = doc.get("effective_to")
        replaced_by = doc.get("replaced_by")
        amended_by = doc.get("amended_by") or []

        eff_from_dt = datetime.strptime(eff_from_str, "%Y-%m-%d") if eff_from_str else None
        eff_to_dt = datetime.strptime(eff_to_str, "%Y-%m-%d") if eff_to_str else None

        # Logic xác định trạng thái hiệu lực chuẩn
        status = "effective"
        notes = None

        if eff_from_dt and target_dt < eff_from_dt:
            status = "not_yet_effective"
            notes = f"Văn bản chưa có hiệu lực vào ngày {target_date_str} (ngày có hiệu lực: {eff_from_str})."
        elif eff_to_dt and target_dt > eff_to_dt:
            if replaced_by:
                status = "replaced"
                notes = f"Văn bản đã hết hiệu lực từ ngày {eff_to_str} và được thay thế bởi {replaced_by}."
            else:
                status = "expired"
                notes = f"Văn bản đã hết hiệu lực từ ngày {eff_to_str}."
        else:
            status = "effective"
            notes = f"Văn bản đang có hiệu lực tại thời điểm {target_date_str}."

        return {
            "tool": "check_effective_status",
            "document_id": doc.get("document_id"),
            "document_number": doc.get("document_number"),
            "target_date": target_date_str,
            "status": status,
            "effective_from": eff_from_str,
            "effective_to": eff_to_str,
            "amended_by": amended_by,
            "replaced_by": replaced_by,
            "notes": notes,
            "trust_boundary": "Effective status verified against internal legal metadata. Use in validation step before answering.",
        }

    except Exception as exc:
        return err("check_effective_status", exc)
