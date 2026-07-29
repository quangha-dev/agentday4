from pathlib import Path

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import (
    AuditLog,
    Document,
    DocumentChunk,
    DocumentPage,
    LegalNode,
    OcrRun,
    ProcessingJob,
    SourceSpan,
    TextRevision,
    utcnow,
)
from app.services.cleanup import clean_page_text, find_repeated_margin_lines
from app.services.ocr import OcrError, extract_pdf
from app.services.parser import PageText, parse_legal_structure
from app.services.vector_store import get_vector_store


def process_document(job_id: str, document_id: str) -> None:
    settings = get_settings()
    with SessionLocal() as db:
        job = db.get(ProcessingJob, job_id)
        document = db.get(Document, document_id)
        if not job or not document:
            return
        job.status, document.status = "RUNNING", "EXTRACTING"
        job.progress, job.message = 5, "Đang đọc và phân loại các trang PDF"
        ocr_run = OcrRun(
            document_id=document.id,
            engine="PyMuPDF+Tesseract/ver2",
            languages=settings.ocr_languages,
        )
        db.add(ocr_run)
        old_points = list(
            db.scalars(select(DocumentChunk.point_id).where(DocumentChunk.document_id == document.id))
        )
        get_vector_store().delete(old_points)
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        db.execute(delete(LegalNode).where(LegalNode.document_id == document.id))
        db.execute(delete(DocumentPage).where(DocumentPage.document_id == document.id))
        document.page_count = 0
        document.error_message = None
        db.commit()
        try:
            def persist_page(result: dict, page_number: int, total_pages: int) -> None:
                page = DocumentPage(document_id=document.id, **result)
                db.add(page)
                document.page_count = page_number
                job.progress = 10 + int((page_number / max(1, total_pages)) * 85)
                job.message = f"Đã OCR trang {page_number}/{total_pages}"
                ocr_run.page_count = page_number
                db.commit()

            results = extract_pdf(
                Path(document.stored_path),
                settings.page_image_dir / document.id,
                settings,
                on_page=persist_page,
            )
            document.page_count = len(results)
            document.status = "OCR_READY"
            document.error_message = None
            ocr_run.status, ocr_run.page_count, ocr_run.completed_at = "COMPLETED", len(results), utcnow()
            db.add(AuditLog(document_id=document.id, action="ocr.completed", details={"pages": len(results)}))
            job.status, job.progress, job.message = "COMPLETED", 100, "OCR hoàn tất"
            db.commit()
        except Exception as exc:
            document.status = "FAILED"
            document.error_message = str(exc)
            ocr_run.status, ocr_run.error_message, ocr_run.completed_at = "FAILED", str(exc), utcnow()
            job.status, job.message = "FAILED", str(exc)
            details = {"code": getattr(exc, "code", type(exc).__name__)}
            if isinstance(exc, OcrError) and exc.page_number:
                details["page_number"] = exc.page_number
            db.add(AuditLog(document_id=document.id, action="ocr.failed", details=details))
            db.commit()


def clean_document_pages(db, document: Document) -> None:
    pages = list(
        db.scalars(
            select(DocumentPage)
            .where(DocumentPage.document_id == document.id)
            .order_by(DocumentPage.page_number)
        )
    )
    repeated = find_repeated_margin_lines([page.raw_text for page in pages])
    for page in pages:
        page.cleaned_text = clean_page_text(page.raw_text, repeated)
        page.verified_text = None
        page.is_verified = False
        db.add(TextRevision(page_id=page.id, revision_type="cleaned", content=page.cleaned_text))
    document.status = "CLEANED"


def _persist_nodes(db, document_id: str, parsed: list[dict], parent_id: str | None = None) -> None:
    for item in parsed:
        node = LegalNode(
            document_id=document_id,
            parent_id=parent_id,
            node_type=item["node_type"],
            marker=item["marker"],
            title=item["title"],
            content=item["content"],
            full_path=item["full_path"],
            order_index=item["order_index"],
            page_start=item["page_start"],
            page_end=item["page_end"],
            char_start=item["char_start"],
            char_end=item["char_end"],
            bbox_spans=[],
        )
        db.add(node)
        db.flush()
        db.add(
            SourceSpan(
                legal_node_id=node.id,
                page_start=node.page_start,
                page_end=node.page_end,
                char_start=node.char_start,
                char_end=node.char_end,
                bounding_boxes=node.bbox_spans,
            )
        )
        _persist_nodes(db, document_id, item["children"], node.id)


def parse_document(db, document: Document) -> int:
    pages = list(
        db.scalars(
            select(DocumentPage)
            .where(DocumentPage.document_id == document.id)
            .order_by(DocumentPage.page_number)
        )
    )
    if not pages:
        raise ValueError("Tài liệu chưa có dữ liệu OCR")
    unverified = [page.page_number for page in pages if not page.is_verified]
    if unverified:
        preview = ", ".join(str(item) for item in unverified[:10])
        suffix = "…" if len(unverified) > 10 else ""
        raise ValueError(f"Cần xác nhận toàn bộ trang trước khi parse. Chưa xác nhận: {preview}{suffix}")
    empty_pages = [page.page_number for page in pages if not page.canonical_text.strip()]
    if empty_pages:
        raise ValueError("Canonical text rỗng tại trang: " + ", ".join(map(str, empty_pages)))
    db.execute(delete(LegalNode).where(LegalNode.document_id == document.id))
    parsed = parse_legal_structure(
        [PageText(page_number=page.page_number, text=page.canonical_text) for page in pages]
    )
    _persist_nodes(db, document.id, parsed)
    document.status = "PARSED"
    db.flush()
    return len(list(db.scalars(select(LegalNode).where(LegalNode.document_id == document.id))))
