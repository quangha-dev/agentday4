from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class PageText:
    page_number: int
    text: str
    offset_start: int = 0
    offset_end: int = 0


PATTERNS: list[tuple[str, int, re.Pattern[str]]] = [
    ("part", 1, re.compile(r"^\s*PH[ẦA]N\s+([IVXLCDM\d]+)\s*[:.\-]?\s*(.*)$", re.IGNORECASE)),
    ("chapter", 2, re.compile(r"^\s*CH[ƯU][ƠO]NG\s+([IVXLCDM\d]+)\s*[:.\-]?\s*(.*)$", re.IGNORECASE)),
    ("section", 3, re.compile(r"^\s*M[ỤU]C\s+([IVXLCDM\d]+)\s*[:.\-]?\s*(.*)$", re.IGNORECASE)),
    ("subsection", 4, re.compile(r"^\s*TI[ỂE]U\s+M[ỤU]C\s+([IVXLCDM\d]+)\s*[:.\-]?\s*(.*)$", re.IGNORECASE)),
    ("article", 5, re.compile(r"^\s*(?:ĐIỀU|D[I1][EỀ]U)\s+(\d+[a-zA-Z]?)\s*[.:\-]?\s*(.*)$", re.IGNORECASE)),
    ("clause", 6, re.compile(r"^\s*(\d{1,3})\s*[.)]\s+(.+)$", re.IGNORECASE)),
    ("point", 7, re.compile(r"^\s*([a-zđ])\s*[.)]\s+(.+)$", re.IGNORECASE)),
]

LABELS = {
    "part": "Phần",
    "chapter": "Chương",
    "section": "Mục",
    "subsection": "Tiểu mục",
    "article": "Điều",
    "clause": "Khoản",
    "point": "Điểm",
}


def combine_pages(pages: list[PageText]) -> tuple[str, list[PageText]]:
    chunks: list[str] = []
    cursor = 0
    for page in pages:
        page.offset_start = cursor
        chunks.append(page.text)
        cursor += len(page.text)
        page.offset_end = cursor
        chunks.append("\n")
        cursor += 1
    return "".join(chunks), pages


def locate_page(offset: int, pages: list[PageText]) -> int:
    for page in pages:
        if page.offset_start <= offset <= page.offset_end:
            return page.page_number
    return pages[-1].page_number if pages else 1


def parse_legal_structure(pages: list[PageText]) -> list[dict]:
    full_text, mapped_pages = combine_pages(pages)
    matches: list[dict] = []
    article_seen = False
    clause_seen = False

    for line_match in re.finditer(r"^.*$", full_text, re.MULTILINE):
        line = line_match.group(0).strip()
        if not line:
            continue
        for node_type, rank, pattern in PATTERNS:
            if node_type == "clause" and not article_seen:
                continue
            if node_type == "point" and not (article_seen and clause_seen):
                continue
            match = pattern.match(line)
            if not match:
                continue
            marker, title = match.group(1).strip(), match.group(2).strip()
            matches.append(
                {
                    "node_type": node_type,
                    "rank": rank,
                    "marker": marker,
                    "title": title or None,
                    "char_start": line_match.start(),
                    "heading_end": line_match.end(),
                }
            )
            if node_type == "article":
                article_seen, clause_seen = True, False
            elif node_type == "clause":
                clause_seen = True
            elif rank < 5:
                article_seen, clause_seen = False, False
            break

    if not matches and full_text.strip():
        matches.append(
            {
                "node_type": "document_content",
                "rank": 0,
                "marker": None,
                "title": "Nội dung văn bản",
                "char_start": 0,
                "heading_end": 0,
            }
        )

    stack: list[dict] = []
    roots: list[dict] = []
    for index, item in enumerate(matches):
        end = matches[index + 1]["char_start"] if index + 1 < len(matches) else len(full_text)
        item["char_end"] = end
        item["content"] = full_text[item["heading_end"] : end].strip()
        item["page_start"] = locate_page(item["char_start"], mapped_pages)
        item["page_end"] = locate_page(max(item["char_start"], end - 1), mapped_pages)
        item["children"] = []
        item["order_index"] = index

        while stack and stack[-1]["rank"] >= item["rank"]:
            stack.pop()
        if stack:
            stack[-1]["children"].append(item)
            item["parent"] = stack[-1]
        else:
            roots.append(item)
            item["parent"] = None
        stack.append(item)

    def add_paths(nodes: list[dict], parent_path: str = "") -> None:
        for node in nodes:
            label = LABELS.get(node["node_type"], "Nội dung")
            segment = f"{label} {node['marker']}".strip() if node["marker"] else label
            node["full_path"] = " / ".join(part for part in (parent_path, segment) if part)
            add_paths(node["children"], node["full_path"])

    add_paths(roots)
    return roots
