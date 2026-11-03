"""Document registry and ingestion schemas (ARCHITECTURE §5.2)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

DocumentStatus = Literal["processing", "indexed", "failed"]
IngestAction = Literal["created", "updated", "unchanged"]


class DocumentOut(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    doc_id: UUID
    name: str
    source: str
    mime_type: str
    content_hash: str
    embedding_model: str
    n_chunks: int
    status: DocumentStatus
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    ingested_at: datetime | None = None


class DocumentList(BaseModel):
    items: list[DocumentOut]
    total: int


class IngestResult(BaseModel):
    doc_id: UUID
    name: str
    source: str
    status: DocumentStatus
    n_chunks: int
    content_hash: str
    action: IngestAction
    took_ms: int
