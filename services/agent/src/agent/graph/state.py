"""Typed graph state (S-01, D-02, ARCHITECTURE §4)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, TypedDict

from common.schemas.chunk import RetrievalFilters, ScoredChunk
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from agent.graph.reducers import add_or_reset, external_reducer, sources_reducer, steps_reducer

Route = Literal["docs", "research", "direct"]
AgentName = Literal["supervisor", "docs", "research"]


class Step(TypedDict):
    """One record per executed node."""

    id: str
    node: str
    agent: AgentName
    started_at: datetime
    duration_ms: int
    model: str | None
    input_tokens: int
    output_tokens: int
    cost_usd: float
    detail: dict[str, Any]


class Source(TypedDict):
    n: int
    kind: Literal["doc", "external"]
    doc_id: str | None
    chunk_id: str | None
    title: str
    section: str | None
    url: str
    page: int | None
    score: float | None
    cited: bool


class ExternalSource(TypedDict):
    """A forum post seen by the research tools; `n` is the number shown to the LLM."""

    n: int
    url: str
    title: str
    read: bool


class GraphState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    question: str
    standalone_question: str
    route: Route | None
    route_reason: str
    steps: Annotated[list[Step], steps_reducer]
    sources: Annotated[list[Source], sources_reducer]
    no_context: bool
    answered_by: Route | None
    delegated: bool
    answer: str
    filters: RetrievalFilters | None
    mode: Literal["agentic", "linear"]
    # research agent (own tool loop)
    external_approved: bool
    research_messages: Annotated[list[AnyMessage], add_or_reset]
    research_iter: int
    external_sources: Annotated[list[ExternalSource], external_reducer]


class DocsState(TypedDict, total=False):
    """Docs subgraph state. Keys shared with `GraphState` flow in and out of the subgraph."""

    messages: Annotated[list[AnyMessage], add_messages]
    standalone_question: str
    filters: RetrievalFilters | None
    steps: Annotated[list[Step], steps_reducer]
    sources: Annotated[list[Source], sources_reducer]
    no_context: bool
    answered_by: Route | None
    answer: str
    # private to the subgraph
    query: str
    retrieved: list[ScoredChunk]
    relevant_chunks: list[ScoredChunk]
    rewrite_count: int
    rewrites: list[RewriteOutput]


# --- LLM structured outputs (Pydantic, D-02) ------------------------------------------------


class StandaloneQuestion(BaseModel):
    question: str


class RouteDecision(BaseModel):
    route: Route
    reason: str = Field(max_length=300)


class ChunkVerdict(BaseModel):
    chunk_id: str
    relevant: bool
    reason: str


class GradeBatch(BaseModel):
    verdicts: list[ChunkVerdict]


class RewriteOutput(BaseModel):
    """R-07: rewrites and/or translates the query (ES -> EN) before the next retrieval."""

    query: str
    language: Literal["es", "en"]
    strategy: Literal["rephrase", "translate", "rephrase_and_translate"]
    reason: str
