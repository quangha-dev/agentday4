from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Document, DocumentChunk, DocumentPage, LegalNode, TextRevision
from app.services.indexing import index_parsed_document
from app.services.vector_store import get_vector_store
from app.services.workflow import parse_document


def _load_fixture(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not payload.get("dataset_id") or not payload.get("metadata") or not payload.get("pages"):
        raise ValueError("Mock fixture phải có dataset_id, metadata và pages")
    return payload


def _fixture_hash(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(b"lexflow-mock-ver2:" + canonical).hexdigest()


def _search_preview(document_id: str, query: str) -> list[dict]:
    hits = get_vector_store().search(query, limit=3, document_id=document_id)
    return [
        {
            "score": round(float(item.get("score", 0)), 4),
            "full_path": item.get("full_path"),
            "page_start": item.get("page_start"),
            "legal_text": item.get("legal_text"),
        }
        for item in hits
    ]


def seed_mock_document(
    db: Session,
    fixture_path: Path,
    *,
    rebuild: bool = False,
    query: str = "thời hạn thông báo sự cố dữ liệu",
) -> dict:
    """Create verified pages from fixture text, parse and index without invoking OCR."""
    fixture_path = fixture_path.resolve()
    if not fixture_path.is_file():
        raise ValueError(f"Không tìm thấy mock fixture: {fixture_path}")
    payload = _load_fixture(fixture_path)
    source_hash = _fixture_hash(payload)
    metadata = payload["metadata"]
    existing = db.scalar(select(Document).where(Document.sha256 == source_hash))
    if not existing:
        existing = db.scalar(
            select(Document).where(
                Document.document_number == str(metadata["document_number"]),
                Document.version_number == int(metadata.get("version_number", 1)),
            )
        )

    if existing and not rebuild:
        if existing.status != "INDEXED":
            raise ValueError("Mock đã tồn tại nhưng chưa index xong; chạy lại với rebuild=true")
        return {
            "ok": True,
            "created": False,
            "bypassed_ocr": True,
            "contract_version": "ver2",
            "document_id": existing.id,
            "document_number": existing.document_number,
            "status": existing.status,
            "page_count": existing.page_count,
            "search_query": query,
            "search_preview": _search_preview(existing.id, query),
        }

    if existing:
        point_ids = list(
            db.scalars(
                select(DocumentChunk.point_id).where(DocumentChunk.document_id == existing.id)
            )
        )
        get_vector_store().delete(point_ids)
        db.delete(existing)
        db.commit()

    pages = sorted(payload["pages"], key=lambda item: int(item["page_number"]))
    document = Document(
        title=str(metadata["title"]),
        document_number=str(metadata["document_number"]),
        issued_date=date.fromisoformat(metadata["issued_date"]),
        effective_date=date.fromisoformat(metadata["effective_date"]),
        document_type=str(metadata["document_type"]),
        issuing_authority=str(metadata["issuing_authority"]),
        signer=str(metadata["signer"]),
        summary=str(metadata["summary"]),
        version_number=int(metadata.get("version_number", 1)),
        original_filename=fixture_path.name,
        stored_path=str(fixture_path),
        sha256=source_hash,
        mime_type="application/json",
        status="MOCK_TEXT_READY",
        page_count=len(pages),
    )
    db.add(document)
    db.flush()

    for item in pages:
        text = str(item["text"]).strip()
        if not text:
            raise ValueError(f"Mock text rỗng tại trang {item['page_number']}")
        page = DocumentPage(
            document_id=document.id,
            page_number=int(item["page_number"]),
            classification="mock_text",
            ocr_engine="mock-direct/ver2",
            ocr_languages="vie",
            raw_text=text,
            cleaned_text=text,
            verified_text=text,
            confidence=100.0,
            bounding_boxes=[],
            is_verified=True,
        )
        db.add(page)
        db.flush()
        db.add(TextRevision(page_id=page.id, revision_type="mock_verified", content=text))

    db.add(
        AuditLog(
            document_id=document.id,
            action="mock.seeded",
            details={
                "dataset_id": payload["dataset_id"],
                "fixture": str(fixture_path),
                "bypassed_ocr": True,
                "contract_version": "ver2",
            },
        )
    )
    db.commit()

    try:
        node_count = parse_document(db, document)
        index_result = index_parsed_document(db, document)
    except Exception:
        db.rollback()
        raise

    nodes = list(db.scalars(select(LegalNode).where(LegalNode.document_id == document.id)))
    node_types = Counter(node.node_type for node in nodes)
    return {
        "ok": True,
        "created": True,
        "bypassed_ocr": True,
        "contract_version": "ver2",
        "document_id": document.id,
        "document_number": document.document_number,
        "status": document.status,
        "page_count": document.page_count,
        "node_count": node_count,
        "node_types": dict(sorted(node_types.items())),
        **index_result,
        "search_query": query,
        "search_preview": _search_preview(document.id, query),
        "suggested_questions": [
            "Theo MOCK-01/2026/QC-LF, dữ liệu thử nghiệm được lưu tối đa bao lâu?",
            "Điều 4 của MOCK-01/2026/QC-LF quy định thời hạn thông báo sự cố thế nào?",
        ],
    }
