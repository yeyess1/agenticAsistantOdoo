"""Runs the graph and yields typed events (A-06); REST aggregates them, SSE forwards them."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

import anthropic
import httpx
from common.schemas.api import Mode, QueryResponse, SourceRef, StepRecord, Usage
from common.schemas.chunk import RetrievalFilters
from common.schemas.events import (
    ErrorEvent,
    Event,
    EventBase,
    FinalEvent,
    InterruptEvent,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command


def classify_error(exc: BaseException) -> str:
    """Stable error code for the API layer (502 vs 504, ARCHITECTURE §5.1)."""
    if isinstance(exc, httpx.TimeoutException | asyncio.TimeoutError | anthropic.APITimeoutError):
        return "upstream_timeout"
    if isinstance(exc, anthropic.APIError):
        return "llm_unavailable"
    if isinstance(exc, httpx.HTTPError):
        return "retrieval_unavailable"
    return "graph_failed"


def build_response(
    state: dict[str, Any],
    thread_id: str,
    latency_ms: int,
    *,
    run_id: str = "",
    mode: Mode = "agentic",
) -> QueryResponse:
    steps = [
        StepRecord(
            id=s["id"],
            node=s["node"],
            agent=s["agent"],
            duration_ms=s["duration_ms"],
            model=s["model"],
            input_tokens=s["input_tokens"],
            output_tokens=s["output_tokens"],
            cost_usd=s["cost_usd"],
            detail=s["detail"],
        )
        for s in state.get("steps", [])
    ]
    answered_by = state.get("answered_by")
    sources = [SourceRef(**s) for s in state.get("sources", [])]
    return QueryResponse(
        thread_id=thread_id,
        run_id=run_id,
        mode=mode,
        answer=state.get("answer", ""),
        answered_by=answered_by,
        route=state.get("route") if mode == "agentic" else "docs",
        delegated=bool(state.get("delegated")),
        external=answered_by == "research" or any(s.kind == "external" for s in sources),
        no_context=bool(state.get("no_context")),
        standalone_question=state.get("standalone_question", ""),
        sources=sources,
        steps=steps,
        nodes=[s.node for s in steps],
        usage=Usage(
            input_tokens=sum(s.input_tokens for s in steps),
            output_tokens=sum(s.output_tokens for s in steps),
            cost_usd=round(sum(s.cost_usd for s in steps), 6),
        ),
        latency_ms=latency_ms,
    )


async def stream_events(
    graph: CompiledStateGraph,  # type: ignore[type-arg]
    question: str | None,
    thread_id: str,
    *,
    filters: RetrievalFilters | None = None,
    resume: Any = None,
    config: RunnableConfig | None = None,
    mode: Mode = "agentic",
) -> AsyncIterator[Event]:
    """Run one turn (or resume an interrupted one) and yield events with `seq` stamped.

    `agentic` needs a graph compiled with a checkpointer (memory per `thread_id`, D-08);
    `linear` runs the baseline graph (`agent.linear`), which has no memory.
    """
    run_id = uuid.uuid4().hex
    cfg: RunnableConfig = {**(config or {}), "configurable": {"thread_id": thread_id}}
    graph_input: Any
    if resume is not None:
        graph_input = Command(resume=resume)
    elif mode == "linear":
        graph_input = {"standalone_question": question, "filters": filters}
    else:
        graph_input = {"question": question, "filters": filters, "mode": "agentic"}
    seq = 0
    started = time.perf_counter()
    last_values: dict[str, Any] = {}
    interrupted = False

    def stamp(event: EventBase) -> Event:
        nonlocal seq
        seq += 1
        return event.model_copy(update={"run_id": run_id, "thread_id": thread_id, "seq": seq})  # type: ignore[return-value]

    try:
        async for ns, stream_mode, chunk in graph.astream(
            graph_input, cfg, stream_mode=["custom", "values"], subgraphs=True
        ):
            if stream_mode == "custom" and isinstance(chunk, EventBase):
                yield stamp(chunk)  # also from the docs subgraph (subgraphs=True)
            elif stream_mode == "values" and not ns and isinstance(chunk, dict):
                if "__interrupt__" in chunk:
                    interrupted = True
                    for itr in chunk["__interrupt__"]:
                        value = itr.value if isinstance(itr.value, dict) else {"value": itr.value}
                        yield stamp(InterruptEvent(payload={"query": value.get("query", "")}))
                else:
                    last_values = chunk
    except Exception as exc:
        message = f"{type(exc).__name__}: {str(exc)[:500]}"
        yield stamp(ErrorEvent(code=classify_error(exc), message=message))
        return
    if not interrupted:
        latency_ms = int((time.perf_counter() - started) * 1000)
        response = build_response(last_values, thread_id, latency_ms, run_id=run_id, mode=mode)
        yield stamp(FinalEvent(response=response))
