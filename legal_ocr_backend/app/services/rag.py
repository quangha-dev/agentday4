from __future__ import annotations

import difflib
import re
import unicodedata
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Document, DocumentChunk, LegalNode
from app.services.embedding import get_embedder
from app.services.vector_store import get_vector_store

settings = get_settings()
ACTIVE_DOCUMENT_STATUSES = {"INDEXED"}


def _fold(value: object) -> str:
    text = unicodedata.normalize("NFD", str(value or "").casefold())
    return "".join(character for character in text if unicodedata.category(character) != "Mn").replace("đ", "d")


def _terms(value: object) -> set[str]:
    ignored = {"ban", "cho", "co", "cua", "duoc", "la", "mot", "nay", "the", "thi", "trong", "va", "ve", "voi"}
    return {item for item in re.findall(r"[a-z0-9]+", _fold(value)) if len(item) > 1 and item not in ignored}


def _split_identifier(identifier: str) -> tuple[str, int | None]:
    match = re.match(r"^(.*)@v(\d+)$", identifier.strip(), re.IGNORECASE)
    return (match.group(1).strip(), int(match.group(2))) if match else (identifier.strip(), None)


def _is_ver2_chunk(chunk: DocumentChunk) -> bool:
    return str((chunk.chunk_metadata or {}).get("contract_version") or "") == settings.contract_version


def _is_ver2_document(db: Session, document_id: str) -> bool:
    chunks = db.scalars(
        select(DocumentChunk).where(DocumentChunk.document_id == document_id).limit(50)
    )
    return any(_is_ver2_chunk(chunk) for chunk in chunks)


def _latest_ver2_version(db: Session, document_number: str) -> int | None:
    documents = db.scalars(
        select(Document)
        .where(
            Document.document_number == document_number,
            Document.status.in_(ACTIVE_DOCUMENT_STATUSES),
        )
        .order_by(Document.version_number.desc())
    )
    document = next((item for item in documents if _is_ver2_document(db, item.id)), None)
    return document.version_number if document else None


def find_document(db: Session, identifier: str) -> Document | None:
    value, version = _split_identifier(identifier)
    query = select(Document).where(
        Document.status.in_(ACTIVE_DOCUMENT_STATUSES),
        or_(
            Document.id == value,
            func.lower(Document.document_number) == value.casefold(),
            func.lower(Document.title) == value.casefold(),
        )
    )
    if version is not None:
        query = query.where(Document.version_number == version)
    documents = db.scalars(query.order_by(Document.version_number.desc()).limit(50))
    return next((document for document in documents if _is_ver2_document(db, document.id)), None)


def _source_url(document_id: str, page: int) -> str:
    return f"{settings.public_api_base_url}/documents/{document_id}/file#page={page}&view=FitH"


def _effective_status(db: Session, document: Document, target: date) -> dict[str, Any]:
    if document.status not in ACTIVE_DOCUMENT_STATUSES:
        return {
            "status": "unavailable",
            "effective_from": document.effective_date.isoformat() if document.effective_date else None,
            "effective_to": None,
            "replaced_by": None,
            "replaced_by_version": None,
        }
    newer_documents = db.scalars(
        select(Document)
        .where(
            Document.document_number == document.document_number,
            Document.version_number > document.version_number,
            Document.status.in_(ACTIVE_DOCUMENT_STATUSES),
            Document.effective_date.is_not(None),
            Document.effective_date <= target,
        )
        .order_by(Document.version_number.desc())
    )
    newer = next((item for item in newer_documents if _is_ver2_document(db, item.id)), None)
    if document.effective_date and target < document.effective_date:
        status = "not_yet_effective"
    elif newer:
        status = "replaced"
    else:
        status = "effective"
    effective_to = newer.effective_date - timedelta(days=1) if newer and newer.effective_date else None
    return {
        "status": status,
        "effective_from": document.effective_date.isoformat() if document.effective_date else None,
        "effective_to": effective_to.isoformat() if effective_to else None,
        "replaced_by": newer.id if newer else None,
        "replaced_by_version": newer.version_number if newer else None,
    }


def _node_is_descendant(node: LegalNode, ancestor_id: str, by_id: dict[str, LegalNode]) -> bool:
    cursor: LegalNode | None = node
    while cursor and cursor.parent_id:
        if cursor.parent_id == ancestor_id:
            return True
        cursor = by_id.get(cursor.parent_id)
    return False


def find_provision_node(
    db: Session,
    document: Document,
    article: str,
    clause: str | None = None,
    point: str | None = None,
) -> tuple[LegalNode | None, list[LegalNode]]:
    nodes = list(
        db.scalars(
            select(LegalNode)
            .where(LegalNode.document_id == document.id)
            .order_by(LegalNode.order_index)
        )
    )
    by_id = {node.id: node for node in nodes}
    article_node = next(
        (node for node in nodes if node.node_type == "article" and _fold(node.marker) == _fold(article)),
        None,
    )
    if not article_node:
        return None, nodes
    selected = article_node
    if clause:
        selected = next(
            (
                node
                for node in nodes
                if node.node_type == "clause"
                and _fold(node.marker) == _fold(clause)
                and _node_is_descendant(node, article_node.id, by_id)
            ),
            None,
        )
        if not selected:
            return None, nodes
    if point:
        parent = selected
        selected = next(
            (
                node
                for node in nodes
                if node.node_type == "point"
                and _fold(node.marker) == _fold(point)
                and _node_is_descendant(node, parent.id, by_id)
            ),
            None,
        )
    return selected, nodes


def _node_content(node: LegalNode, nodes: list[LegalNode]) -> str:
    by_id = {item.id: item for item in nodes}
    selected = [item for item in nodes if item.id == node.id or _node_is_descendant(item, node.id, by_id)]
    parts: list[str] = []
    for item in selected:
        heading = " ".join(part for part in (item.full_path, item.title) if part)
        text = "\n".join(part for part in (heading, item.content) if part).strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def _marker_from_path(path: str, label: str) -> str | None:
    match = re.search(rf"(?:^|/)\s*{label}\s+([^/]+)", path or "", re.IGNORECASE)
    return match.group(1).strip() if match else None


def node_evidence(document: Document, node: LegalNode, nodes: list[LegalNode]) -> dict[str, Any]:
    return {
        "citation_id": node.id,
        "retrieval_type": "exact",
        "document_id": document.id,
        "document_number": document.document_number,
        "document_title": document.title,
        "document_type": document.document_type,
        "version_number": document.version_number,
        "article": node.marker if node.node_type == "article" else _marker_from_path(node.full_path, "Điều"),
        "clause": node.marker if node.node_type == "clause" else _marker_from_path(node.full_path, "Khoản"),
        "point": node.marker if node.node_type == "point" else _marker_from_path(node.full_path, "Điểm"),
        "full_path": node.full_path,
        "content": _node_content(node, nodes),
        "page_start": node.page_start,
        "page_end": node.page_end,
        "issued_date": document.issued_date.isoformat() if document.issued_date else None,
        "effective_from": document.effective_date.isoformat() if document.effective_date else None,
        "effective_to": None,
        "source_url": _source_url(document.id, node.page_start),
        "score": 1.0,
    }


def document_evidence(document: Document, nodes: list[LegalNode]) -> dict[str, Any]:
    content = "\n\n".join(
        "\n".join(part for part in (node.full_path, node.title, node.content) if part).strip()
        for node in nodes
        if node.full_path or node.title or node.content
    )
    page_start = min((node.page_start for node in nodes), default=1)
    page_end = max((node.page_end for node in nodes), default=max(document.page_count, 1))
    return {
        "citation_id": f"document:{document.id}",
        "retrieval_type": "document_version",
        "document_id": document.id,
        "document_number": document.document_number,
        "document_title": document.title,
        "document_type": document.document_type,
        "version_number": document.version_number,
        "article": None,
        "clause": None,
        "point": None,
        "full_path": "Toàn văn",
        "content": content,
        "page_start": page_start,
        "page_end": page_end,
        "issued_date": document.issued_date.isoformat() if document.issued_date else None,
        "effective_from": document.effective_date.isoformat() if document.effective_date else None,
        "effective_to": None,
        "source_url": _source_url(document.id, page_start),
        "score": 1.0,
    }


def search_evidence(
    db: Session,
    *,
    query: str,
    document_type: str = "all",
    legal_domain: str = "all",
    document_number: str | None = None,
    target_date: date | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    embedder = get_embedder()
    semantic = get_vector_store().search(query, min(50, max(top_k * 5, 15)))
    candidates: dict[str, dict[str, Any]] = {}
    for rank, item in enumerate(semantic):
        citation_id = str(item.get("chunk_id") or "")
        if not citation_id or str(item.get("contract_version") or "") != settings.contract_version:
            continue
        candidates[citation_id] = {
            **item,
            "score": 0.72 * float(item.get("score") or 0) + 0.08 / (rank + 1),
            "_retrieval_type": "semantic" if embedder.is_semantic else "vector_hash",
        }

    query_terms = list(_terms(query))[:10]
    if query_terms:
        lexical_query = select(DocumentChunk).where(
            or_(*(DocumentChunk.chunk_text.ilike(f"%{term}%") for term in query_terms))
        ).limit(200)
        for chunk in db.scalars(lexical_query):
            if not _is_ver2_chunk(chunk):
                continue
            overlap = len(set(query_terms) & _terms(chunk.chunk_text)) / len(query_terms)
            existing = candidates.get(chunk.point_id)
            payload = {
                **(chunk.chunk_metadata or {}),
                "chunk_id": chunk.point_id,
                "legal_text": chunk.chunk_text,
            }
            if existing:
                existing["score"] = min(1.0, float(existing["score"]) + 0.2 * overlap)
                existing["_retrieval_type"] = "hybrid"
            else:
                candidates[chunk.point_id] = {
                    **payload,
                    "score": 0.2 * overlap,
                    "_retrieval_type": "keyword",
                }

    ranked = sorted(candidates.values(), key=lambda item: float(item.get("score") or 0), reverse=True)
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in ranked:
        citation_id = str(item.get("chunk_id") or "")
        document_id = str(item.get("document_id") or "")
        if not citation_id or not document_id or citation_id in seen:
            continue
        document = db.get(Document, document_id)
        if not document or document.status not in ACTIVE_DOCUMENT_STATUSES:
            continue
        if document_number and _fold(document.document_number) != _fold(document_number):
            continue
        if document_type not in {"", "all"} and _fold(document_type) not in _fold(document.document_type):
            continue
        latest_version = _latest_ver2_version(db, document.document_number) if document.document_number else document.version_number
        if target_date is None and document.version_number != latest_version:
            continue
        searchable = " ".join(
            str(value or "")
            for value in (
                document.title,
                document.summary,
                item.get("legal_text") or item.get("content"),
                item.get("full_path"),
            )
        )
        if legal_domain not in {"", "all"} and not (_terms(legal_domain) & _terms(searchable)):
            continue
        status = _effective_status(db, document, target_date) if target_date else None
        if status and status["status"] != "effective":
            continue
        final_score = float(item.get("score") or 0)
        if final_score < settings.rag_min_score:
            continue
        full_path = str(item.get("full_path") or "")
        page_start = int(item.get("page_start") or 1)
        evidence = {
            "citation_id": citation_id,
            "retrieval_type": item.get("_retrieval_type") or "semantic",
            "document_id": document.id,
            "document_number": document.document_number,
            "document_title": document.title,
            "document_type": document.document_type,
            "version_number": document.version_number,
            "article": item.get("marker") or _marker_from_path(full_path, "Điều"),
            "clause": _marker_from_path(full_path, "Khoản"),
            "point": _marker_from_path(full_path, "Điểm"),
            "full_path": full_path,
            "structural_positions": item.get("structural_positions") or [full_path],
            "content": item.get("legal_text") or item.get("content") or "",
            "page_start": page_start,
            "page_end": int(item.get("page_end") or page_start),
            "issued_date": document.issued_date.isoformat() if document.issued_date else None,
            "effective_from": document.effective_date.isoformat() if document.effective_date else None,
            "effective_to": status["effective_to"] if status else None,
            "source_url": _source_url(document.id, page_start),
            "score": round(final_score, 6),
            "contract_version": settings.contract_version,
        }
        results.append(evidence)
        seen.add(citation_id)
        if len(results) >= top_k:
            break
    return results


def resolve_documents(
    db: Session,
    *,
    query: str,
    target_date: date | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    term = query.strip()
    rows = list(
        db.scalars(
            select(Document)
            .where(
                Document.status.in_(ACTIVE_DOCUMENT_STATUSES),
                or_(
                    Document.document_number.ilike(f"%{term}%"),
                    Document.title.ilike(f"%{term}%"),
                    Document.summary.ilike(f"%{term}%"),
                ),
            )
            .order_by(Document.version_number.desc(), Document.created_at.desc())
            .limit(max(limit * 5, 20))
        )
    )
    results: list[dict[str, Any]] = []
    seen_numbers: set[str] = set()
    folded = _fold(term)
    for document in rows:
        if not _is_ver2_document(db, document.id):
            continue
        group = _fold(document.document_number) or document.id
        if group in seen_numbers:
            continue
        status = _effective_status(db, document, target_date) if target_date else None
        if status and status["status"] != "effective":
            continue
        exact = folded in {_fold(document.document_number), _fold(document.title)}
        results.append(
            {
                "document_id": document.id,
                "document_number": document.document_number,
                "document_title": document.title,
                "document_type": document.document_type,
                "version_number": document.version_number,
                "issued_date": document.issued_date.isoformat() if document.issued_date else None,
                "effective_from": document.effective_date.isoformat() if document.effective_date else None,
                "status": status["status"] if status else "indexed",
                "summary": document.summary,
                "match": "exact" if exact else "partial",
            }
        )
        seen_numbers.add(group)
        if len(results) >= limit:
            break
    return results


def _citation_content(db: Session, citation_id: str) -> tuple[Document | None, str]:
    chunk = db.scalar(
        select(DocumentChunk).where(
            or_(DocumentChunk.id == citation_id, DocumentChunk.point_id == citation_id)
        )
    )
    node = db.get(LegalNode, citation_id) if not chunk and not citation_id.startswith("document:") else None
    cited_document = (
        db.get(Document, citation_id.removeprefix("document:"))
        if citation_id.startswith("document:")
        else None
    )
    document = cited_document or (
        db.get(Document, chunk.document_id if chunk else node.document_id)
        if chunk or node
        else None
    )
    if not document or not _is_ver2_document(db, document.id):
        return None, ""
    if chunk:
        if not _is_ver2_chunk(chunk):
            return None, ""
        return document, chunk.chunk_text
    if node:
        nodes = list(db.scalars(select(LegalNode).where(LegalNode.document_id == node.document_id)))
        return document, _node_content(node, nodes)
    if cited_document:
        nodes = list(
            db.scalars(
                select(LegalNode)
                .where(LegalNode.document_id == cited_document.id)
                .order_by(LegalNode.order_index)
            )
        )
        return document, document_evidence(cited_document, nodes)["content"]
    return None, ""


def extract_citation_information(
    db: Session,
    *,
    citation_ids: list[str],
    fields: list[str],
) -> dict[str, Any]:
    contents: list[str] = []
    valid_ids: list[str] = []
    missing_ids: list[str] = []
    for citation_id in dict.fromkeys(citation_ids):
        document, content = _citation_content(db, citation_id)
        if document and document.status in ACTIVE_DOCUMENT_STATUSES and content:
            valid_ids.append(citation_id)
            contents.append(content)
        else:
            missing_ids.append(citation_id)
    if missing_ids:
        return {
            "ok": False,
            "evidence_ids": valid_ids,
            "error": {
                "code": "citation_not_found",
                "message": "Không tìm thấy citation: " + ", ".join(missing_ids),
                "retryable": False,
            },
        }

    text = "\n".join(contents)
    sentences = [item.strip() for item in re.split(r"(?<=[.;:])\s+|\n+", text) if item.strip()]

    def matching(markers: tuple[str, ...]) -> list[str]:
        return [item for item in sentences if any(marker in item.casefold() for marker in markers)]

    deadline_match = re.search(r"trong thời hạn\s+(\d+\s+(?:ngày|tháng|năm))", text, re.IGNORECASE)
    penalty_match = re.search(
        r"phạt tiền từ\s+([\d.,]+)\s*(?:đồng|triệu đồng)?\s+đến\s+([\d.,]+)\s*(?:đồng|triệu đồng)",
        text,
        re.IGNORECASE,
    )
    result: dict[str, Any] = {"evidence_ids": valid_ids}
    if "subject" in fields:
        subjects = matching(("đối tượng áp dụng", "đối với", "chủ thể"))
        result["subject"] = subjects[0] if subjects else None
    if "conduct" in fields:
        conducts = matching(("hành vi", "thực hiện", "không được"))
        result["conduct"] = conducts[0] if conducts else None
    if "rights" in fields:
        result["rights"] = matching(("có quyền", "được quyền", "được phép"))
    if "obligations" in fields:
        result["obligations"] = matching(("có nghĩa vụ", "phải ", "có trách nhiệm"))
    if "deadline" in fields:
        result["deadline"] = deadline_match.group(1) if deadline_match else None
    if "penalty" in fields:
        result["penalty"] = (
            {"minimum_text": penalty_match.group(1), "maximum_text": penalty_match.group(2)}
            if penalty_match
            else None
        )
    if "exceptions" in fields:
        result["exceptions"] = matching(("trừ trường hợp", "ngoại trừ", "không áp dụng"))
    return result


def provision_evidence(
    db: Session,
    *,
    document_id: str,
    article: str,
    clause: str | None = None,
    point: str | None = None,
) -> dict[str, Any] | None:
    document = find_document(db, document_id)
    if not document:
        return None
    node, nodes = find_provision_node(db, document, article, clause, point)
    return node_evidence(document, node, nodes) if node else None


def effective_status(db: Session, *, document_id: str, target_date: date) -> dict[str, Any] | None:
    document = find_document(db, document_id)
    if not document:
        return None
    return {
        "document_id": document.id,
        "document_number": document.document_number,
        "version_number": document.version_number,
        "target_date": target_date.isoformat(),
        **_effective_status(db, document, target_date),
    }


def compare_provisions(
    db: Session,
    *,
    old_document_id: str,
    new_document_id: str,
    article: str | None = None,
    clause: str | None = None,
    point: str | None = None,
) -> dict[str, Any]:
    old_doc = find_document(db, old_document_id)
    new_doc = find_document(db, new_document_id)
    old_evidence = new_evidence = None
    if old_doc:
        old_nodes = list(db.scalars(select(LegalNode).where(LegalNode.document_id == old_doc.id).order_by(LegalNode.order_index)))
        if article:
            old_node, old_nodes = find_provision_node(db, old_doc, article, clause, point)
            old_evidence = node_evidence(old_doc, old_node, old_nodes) if old_node else None
        else:
            old_evidence = document_evidence(old_doc, old_nodes)
    if new_doc:
        new_nodes = list(db.scalars(select(LegalNode).where(LegalNode.document_id == new_doc.id).order_by(LegalNode.order_index)))
        if article:
            new_node, new_nodes = find_provision_node(db, new_doc, article, clause, point)
            new_evidence = node_evidence(new_doc, new_node, new_nodes) if new_node else None
        else:
            new_evidence = document_evidence(new_doc, new_nodes)
    old_text = old_evidence["content"] if old_evidence else ""
    new_text = new_evidence["content"] if new_evidence else ""
    changes: list[dict[str, str]] = []
    matcher = difflib.SequenceMatcher(None, old_text.split(), new_text.split())
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag != "equal":
            changes.append({
                "type": {"replace": "modified", "delete": "deleted", "insert": "added"}[tag],
                "old_text": " ".join(old_text.split()[old_start:old_end]),
                "new_text": " ".join(new_text.split()[new_start:new_end]),
            })
    return {
        "old_document": old_evidence,
        "new_document": new_evidence,
        "old_found": old_doc is not None,
        "new_found": new_doc is not None,
        "changes": changes,
    }


def validate_claims(db: Session, *, claims: list[dict[str, str]], target_date: date) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    for claim in claims:
        citation_id = str(claim.get("citation_id") or "")
        claim_text = str(claim.get("claim") or "")
        chunk = db.scalar(select(DocumentChunk).where(or_(DocumentChunk.id == citation_id, DocumentChunk.point_id == citation_id)))
        node = db.get(LegalNode, citation_id) if not chunk and not citation_id.startswith("document:") else None
        cited_document = db.get(Document, citation_id.removeprefix("document:")) if citation_id.startswith("document:") else None
        document = cited_document or (db.get(Document, chunk.document_id if chunk else node.document_id) if chunk or node else None)
        if document and not _is_ver2_document(db, document.id):
            document = None
            chunk = None
            node = None
        if chunk:
            content = chunk.chunk_text
        elif node:
            nodes = list(db.scalars(select(LegalNode).where(LegalNode.document_id == node.document_id)))
            content = _node_content(node, nodes)
        elif cited_document:
            nodes = list(db.scalars(select(LegalNode).where(LegalNode.document_id == cited_document.id).order_by(LegalNode.order_index)))
            content = document_evidence(cited_document, nodes)["content"]
        else:
            content = ""
        claim_terms = _terms(claim_text)
        content_terms = _terms(content)
        coverage = len(claim_terms & content_terms) / len(claim_terms) if claim_terms else 0.0
        normalized_claim = " ".join(_fold(claim_text).split())
        normalized_content = " ".join(_fold(content).split())
        supported = bool(
            document
            and claim_terms
            and (normalized_claim in normalized_content or coverage >= 0.6)
        )
        status = _effective_status(db, document, target_date) if document else None
        effective = bool(status and status["status"] == "effective")
        valid = bool(document and supported and effective)
        if not document:
            errors.append(f"Citation '{citation_id}' không tồn tại trong kho dữ liệu.")
        elif not supported:
            errors.append(f"Citation '{citation_id}' không hỗ trợ nội dung khẳng định.")
        elif not effective:
            errors.append(f"Citation '{citation_id}' không có hiệu lực tại {target_date.isoformat()}.")
        results.append({
            "claim": claim_text,
            "citation_id": citation_id,
            "citation_exists": document is not None,
            "content_supported": supported,
            "term_coverage": round(coverage, 4),
            "effective_at_target_date": effective,
            "location_valid": bool(chunk or node or cited_document),
            "valid": valid,
        })
    return {"valid": bool(results) and all(item["valid"] for item in results), "results": results, "errors": errors}
