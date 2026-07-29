from pathlib import Path

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import (
    AuditLog,
    Document,
    DocumentPage,
    LegalNode,
    OcrRun,
    ProcessingJob,
    SourceSpan,
    TextRevision,
    utcnow,
)
from app.services.cleanup import clean_page_text, find_repeated_margin_lines
from app.services.ocr import extract_pdf
from app.services.parser import PageText, parse_legal_structure


def process_document(job_id: str, document_id: str) -> None:
    settings = get_settings()
    with SessionLocal() as db:
        job = db.get(ProcessingJob, job_id)
        document = db.get(Document, document_id)
        if not job or not document:
            return
        job.status, document.status = "RUNNING", "EXTRACTING"
        job.progress, job.message = 5, "Đang đọc và phân loại các trang PDF"
        ocr_run = OcrRun(document_id=document.id, languages=settings.ocr_languages)
        db.add(ocr_run)
        db.commit()
        try:
            results = extract_pdf(
                Path(document.stored_path), settings.page_image_dir / document.id, settings
            )
            db.execute(delete(DocumentPage).where(DocumentPage.document_id == document.id))
            for index, result in enumerate(results):
                page = DocumentPage(document_id=document.id, **result)
                db.add(page)
                job.progress = 10 + int(((index + 1) / max(1, len(results))) * 80)
                job.message = f"Đã xử lý trang {index + 1}/{len(results)}"
                db.flush()
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
    db.execute(delete(LegalNode).where(LegalNode.document_id == document.id))
    parsed = parse_legal_structure(
        [PageText(page_number=page.page_number, text=page.canonical_text) for page in pages]
    )
    _persist_nodes(db, document.id, parsed)
    document.status = "PARSED"
    db.flush()
    return len(list(db.scalars(select(LegalNode).where(LegalNode.document_id == document.id))))
