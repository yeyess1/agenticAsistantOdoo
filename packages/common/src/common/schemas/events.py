"""Typed event model emitted by the agent graph (A-06, ARCHITECTURE §5.3, D-13).

Nodes emit events without run metadata; the runner (`agent.events`) stamps `run_id`,
`thread_id`, `seq` and `ts` so that REST (aggregate) and SSE (stream) share one model.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from common.schemas.api import QueryResponse, SourceRef

AgentName = Literal["supervisor", "docs", "research"]


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class EventBase(BaseModel):
    run_id: str = ""
    thread_id: str = ""
    seq: int = 0
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NodeStarted(EventBase):
    type: Literal["node_started"] = "node_started"
    node: str
    agent: AgentName


class NodeFinished(EventBase):
    type: Literal["node_finished"] = "node_finished"
    node: str
    agent: AgentName
    duration_ms: int
    model: str | None = None
    usage: Usage | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


class TokenEvent(EventBase):
    type: Literal["token"] = "token"
    node: str
    text: str


class SourcesEvent(EventBase):
    type: Literal["sources"] = "sources"
    sources: list[SourceRef]


class InterruptEvent(EventBase):
    type: Literal["interrupt"] = "interrupt"
    kind: Literal["confirm_external_search"] = "confirm_external_search"
    payload: dict[str, Any] = Field(default_factory=dict)


class FinalEvent(EventBase):
    type: Literal["final"] = "final"
    response: QueryResponse


class ErrorEvent(EventBase):
    type: Literal["error"] = "error"
    code: str
    message: str
    node: str | None = None


Event = Annotated[
    NodeStarted
    | NodeFinished
    | TokenEvent
    | SourcesEvent
    | InterruptEvent
    | FinalEvent
    | ErrorEvent,
    Field(discriminator="type"),
]
