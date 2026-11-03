"""Agent API schemas shared with eval (ARCHITECTURE §5.1)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from common.schemas.chunk import RetrievalFilters, ScoredChunk


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=10, ge=1, le=100)
    filters: RetrievalFilters | None = None
    exact: bool = Field(default=False, description="Exact (brute-force) search, for V-04 only.")
    hnsw_ef: int | None = Field(default=None, ge=1, le=1024)
    with_instruction: bool = True


class SearchResponse(BaseModel):
    results: list[ScoredChunk]
    took_ms: int
