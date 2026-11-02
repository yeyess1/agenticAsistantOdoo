"""Retrieval schemas (ARCHITECTURE §5.1, §6.1)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class RetrievalFilters(BaseModel):
    """Metadata filters applied to payload indexes in Qdrant (V-03)."""

    doc_ids: list[UUID] | None = None
    sources: list[str] | None = None


class ScoredChunk(BaseModel):
    chunk_id: str
    doc_id: str
    score: float
    text: str
    title: str
    section: str | None = None
    url: str
    anchor: str | None = None
    page: int | None = Field(default=None, description="PDF page number; null otherwise.")
