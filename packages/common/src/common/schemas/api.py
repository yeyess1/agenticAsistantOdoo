"""Agent API schemas shared with eval (ARCHITECTURE §5.1)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from common.schemas.chunk import RetrievalFilters, ScoredChunk

Mode = Literal["agentic", "linear"]
AnsweredBy = Literal["docs", "research", "direct"]

# Response models: fields with defaults are always present in the JSON, so mark them as
# required in the OpenAPI output schema (non-optional in the generated TS types, U-05).
_OUT = ConfigDict(json_schema_serialization_defaults_required=True)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=10, ge=1, le=100)
    filters: RetrievalFilters | None = None
    exact: bool = Field(default=False, description="Exact (brute-force) search, for V-04 only.")
    hnsw_ef: int | None = Field(default=None, ge=1, le=1024)
    with_instruction: bool = True


class SearchResponse(BaseModel):
    model_config = _OUT

    results: list[ScoredChunk]
    took_ms: int


class SourceRef(BaseModel):
    """A numbered source: `[n]` in the answer maps to it (ARCHITECTURE §4, §6.3)."""

    model_config = _OUT

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

    model_config = _OUT

    id: str
    node: str
    agent: Literal["supervisor", "docs", "research"]
    duration_ms: int
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    detail: dict[str, Any] = Field(default_factory=dict)


class Usage(BaseModel):
    model_config = _OUT

    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class QueryRequest(BaseModel):
    """`POST /query` and `/query/stream` body (ARCHITECTURE §5.1)."""

    question: str = Field(
        min_length=1, max_length=4000, examples=["¿Cómo defino un campo computado?"]
    )
    thread_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9._:-]+$",
        description="Conversation id (memory, D-08). Null: the server generates a uuid4.",
    )
    mode: Mode = Field(
        default="agentic",
        description="`linear` = retrieve -> generate baseline (E-02): no memory, no grader/router.",
    )
    filters: RetrievalFilters | None = None


class ResumeRequest(BaseModel):
    """`POST /query/resume`: answer a pending `confirm_external_search` interrupt (challenge D)."""

    thread_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    approved: bool


class PendingInterrupt(BaseModel):
    kind: Literal["confirm_external_search"] = "confirm_external_search"
    payload: dict[str, Any] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    """Aggregated result of one turn (the REST body, closing event of the SSE stream)."""

    model_config = _OUT

    thread_id: str
    run_id: str = ""
    mode: Mode = "agentic"
    answer: str
    answered_by: AnsweredBy | None = None
    route: AnsweredBy | None = None
    delegated: bool = False
    external: bool = Field(default=False, description="Answered from external sources (forum).")
    no_context: bool = False
    standalone_question: str = ""
    nodes: list[str] = Field(default_factory=list, description="Executed nodes, in order.")
    steps: list[StepRecord] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    latency_ms: int = 0
    interrupt: PendingInterrupt | None = Field(
        default=None, description="Set when the turn paused waiting for `/query/resume` (HITL)."
    )


class ErrorInfo(BaseModel):
    code: str
    message: str


class ErrorDetail(BaseModel):
    error: ErrorInfo


class ErrorResponse(BaseModel):
    """Body of 4xx/5xx errors raised by the services: `{"detail": {"error": {code, message}}}`."""

    detail: ErrorDetail
