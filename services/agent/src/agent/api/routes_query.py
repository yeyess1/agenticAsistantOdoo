"""Query endpoints (A-01..A-04, ARCHITECTURE §5.1): REST aggregates events, SSE forwards them."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

from common.schemas.api import (
    ErrorResponse,
    PendingInterrupt,
    QueryRequest,
    QueryResponse,
    ResumeRequest,
)
from common.schemas.events import ErrorEvent, Event, FinalEvent, InterruptEvent
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langgraph.graph.state import CompiledStateGraph

from agent.events import build_response, stream_events
from agent.insights.hook import logged

router = APIRouter(tags=["query"])

_ERRORS: dict[int | str, dict[str, Any]] = {
    502: {"model": ErrorResponse, "description": "LLM, embeddings or Qdrant failed"},
    504: {"model": ErrorResponse, "description": "An upstream service timed out"},
}
_SSE_DOC: dict[int | str, dict[str, Any]] = {
    200: {
        "description": "`text/event-stream`: `event: <type>` + `data: <json>` per event "
        "(node_started, node_finished, token, sources, interrupt, final, error; §5.3).",
        "content": {"text/event-stream": {"schema": {"type": "string"}}},
    }
}


def api_error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status, detail={"error": {"code": code, "message": message}})


def _graph(request: Request, linear: bool = False) -> CompiledStateGraph:  # type: ignore[type-arg]
    graph: CompiledStateGraph = (  # type: ignore[type-arg]
        request.app.state.linear_graph if linear else request.app.state.graph
    )
    return graph


def _logged(
    request: Request,
    graph: CompiledStateGraph,  # type: ignore[type-arg]
    events: AsyncIterator[Event],
    question: str | None,
) -> AsyncIterator[Event]:
    """Every answered turn lands in `query_log` (insights view)."""
    return logged(events, getattr(request.app.state, "query_log", None), graph, question)


def _events(request: Request, body: QueryRequest, thread_id: str) -> AsyncIterator[Event]:
    graph = _graph(request, body.mode == "linear")
    events = stream_events(graph, body.question, thread_id, filters=body.filters, mode=body.mode)
    return _logged(request, graph, events, body.question)


async def _aggregate(
    graph: CompiledStateGraph,  # type: ignore[type-arg]
    events: AsyncIterator[Event],
    thread_id: str,
) -> QueryResponse:
    """Consume the event stream and return the `final` response (REST contract)."""
    pending: InterruptEvent | None = None
    error: ErrorEvent | None = None
    async for event in events:
        if isinstance(event, FinalEvent):
            return event.response
        if isinstance(event, InterruptEvent):
            pending = event
        elif isinstance(event, ErrorEvent):
            error = event
    if pending is not None:  # HITL (challenge D): the turn paused before the external search
        snapshot = await graph.aget_state({"configurable": {"thread_id": thread_id}})
        response = build_response(dict(snapshot.values), thread_id, 0, run_id=pending.run_id)
        return response.model_copy(
            update={
                "answer": "",
                "answered_by": None,
                "interrupt": PendingInterrupt(kind=pending.kind, payload=pending.payload),
            }
        )
    if error is not None:
        status = 504 if error.code == "upstream_timeout" else 502
        raise api_error(status, error.code, error.message)
    raise api_error(502, "graph_failed", "the graph finished without a final event")


async def _sse(events: AsyncIterator[Event]) -> AsyncIterator[str]:
    async for event in events:
        yield f"event: {event.type}\ndata: {event.model_dump_json()}\n\n"


def _sse_response(events: AsyncIterator[Event]) -> StreamingResponse:
    return StreamingResponse(
        _sse(events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Ask a question (agentic graph or linear baseline); aggregated response",
    responses=_ERRORS,
)
async def query(request: Request, body: QueryRequest) -> QueryResponse:
    thread_id = body.thread_id or uuid.uuid4().hex
    graph = _graph(request, body.mode == "linear")
    return await _aggregate(graph, _events(request, body, thread_id), thread_id)


@router.post(
    "/query/stream",
    summary="Same as /query, streamed as Server-Sent Events (challenge C)",
    response_class=StreamingResponse,
    responses=_SSE_DOC,
)
async def query_stream(request: Request, body: QueryRequest) -> StreamingResponse:
    thread_id = body.thread_id or uuid.uuid4().hex
    return _sse_response(_events(request, body, thread_id))


@router.post(
    "/query/resume",
    response_model=QueryResponse,
    summary="Approve or reject a pending external search (HITL, challenge D)",
    responses={404: {"model": ErrorResponse, "description": "No pending interrupt"}, **_ERRORS},
)
async def query_resume(request: Request, body: ResumeRequest) -> QueryResponse:
    graph = _graph(request)
    snapshot = await graph.aget_state({"configurable": {"thread_id": body.thread_id}})
    if not snapshot.interrupts:
        raise api_error(404, "no_pending_interrupt", f"thread {body.thread_id} is not paused")
    events = stream_events(graph, None, body.thread_id, resume={"approved": body.approved})
    events = _logged(request, graph, events, None)
    return await _aggregate(graph, events, body.thread_id)
