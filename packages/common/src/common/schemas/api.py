"""Agent API schemas shared with eval (ARCHITECTURE §5.1)."""

from __future__ import annotations

from typing import Any, Literal

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


class SourceRef(BaseModel):
    """A numbered source: `[n]` in the answer maps to it (ARCHITECTURE §4, §6.3)."""

    n: int
    kind: Literal["doc", "external"]
    doc_id: str | None = None
    title: str
    section: str | None = None
    url: str
    page: int | None = None
    score: float | None = None
    cited: bool = False


class StepRecord(BaseModel):
    """One executed node (timeline, U-08)."""

    id: str
    node: str
    agent: Literal["supervisor", "docs", "research"]
    duration_ms: int
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    detail: dict[str, Any] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    """Aggregated result of one turn (the REST body, closing event of the SSE stream)."""

    thread_id: str
    answer: str
    answered_by: Literal["docs", "research", "direct"] | None = None
    route: Literal["docs", "research", "direct"] | None = None
    delegated: bool = False
    no_context: bool = False
    standalone_question: str = ""
    sources: list[SourceRef] = Field(default_factory=list)
    steps: list[StepRecord] = Field(default_factory=list)
    nodes: list[str] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
