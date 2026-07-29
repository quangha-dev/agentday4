from __future__ import annotations

import re
from difflib import SequenceMatcher

from openai import OpenAI

from app.core.config import get_settings
from app.services.cleanup import clean_page_text

SYSTEM_INSTRUCTION = """Bạn là bộ lọc hậu xử lý OCR cho văn bản pháp luật Việt Nam.
Chỉ loại bỏ ký tự rác, lỗi xuống dòng, khoảng trắng và header/footer lặp vô nghĩa.
Tuyệt đối không tóm tắt, không diễn giải, không tự bổ sung, không đổi số hiệu Điều/Khoản/Điểm,
không sửa tên riêng hoặc nội dung quy phạm khi không chắc chắn. Trả về duy nhất văn bản đã làm sạch."""


def _protected_tokens(text: str) -> set[str]:
    return set(
        re.findall(
            r"\b(?:Điều|Khoản|Điểm)\s*[\wđĐ]+|\b\d[\d./-]*\b|\b(?:NQ|NĐ|TT|QĐ)-[A-ZĐ]+\b",
            text,
            re.IGNORECASE,
        )
    )


def _preserves_legal_content(source: str, candidate: str) -> bool:
    if not candidate or len(candidate) < max(30, int(len(source) * 0.8)):
        return False
    source_tokens = {item.casefold() for item in _protected_tokens(source)}
    candidate_tokens = {item.casefold() for item in _protected_tokens(candidate)}
    if not source_tokens.issubset(candidate_tokens):
        return False
    similarity = SequenceMatcher(None, " ".join(source.split()), " ".join(candidate.split())).ratio()
    return similarity >= 0.72


def clean_with_llm(raw_text: str) -> tuple[str, str, str | None]:
    settings = get_settings()
    deterministic = clean_page_text(raw_text)
    provider = settings.llm_cleanup_provider.casefold()
    api_key = settings.openrouter_api_key if provider == "openrouter" else settings.openai_api_key
    if not api_key:
        return deterministic, "deterministic-fallback", "Chưa cấu hình API key cho LLM cleanup."

    base_url = "https://openrouter.ai/api/v1" if provider == "openrouter" else None
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=settings.llm_cleanup_model,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": deterministic},
            ],
        )
        cleaned = (response.choices[0].message.content or "").strip()
        if not _preserves_legal_content(deterministic, cleaned):
            return deterministic, "deterministic-fallback", "Kết quả LLM không đạt kiểm tra bảo toàn nội dung."
        return cleaned, f"llm:{provider}", None
    except Exception:
        return deterministic, "deterministic-fallback", "LLM không khả dụng; đã dùng bộ lọc quy tắc an toàn."
