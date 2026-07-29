from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from app.models import Document, LegalNode

MAX_CHARS = 4_500
OVERLAP_CHARS = 240


@dataclass
class ChunkDraft:
    legal_node_id: str
    chunk_index: int
    text: str
    embedding_text: str
    metadata: dict

    @property
    def token_estimate(self) -> int:
        return max(1, len(self.text) // 4)

    @property
    def content_hash(self) -> str:
        return sha256(self.text.encode("utf-8")).hexdigest()


def build_embedding_context(document: Document, structural_positions: list[str]) -> str:
    fields = [
        document.document_type,
        document.document_number,
        document.title,
        document.summary,
        " / ".join(structural_positions),
    ]
    return "\n".join(str(value).strip() for value in fields if value and str(value).strip())


def build_embedding_text(document: Document, text: str, structural_positions: list[str]) -> str:
    return f"{build_embedding_context(document, structural_positions)}\n\n{text}".strip()


def _descendant_blocks(node: LegalNode) -> list[tuple[str, int, int, str]]:
    blocks: list[tuple[str, int, int, str]] = []
    for child in sorted(node.children, key=lambda item: item.order_index):
        heading = " ".join(part for part in (child.full_path, child.title) if part)
        text = "\n".join(part for part in (heading, child.content) if part).strip()
        if text:
            blocks.append((text, child.page_start, child.page_end, child.full_path))
        blocks.extend(_descendant_blocks(child))
    return blocks


def _split_oversized(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    cursor = 0
    while cursor < len(text):
        end = min(len(text), cursor + max_chars)
        if end < len(text):
            boundary = max(text.rfind("\n", cursor, end), text.rfind(". ", cursor, end))
            if boundary > cursor + max_chars // 2:
                end = boundary + 1
        chunks.append(text[cursor:end].strip())
        if end >= len(text):
            break
        cursor = max(cursor + 1, end - OVERLAP_CHARS)
    return [item for item in chunks if item]


def build_article_chunks(document: Document, article: LegalNode) -> list[ChunkDraft]:
    """ver2 hierarchy chunks with legal text separated from metadata and embedding context."""
    article_heading = "\n".join(
        part for part in (article.full_path, article.title, article.content) if part
    ).strip()
    blocks = [
        (article_heading, article.page_start, article.page_end, article.full_path)
    ] + _descendant_blocks(article)
    normalized: list[tuple[str, int, int, str]] = []
    for text, page_start, page_end, structural_position in blocks:
        for part in _split_oversized(text):
            normalized.append((part, page_start, page_end, structural_position))

    groups: list[list[tuple[str, int, int, str]]] = []
    current: list[tuple[str, int, int, str]] = []
    current_size = 0
    for block in normalized:
        projected = current_size + len(block[0]) + 2
        if current and projected > MAX_CHARS:
            groups.append(current)
            current, current_size = [], 0
        current.append(block)
        current_size += len(block[0]) + 2
    if current:
        groups.append(current)

    drafts: list[ChunkDraft] = []
    for index, group in enumerate(groups):
        body = "\n\n".join(item[0] for item in group)
        page_start = min(item[1] for item in group)
        page_end = max(item[2] for item in group)
        structural_positions = list(dict.fromkeys(item[3] for item in group if item[3]))
        text = body.strip()
        embedding_text = build_embedding_text(document, text, structural_positions)
        metadata = {
            "contract_version": "ver2",
            "document_id": document.id,
            "document_title": document.title,
            "document_number": document.document_number,
            "issued_date": document.issued_date.isoformat() if document.issued_date else None,
            "effective_date": document.effective_date.isoformat() if document.effective_date else None,
            "document_type": document.document_type,
            "issuing_authority": document.issuing_authority,
            "signer": document.signer,
            "summary": document.summary,
            "version_number": document.version_number,
            "legal_node_id": article.id,
            "node_type": article.node_type,
            "marker": article.marker,
            "title": article.title,
            "full_path": article.full_path,
            "structural_positions": structural_positions,
            "page_start": page_start,
            "page_end": page_end,
            "chunk_index": index,
            "chunk_strategy": "legal-hierarchy-ver2",
        }
        drafts.append(ChunkDraft(article.id, index, text, embedding_text, metadata))
    return drafts
