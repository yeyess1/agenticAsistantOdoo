"""Runs the graph and yields typed events (A-06); REST aggregates them, SSE forwards them."""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from common.schemas.api import QueryResponse, SourceRef, StepRecord
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


def build_response(state: dict[str, Any], thread_id: str, latency_ms: int) -> QueryResponse:
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
    return QueryResponse(
        thread_id=thread_id,
        answer=state.get("answer", ""),
        answered_by=state.get("answered_by"),
        route=state.get("route"),
        delegated=bool(state.get("delegated")),
        no_context=bool(state.get("no_context")),
        standalone_question=state.get("standalone_question", ""),
        sources=[SourceRef(**s) for s in state.get("sources", [])],
        steps=steps,
        nodes=[s.node for s in steps],
        input_tokens=sum(s.input_tokens for s in steps),
        output_tokens=sum(s.output_tokens for s in steps),
        cost_usd=round(sum(s.cost_usd for s in steps), 6),
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
) -> AsyncIterator[Event]:
    """Run one turn (or resume an interrupted one) and yield events with `seq` stamped.

    Requires a graph compiled with a checkpointer (memory per `thread_id`, D-08).
    """
    run_id = uuid.uuid4().hex
    cfg: RunnableConfig = {**(config or {}), "configurable": {"thread_id": thread_id}}
    graph_input: Any
    if resume is not None:
        graph_input = Command(resume=resume)
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
        async for ns, mode, chunk in graph.astream(
            graph_input, cfg, stream_mode=["custom", "values"], subgraphs=True
        ):
            if mode == "custom" and isinstance(chunk, EventBase):
                yield stamp(chunk)  # also from the docs subgraph (subgraphs=True)
            elif mode == "values" and not ns and isinstance(chunk, dict):
                if "__interrupt__" in chunk:
                    interrupted = True
                    for itr in chunk["__interrupt__"]:
                        value = itr.value if isinstance(itr.value, dict) else {"value": itr.value}
                        yield stamp(InterruptEvent(payload={"query": value.get("query", "")}))
                else:
                    last_values = chunk
    except Exception as exc:
        yield stamp(ErrorEvent(code="graph_failed", message=str(exc)[:500]))
        return
    if not interrupted:
        latency_ms = int((time.perf_counter() - started) * 1000)
        yield stamp(FinalEvent(response=build_response(last_values, thread_id, latency_ms)))
