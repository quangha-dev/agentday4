from __future__ import annotations

import hashlib
import json
import re
import shutil
import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models import (
    AuditLog,
    Document,
    DocumentChunk,
    DocumentPage,
    LegalNode,
    ProcessingJob,
    TextRevision,
)
from app.schemas import (
    CleanupOut,
    DocumentOut,
    JobOut,
    LegalNodeOut,
    MessageOut,
    PageOut,
    SearchRequest,
    SearchResult,
    TextUpdate,
)
from app.services.chunking import build_embedding_text
from app.services.cleanup import clean_page_text
from app.services.embedding import get_embedder
from app.services.indexing import index_parsed_document
from app.services.llm_cleanup import clean_with_llm
from app.services.ocr import ocr_readiness
from app.services.vector_store import get_vector_store
from app.services.workflow import clean_document_pages, parse_document, process_document

router = APIRouter()
settings = get_settings()


def audit(db: Session, action: str, document_id: str | None = None, page_id: str | None = None, **details: object) -> None:
    db.add(AuditLog(document_id=document_id, page_id=page_id, action=action, details=details))


def get_document_or_404(db: Session, document_id: str) -> Document:
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, "Không tìm thấy tài liệu")
    return document


def page_out(page: DocumentPage) -> PageOut:
    output = PageOut.model_validate(page)
    output.image_url = f"{settings.api_prefix}/pages/{page.id}/image" if page.image_path else None
    return output


def node_out(node: LegalNode) -> LegalNodeOut:
    return LegalNodeOut(
        id=node.id,
        document_id=node.document_id,
        parent_id=node.parent_id,
        node_type=node.node_type,
        marker=node.marker,
        title=node.title,
        content=node.content,
        full_path=node.full_path,
        order_index=node.order_index,
        page_start=node.page_start,
        page_end=node.page_end,
        bbox_spans=node.bbox_spans or [],
        children=[node_out(child) for child in node.children],
    )


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "contract_version": settings.contract_version,
    }


@router.get("/system/readiness")
def system_readiness() -> dict:
    ocr = ocr_readiness(settings)
    embedder = get_embedder()
    return {
        "contract_version": settings.contract_version,
        "ready": bool(ocr["ready"] and embedder.is_semantic),
        "ocr": ocr,
        "embedding": {
            "ready": embedder.is_semantic,
            "model": embedder.model_name,
            "semantic": embedder.is_semantic,
            "vector_size": embedder.vector_size,
            "collection": settings.qdrant_collection,
        },
    }


@router.post("/documents/upload", response_model=DocumentOut, status_code=201)
def upload_document(
    file: UploadFile = File(...),
    document_number: str = Form(...),
    issued_date: date = Form(...),
    effective_date: date = Form(...),
    document_type: str = Form(...),
    issuing_authority: str = Form(...),
    signer: str = Form(...),
    summary: str = Form(...),
    db: Session = Depends(get_db),
) -> Document:
    filename = Path(file.filename or "document.pdf").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(415, "Phiên bản hiện tại chỉ hỗ trợ file PDF")
    content = file.file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File vượt quá {settings.max_upload_mb} MB")
    if not content.startswith(b"%PDF"):
        raise HTTPException(415, "Nội dung file không phải PDF hợp lệ")
    text_fields = {
        "document_number": document_number,
        "document_type": document_type,
        "issuing_authority": issuing_authority,
        "signer": signer,
        "summary": summary,
    }
    missing = [name for name, value in text_fields.items() if not value.strip()]
    if missing:
        raise HTTPException(422, "Thiếu metadata bắt buộc: " + ", ".join(missing))
    if effective_date < issued_date:
        raise HTTPException(422, "Ngày có hiệu lực không được trước ngày ban hành")
    document_number = document_number.strip()
    document_type = document_type.strip()
    issuing_authority = issuing_authority.strip()
    signer = signer.strip()
    summary = summary.strip()
    digest = hashlib.sha256(content).hexdigest()
    existing = db.scalar(select(Document).where(Document.sha256 == digest))
    if existing:
        same_metadata = all(
            (
                existing.document_number == document_number,
                existing.issued_date == issued_date,
                existing.effective_date == effective_date,
                existing.document_type == document_type,
                existing.issuing_authority == issuing_authority,
                existing.signer == signer,
                existing.summary == summary,
            )
        )
        if same_metadata:
            return existing
        raise HTTPException(
            409,
            "PDF này đã tồn tại với metadata khác. Metadata của hồ sơ đã lưu là bất biến; hãy kiểm tra lại hồ sơ hiện có.",
        )

    latest_version = db.scalar(
        select(func.max(Document.version_number)).where(
            Document.document_number == document_number
        )
    ) or 0
    previous = db.scalar(
        select(Document)
        .where(
            Document.document_number == document_number,
            Document.status == "INDEXED",
        )
        .order_by(Document.version_number.desc())
        .limit(1)
    )

    document_id = str(uuid.uuid4())
    safe_stem = re.sub(r"[^\w.-]+", "-", Path(filename).stem, flags=re.UNICODE).strip("-") or "document"
    target_dir = settings.upload_dir / document_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{safe_stem}.pdf"
    target.write_bytes(content)
    document = Document(
        id=document_id,
        title=Path(filename).stem,
        document_number=document_number,
        issued_date=issued_date,
        effective_date=effective_date,
        document_type=document_type,
        issuing_authority=issuing_authority,
        signer=signer,
        summary=summary,
        version_number=latest_version + 1,
        previous_version_id=previous.id if previous else None,
        original_filename=filename,
        stored_path=str(target.resolve()),
        sha256=digest,
    )
    db.add(document)
    db.flush()
    audit(db, "document.uploaded", document.id, filename=filename, sha256=digest)
    db.commit()
    db.refresh(document)
    return document


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)) -> list[Document]:
    return list(db.scalars(select(Document).order_by(Document.created_at.desc())))


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, db: Session = Depends(get_db)) -> Document:
    return get_document_or_404(db, document_id)


@router.delete("/documents/{document_id}", response_model=MessageOut)
def delete_document(document_id: str, db: Session = Depends(get_db)) -> MessageOut:
    document = get_document_or_404(db, document_id)
    upload_parent = Path(document.stored_path).parent
    image_parent = settings.page_image_dir / document.id
    point_ids = list(
        db.scalars(select(DocumentChunk.point_id).where(DocumentChunk.document_id == document.id))
    )
    get_vector_store().delete(point_ids)
    db.delete(document)
    db.commit()
    for path in (upload_parent, image_parent):
        if path.exists() and path.is_dir() and path.resolve().is_relative_to(Path.cwd().resolve()):
            shutil.rmtree(path)
    return MessageOut(message="Đã xóa tài liệu")


@router.get("/documents/{document_id}/file")
def get_document_file(document_id: str, db: Session = Depends(get_db)) -> FileResponse:
    document = get_document_or_404(db, document_id)
    return FileResponse(document.stored_path, media_type="application/pdf", filename=document.original_filename)


@router.post("/documents/{document_id}/process", response_model=JobOut, status_code=202)
def start_processing(
    document_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> ProcessingJob:
    document = get_document_or_404(db, document_id)
    active_job = db.scalar(
        select(ProcessingJob)
        .where(
            ProcessingJob.document_id == document.id,
            ProcessingJob.job_type == "OCR",
            ProcessingJob.status.in_(["PENDING", "RUNNING"]),
        )
        .order_by(ProcessingJob.created_at.desc())
        .limit(1)
    )
    if active_job:
        return active_job
    job = ProcessingJob(document_id=document.id, job_type="OCR")
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(process_document, job.id, document.id)
    return job


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)) -> ProcessingJob:
    job = db.get(ProcessingJob, job_id)
    if not job:
        raise HTTPException(404, "Không tìm thấy tiến trình")
    return job


@router.get("/documents/{document_id}/pages", response_model=list[PageOut])
def list_pages(document_id: str, db: Session = Depends(get_db)) -> list[PageOut]:
    get_document_or_404(db, document_id)
    pages = db.scalars(
        select(DocumentPage)
        .where(DocumentPage.document_id == document_id)
        .order_by(DocumentPage.page_number)
    )
    return [page_out(page) for page in pages]


@router.get("/pages/{page_id}", response_model=PageOut)
def get_page(page_id: str, db: Session = Depends(get_db)) -> PageOut:
    page = db.get(DocumentPage, page_id)
    if not page:
        raise HTTPException(404, "Không tìm thấy trang")
    return page_out(page)


@router.get("/pages/{page_id}/image")
def get_page_image(page_id: str, db: Session = Depends(get_db)) -> FileResponse:
    page = db.get(DocumentPage, page_id)
    if not page or not page.image_path:
        raise HTTPException(404, "Không tìm thấy ảnh trang")
    return FileResponse(page.image_path, media_type="image/png")


@router.post("/pages/{page_id}/clean", response_model=PageOut)
def clean_page(page_id: str, db: Session = Depends(get_db)) -> PageOut:
    page = db.get(DocumentPage, page_id)
    if not page:
        raise HTTPException(404, "Không tìm thấy trang")
    page.cleaned_text = clean_page_text(page.raw_text)
    page.verified_text = None
    page.is_verified = False
    db.add(TextRevision(page_id=page.id, revision_type="cleaned", content=page.cleaned_text))
    page.document.status = "CLEANED"
    audit(db, "page.cleaned", page.document_id, page.id)
    db.commit()
    db.refresh(page)
    return page_out(page)


@router.post("/pages/{page_id}/clean/llm", response_model=CleanupOut)
def clean_page_with_llm(page_id: str, db: Session = Depends(get_db)) -> CleanupOut:
    page = db.get(DocumentPage, page_id)
    if not page:
        raise HTTPException(404, "Không tìm thấy trang")
    cleaned, method, warning = clean_with_llm(page.raw_text)
    page.cleaned_text = cleaned
    page.verified_text = None
    page.is_verified = False
    page.document.status = "CLEANED"
    db.add(TextRevision(page_id=page.id, revision_type=method, content=cleaned))
    audit(db, "page.cleaned", page.document_id, page.id, method=method, warning=warning)
    db.commit()
    db.refresh(page)
    return CleanupOut(page=page_out(page), method=method, warning=warning)


@router.post("/documents/{document_id}/clean", response_model=MessageOut)
def clean_document(document_id: str, db: Session = Depends(get_db)) -> MessageOut:
    document = get_document_or_404(db, document_id)
    clean_document_pages(db, document)
    audit(db, "document.cleaned", document.id, pages=document.page_count)
    db.commit()
    return MessageOut(message="Đã tạo bản làm sạch cho toàn bộ tài liệu")


@router.patch("/pages/{page_id}/text", response_model=PageOut)
def update_page_text(page_id: str, payload: TextUpdate, db: Session = Depends(get_db)) -> PageOut:
    page = db.get(DocumentPage, page_id)
    if not page:
        raise HTTPException(404, "Không tìm thấy trang")
    page.cleaned_text = payload.content
    page.verified_text = None
    page.is_verified = False
    db.add(TextRevision(page_id=page.id, revision_type="edited", content=payload.content))
    audit(db, "page.edited", page.document_id, page.id, characters=len(payload.content))
    db.commit()
    db.refresh(page)
    return page_out(page)


@router.post("/pages/{page_id}/verify", response_model=PageOut)
def verify_page(page_id: str, payload: TextUpdate, db: Session = Depends(get_db)) -> PageOut:
    page = db.get(DocumentPage, page_id)
    if not page:
        raise HTTPException(404, "Không tìm thấy trang")
    page.verified_text = payload.content
    page.is_verified = True
    db.add(TextRevision(page_id=page.id, revision_type="verified", content=payload.content))
    audit(db, "page.verified", page.document_id, page.id, characters=len(payload.content))
    remaining = db.scalar(
        select(func.count(DocumentPage.id)).where(
            DocumentPage.document_id == page.document_id, DocumentPage.is_verified.is_(False)
        )
    )
    if remaining == 0:
        page.document.status = "REVIEWED"
    db.commit()
    db.refresh(page)
    return page_out(page)


@router.post("/documents/{document_id}/parse")
def parse_document_endpoint(document_id: str, db: Session = Depends(get_db)) -> dict:
    document = get_document_or_404(db, document_id)
    try:
        count = parse_document(db, document)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    audit(db, "document.parsed", document.id, nodes=count)
    db.commit()
    return {"message": "Phân tích cấu trúc hoàn tất", "node_count": count}


@router.get("/documents/{document_id}/tree", response_model=list[LegalNodeOut])
def get_tree(document_id: str, db: Session = Depends(get_db)) -> list[LegalNodeOut]:
    get_document_or_404(db, document_id)
    roots = db.scalars(
        select(LegalNode)
        .where(LegalNode.document_id == document_id, LegalNode.parent_id.is_(None))
        .order_by(LegalNode.order_index)
    )
    return [node_out(node) for node in roots]


@router.get("/legal-nodes/{node_id}", response_model=LegalNodeOut)
def get_legal_node(node_id: str, db: Session = Depends(get_db)) -> LegalNodeOut:
    node = db.get(LegalNode, node_id)
    if not node:
        raise HTTPException(404, "Không tìm thấy cấu trúc")
    return node_out(node)


@router.get("/documents/{document_id}/export/json")
def export_json(document_id: str, db: Session = Depends(get_db)) -> JSONResponse:
    document = get_document_or_404(db, document_id)
    roots = db.scalars(
        select(LegalNode).where(
            LegalNode.document_id == document_id, LegalNode.parent_id.is_(None)
        ).order_by(LegalNode.order_index)
    )
    payload = {
        "contract_version": settings.contract_version,
        "parser_version": "legal-structure-ver2",
        "chunk_version": "legal-hierarchy-ver2",
        "document_id": document.id,
        "title": document.title,
        "metadata": {
            "document_number": document.document_number,
            "issued_date": document.issued_date.isoformat() if document.issued_date else None,
            "effective_date": document.effective_date.isoformat() if document.effective_date else None,
            "document_type": document.document_type,
            "issuing_authority": document.issuing_authority,
            "signer": document.signer,
            "summary": document.summary,
            "version_number": document.version_number,
            "previous_version_id": document.previous_version_id,
        },
        "status": document.status,
        "pages": [
            {
                "page_number": page.page_number,
                "classification": page.classification,
                "ocr_engine": page.ocr_engine,
                "ocr_languages": page.ocr_languages,
                "confidence": page.confidence,
                "is_verified": page.is_verified,
            }
            for page in document.pages
        ],
        "structure": [node_out(node).model_dump() for node in roots],
        "chunks": [
            {
                "id": chunk.id,
                "legal_node_id": chunk.legal_node_id,
                "chunk_index": chunk.chunk_index,
                "text": chunk.chunk_text,
                "embedding_text": build_embedding_text(
                    document,
                    chunk.chunk_text,
                    list((chunk.chunk_metadata or {}).get("structural_positions") or []),
                ),
                "metadata": chunk.chunk_metadata,
            }
            for chunk in db.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document.id)
                .order_by(DocumentChunk.legal_node_id, DocumentChunk.chunk_index)
            )
        ],
    }
    target = settings.export_dir / f"{document.id}.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return JSONResponse(payload, headers={"Content-Disposition": f'attachment; filename="{document.id}.json"'})


@router.post("/documents/{document_id}/index")
def index_document(document_id: str, db: Session = Depends(get_db)) -> dict:
    document = get_document_or_404(db, document_id)
    if document.status != "PARSED":
        raise HTTPException(409, "Tài liệu phải ở trạng thái PARSED trước khi lập chỉ mục")
    unverified_count = db.scalar(
        select(func.count(DocumentPage.id)).where(
            DocumentPage.document_id == document.id,
            DocumentPage.is_verified.is_(False),
        )
    )
    if unverified_count:
        raise HTTPException(409, "Không thể index khi còn trang chưa xác nhận")
    try:
        return index_parsed_document(db, document)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


def _sql_search(payload: SearchRequest, db: Session) -> list[SearchResult]:
    query = select(LegalNode, Document).join(Document, Document.id == LegalNode.document_id)
    if payload.document_id:
        query = query.where(LegalNode.document_id == payload.document_id)
    term = payload.query.strip()
    if payload.mode == "exact":
        number_match = re.search(r"(?:điều|dieu)\s*(\d+[a-z]?)", term, re.IGNORECASE)
        if number_match:
            query = query.where(
                LegalNode.node_type == "article", func.lower(LegalNode.marker) == number_match.group(1).lower()
            )
        else:
            query = query.where(or_(LegalNode.title.ilike(f"%{term}%"), LegalNode.full_path.ilike(f"%{term}%")))
    else:
        query = query.where(or_(LegalNode.content.ilike(f"%{term}%"), LegalNode.title.ilike(f"%{term}%")))
    rows = db.execute(query.limit(payload.limit)).all()
    return [
        SearchResult(
            legal_node_id=node.id,
            document_id=document.id,
            document_title=document.title,
            node_type=node.node_type,
            marker=node.marker,
            title=node.title,
            content=node.content,
            full_path=node.full_path,
            page_start=node.page_start,
            page_end=node.page_end,
            score=1.0,
        )
        for node, document in rows
    ]


@router.post("/search", response_model=list[SearchResult])
def search(payload: SearchRequest, db: Session = Depends(get_db)) -> list[SearchResult]:
    if payload.mode in {"exact", "keyword"}:
        return _sql_search(payload, db)
    semantic = get_vector_store().search(payload.query, payload.limit, payload.document_id)
    results = [
        SearchResult(
            **{
                **item,
                "content": item.get("legal_text") or item.get("content") or "",
            }
        )
        for item in semantic
    ]
    if payload.mode == "hybrid":
        lexical = _sql_search(payload.model_copy(update={"mode": "keyword"}), db)
        seen = {item.legal_node_id for item in results}
        results.extend(item for item in lexical if item.legal_node_id not in seen)
        results = results[: payload.limit]
    return results
