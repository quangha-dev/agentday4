import re
import unicodedata
from collections import Counter

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SPACES = re.compile(r"[ \t]+")
JUNK_RUN = re.compile(r"([^\w\sÀ-ỹ])\1{4,}", re.UNICODE)


def clean_page_text(text: str, repeated_lines: set[str] | None = None) -> str:
    """Conservative cleanup. The raw OCR text is never mutated by this function."""
    normalized = unicodedata.normalize("NFC", text or "")
    normalized = CONTROL_CHARS.sub("", normalized).replace("\r\n", "\n").replace("\r", "\n")
    repeated_lines = repeated_lines or set()
    output: list[str] = []

    for original_line in normalized.splitlines():
        line = SPACES.sub(" ", original_line).strip()
        if not line:
            if output and output[-1] != "":
                output.append("")
            continue
        if line.casefold() in repeated_lines:
            continue
        if re.fullmatch(r"[-–—•·._\s]*\d{1,4}[-–—•·._\s]*", line):
            continue
        line = JUNK_RUN.sub(lambda match: match.group(1) * 2, line)
        output.append(line)

    # Join words split by OCR line wrapping, but preserve legal headings and paragraph breaks.
    joined: list[str] = []
    for line in output:
        if (
            joined
            and line
            and joined[-1].endswith("-")
            and re.match(r"^[a-zà-ỹ]", line, re.IGNORECASE)
        ):
            joined[-1] = joined[-1][:-1] + line
        else:
            joined.append(line)
    return "\n".join(joined).strip()


def find_repeated_margin_lines(page_texts: list[str]) -> set[str]:
    if len(page_texts) < 3:
        return set()
    candidates: list[str] = []
    for text in page_texts:
        lines = [SPACES.sub(" ", line).strip() for line in text.splitlines() if line.strip()]
        candidates.extend(line.casefold() for line in (lines[:2] + lines[-2:]) if 3 < len(line) < 160)
    threshold = max(3, int(len(page_texts) * 0.6))
    return {line for line, count in Counter(candidates).items() if count >= threshold}

