"""Write one `query_log` row per answered turn, without ever failing the request."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from common.schemas.api import QueryResponse
from common.schemas.events import Event, FinalEvent
from langgraph.graph.state import CompiledStateGraph

from agent.insights.repo import QueryLogRepo, row_from_response

log = logging.getLogger(__name__)
WRITE_TIMEOUT_S = 2.0


async def record_turn(
    repo: QueryLogRepo,
    graph: CompiledStateGraph,  # type: ignore[type-arg]
    response: QueryResponse,
    question: str | None,
) -> None:
    """Agentic turns are keyed by their last checkpoint id, the same key the backfill uses."""
    try:
        turn_id = response.run_id
        if graph.checkpointer is not None:
            snapshot = await graph.aget_state({"configurable": {"thread_id": response.thread_id}})
            turn_id = str(snapshot.config["configurable"].get("checkpoint_id") or turn_id)
            question = question or str(snapshot.values.get("question") or "")
        row = row_from_response(response, turn_id=turn_id, question=question or "")
        await asyncio.wait_for(repo.insert([row]), WRITE_TIMEOUT_S)
    except Exception as exc:  # analytics must never break a turn
        log.warning("query_log write failed: %s: %s", type(exc).__name__, exc)


async def logged(
    events: AsyncIterator[Event],
    repo: QueryLogRepo | None,
    graph: Any,
    question: str | None,
) -> AsyncIterator[Event]:
    """Pass events through; log the turn right before its `final` event is yielded.

    Before, not after: the REST aggregator stops consuming at `final`.
    """
    async for event in events:
        if repo is not None and isinstance(event, FinalEvent):
            await record_turn(repo, graph, event.response, question)
        yield event
