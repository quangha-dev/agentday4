from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AuditLog, Document, DocumentChunk, LegalNode
from app.services.chunking import build_article_chunks
from app.services.embedding import get_embedder
from app.services.vector_store import get_vector_store


def index_parsed_document(db: Session, document: Document) -> dict:
    """Index a parsed, verified document using the production ver2 chunk contract."""
    nodes = list(
        db.scalars(
            select(LegalNode).where(
                LegalNode.document_id == document.id,
                LegalNode.node_type == "article",
            )
        )
    )
    if not nodes:
        raise ValueError("Hãy phân tích cấu trúc trước khi lập chỉ mục")

    store, embedder = get_vector_store(), get_embedder()
    old_chunks = list(
        db.scalars(select(DocumentChunk).where(DocumentChunk.document_id == document.id))
    )
    store.delete([chunk.point_id for chunk in old_chunks])
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))

    items: list[dict] = []
    chunk_count = 0
    for node in nodes:
        for draft in build_article_chunks(document, node):
            point_id = str(uuid.uuid4())
            db.add(
                DocumentChunk(
                    id=point_id,
                    document_id=document.id,
                    legal_node_id=node.id,
                    chunk_index=draft.chunk_index,
                    chunk_text=draft.text,
                    token_estimate=draft.token_estimate,
                    chunk_metadata=draft.metadata,
                    content_hash=draft.content_hash,
                    point_id=point_id,
                    embedding_model=embedder.model_name,
                )
            )
            items.append(
                {
                    "point_id": point_id,
                    "text": draft.embedding_text,
                    "payload": {
                        **draft.metadata,
                        "legal_text": draft.text,
                        "embedding_text": draft.embedding_text,
                        "chunk_id": point_id,
                    },
                }
            )
            chunk_count += 1

    store.upsert(items)
    for node in nodes:
        node.is_indexed = True
    document.status = "INDEXED"
    db.add(
        AuditLog(
            document_id=document.id,
            action="document.indexed",
            details={
                "articles": len(nodes),
                "chunks": chunk_count,
                "strategy": "legal-hierarchy-ver2",
                "model": embedder.model_name,
            },
        )
    )
    db.commit()
    return {
        "message": "Lập chỉ mục hoàn tất",
        "indexed_articles": len(nodes),
        "indexed_chunks": chunk_count,
        "chunk_strategy": "legal-hierarchy-ver2",
        "contract_version": "ver2",
        "model": embedder.model_name,
    }
