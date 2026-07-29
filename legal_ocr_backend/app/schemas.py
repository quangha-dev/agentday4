from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    document_number: str
    issued_date: date | None
    effective_date: date | None
    document_type: str
    issuing_authority: str
    signer: str
    summary: str
    version_number: int
    previous_version_id: str | None
    original_filename: str
    status: str
    page_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class PageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    document_id: str
    page_number: int
    classification: str
    raw_text: str
    cleaned_text: str | None
    verified_text: str | None
    confidence: float | None
    bounding_boxes: list[Any]
    is_verified: bool
    image_url: str | None = None


class TextUpdate(BaseModel):
    content: str = Field(min_length=0)


class CleanupOut(BaseModel):
    page: PageOut
    method: str
    warning: str | None = None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    document_id: str
    job_type: str
    status: str
    progress: int
    message: str | None


class LegalNodeOut(BaseModel):
    id: str
    document_id: str
    parent_id: str | None
    node_type: str
    marker: str | None
    title: str | None
    content: str
    full_path: str
    order_index: int
    page_start: int
    page_end: int
    bbox_spans: list[Any]
    children: list["LegalNodeOut"] = []


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    mode: str = Field(default="semantic", pattern="^(exact|keyword|semantic|hybrid)$")
    document_id: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class SearchResult(BaseModel):
    legal_node_id: str
    document_id: str
    document_title: str
    node_type: str
    marker: str | None
    title: str | None
    content: str
    full_path: str
    page_start: int
    page_end: int
    score: float


class MessageOut(BaseModel):
    message: str
