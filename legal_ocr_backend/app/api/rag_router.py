from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas import (
    CitationExtractionRequest,
    CitationValidationRequest,
    CompareLegalRequest,
    EffectiveStatusRequest,
    ExactProvisionRequest,
    RagSearchRequest,
    ResolveDocumentRequest,
)
from app.services.embedding import get_embedder
from app.services.rag import (
    compare_provisions,
    effective_status,
    extract_citation_information,
    provision_evidence,
    resolve_documents,
    search_evidence,
    validate_claims,
)

router = APIRouter(prefix="/rag", tags=["RAG tools"])
settings = get_settings()


@router.post("/search")
def rag_search(payload: RagSearchRequest, db: Session = Depends(get_db)) -> dict:
    evidence = search_evidence(db, **payload.model_dump())
    embedder = get_embedder()
    return {
        "tool": "legal_rag_search",
        "ok": True,
        "query": payload.query,
        "count": len(evidence),
        "results": evidence,
        "evidence": evidence,
        "retrieval": {
            "engine": "qdrant+sql",
            "mode": "hybrid_semantic_keyword" if embedder.is_semantic else "hybrid_hash_keyword",
            "embedding_model": embedder.model_name,
            "semantic": embedder.is_semantic,
            "min_score": settings.rag_min_score,
            "top_k": payload.top_k,
        },
        "contract_version": "ver2",
    }


@router.post("/documents/resolve")
def resolve_document(payload: ResolveDocumentRequest, db: Session = Depends(get_db)) -> dict:
    documents = resolve_documents(db, **payload.model_dump())
    return {
        "tool": "resolve_legal_document",
        "ok": True,
        "contract_version": "ver2",
        "count": len(documents),
        "documents": documents,
        "evidence": [],
    }


@router.post("/provision")
def exact_provision(payload: ExactProvisionRequest, db: Session = Depends(get_db)) -> dict:
    evidence = provision_evidence(db, **payload.model_dump())
    return {
        "tool": "get_legal_provision",
        "ok": True,
        "contract_version": "ver2",
        "found": evidence is not None,
        **(evidence or payload.model_dump()),
        "evidence": [evidence] if evidence else [],
    }


@router.post("/effective-status")
def get_effective_status(payload: EffectiveStatusRequest, db: Session = Depends(get_db)) -> dict:
    result = effective_status(db, document_id=payload.document_id, target_date=payload.target_date)
    fallback = {
        "document_id": payload.document_id,
        "target_date": payload.target_date.isoformat(),
        "status": "unknown",
    }
    return {
        "tool": "check_effective_status",
        "ok": True,
        "contract_version": "ver2",
        **(result or fallback),
    }


@router.post("/compare")
def compare(payload: CompareLegalRequest, db: Session = Depends(get_db)) -> dict:
    result = compare_provisions(db, **payload.model_dump())
    return {
        "tool": "compare_legal_versions",
        "ok": True,
        "contract_version": "ver2",
        **payload.model_dump(),
        **result,
        "evidence": [item for item in (result["old_document"], result["new_document"]) if item],
    }


@router.post("/citations/validate")
def validate(payload: CitationValidationRequest, db: Session = Depends(get_db)) -> dict:
    result = validate_claims(
        db,
        claims=[item.model_dump() for item in payload.claims],
        target_date=payload.target_date,
    )
    return {
        "tool": "validate_citation",
        "ok": True,
        "target_date": payload.target_date.isoformat(),
        **result,
        "contract_version": "ver2",
    }


@router.post("/extract")
def extract(payload: CitationExtractionRequest, db: Session = Depends(get_db)) -> dict:
    return {
        "tool": "extract_legal_information",
        "ok": True,
        "contract_version": "ver2",
        **extract_citation_information(db, **payload.model_dump()),
    }
