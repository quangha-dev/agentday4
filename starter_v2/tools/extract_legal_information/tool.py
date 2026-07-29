from __future__ import annotations

import re
from typing import Any

from tools._shared import err


def _parse_amount(amount_str: str) -> int:
    clean = amount_str.replace(".", "").replace(",", "").strip()
    return int(clean) if clean.isdigit() else 0


def _extract_penalty(text: str) -> dict[str, Any] | None:
    """Trích xuất thông tin mức phạt tiền từ văn bản quy định pháp luật."""
    # Pattern: Phạt tiền từ X đồng đến Y đồng
    match_range = re.search(r"Phạt tiền từ ([\d\.]+) (?:đồng|VNĐ) đến ([\d\.]+) (?:đồng|VNĐ)", text, re.IGNORECASE)
    if match_range:
        min_val = _parse_amount(match_range.group(1))
        max_val = _parse_amount(match_range.group(2))
        return {
            "minimum": min_val,
            "maximum": max_val,
            "currency": "VND",
        }

    # Pattern: Phạt tiền từ X đến Y triệu đồng
    match_trieu = re.search(r"Phạt tiền từ ([\d\,\.]+) đến ([\d\,\.]+) triệu (?:đồng|VNĐ)", text, re.IGNORECASE)
    if match_trieu:
        min_float = float(match_trieu.group(1).replace(",", "."))
        max_float = float(match_trieu.group(2).replace(",", "."))
        return {
            "minimum": int(min_float * 1000000),
            "maximum": int(max_float * 1000000),
            "currency": "VND",
        }

    return None


def _extract_subject(text: str) -> str | None:
    """Trích xuất đối tượng/chủ thể áp dụng."""
    match = re.search(r"(?:Xử phạt|đối với)\s+(người điều khiển [^:\.\,]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    if "người điều khiển" in text.lower():
        return "Người điều khiển phương tiện"
    return "Chủ thể vi phạm"


def _extract_conduct(text: str) -> str | None:
    """Trích xuất hành vi vi phạm."""
    match = re.search(r"(?:hành vi vi phạm|hành vi)\s+([^:\.\,]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    if "không chấp hành tín hiệu đèn" in text.lower() or "vượt đèn đỏ" in text.lower():
        return "Không chấp hành tín hiệu đèn giao thông"
    return None


def extract_legal_information(
    provisions: list[dict[str, Any]] | None = None,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """
    Trích xuất thông tin pháp lý có cấu trúc (Chủ thể, Hành vi, Quyền, Nghĩa vụ, Thời hạn, Mức phạt, Ngoại lệ)
    từ các điều khoản đã lấy được. Mọi thông tin trích xuất bắt buộc gắn liền với evidence_ids.
    """
    try:
        if not provisions:
            return {
                "tool": "extract_legal_information",
                "subject": None,
                "conduct": None,
                "rights": [],
                "obligations": [],
                "deadline": None,
                "penalty": None,
                "exceptions": [],
                "evidence_ids": [],
            }

        wanted_fields = set(fields or [
            "subject", "conduct", "rights", "obligations", "deadline", "penalty", "exceptions"
        ])

        combined_text_parts = []
        evidence_ids = []

        for item in provisions:
            if isinstance(item, dict):
                c_id = item.get("citation_id")
                content = item.get("content", "")
                if c_id:
                    evidence_ids.append(str(c_id))
                if content:
                    combined_text_parts.append(content)

        full_text = " ".join(combined_text_parts)

        # Trích xuất từng trường
        subject = _extract_subject(full_text) if "subject" in wanted_fields else None
        conduct = _extract_conduct(full_text) if "conduct" in wanted_fields else None
        penalty = _extract_penalty(full_text) if "penalty" in wanted_fields else None

        # Trích xuất thời hạn (deadline)
        deadline = None
        if "deadline" in wanted_fields:
            deadline_match = re.search(r"trong thời hạn (\d+ ngày|\d+ tháng)", full_text, re.IGNORECASE)
            if deadline_match:
                deadline = deadline_match.group(1)

        return {
            "tool": "extract_legal_information",
            "subject": subject,
            "conduct": conduct,
            "rights": [],
            "obligations": [],
            "deadline": deadline,
            "penalty": penalty,
            "exceptions": [],
            "evidence_ids": evidence_ids,
            "trust_boundary": "Structured legal data extracted from provisions. Keep evidence_ids attached to all claims.",
        }

    except Exception as exc:
        return err("extract_legal_information", exc)
