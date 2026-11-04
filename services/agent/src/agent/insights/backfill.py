"""One-off backfill of `query_log` from the LangGraph checkpoints (`make insights-backfill`).

Walks every thread's state history and logs each turn end: a top-level checkpoint with no
pending nodes and an answer. The row key is that checkpoint id, the same one the live hook
uses, so re-running (or running it after live traffic) inserts nothing twice.
Linear-mode turns have no checkpoints and cannot be recovered.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from typing import Any

import psycopg
from common.embedder import TEIEmbedder
from common.settings import Settings, get_settings
from langchain_core.runnables import RunnableConfig
from langgraph.types import StateSnapshot
from qdrant_client import AsyncQdrantClient

from agent.events import build_response
from agent.factory import build_deps
from agent.graph.checkpointer import postgres_checkpointer
from agent.graph.supervisor import build_graph
from agent.insights.repo import LogRow, QueryLogRepo, row_from_response

log = logging.getLogger("insights.backfill")


def turn_rows(thread_id: str, history: list[StateSnapshot]) -> list[LogRow]:
    """Rows for the completed turns of one thread; `history` is oldest first."""
    rows: list[LogRow] = []
    for snap in history:
        values: dict[str, Any] = dict(snap.values or {})
        if snap.next or not values.get("answer") or not values.get("question"):
            continue
        checkpoint_id = str(snap.config["configurable"]["checkpoint_id"])
        latency_ms = sum(int(s.get("duration_ms", 0)) for s in values.get("steps", []))
        response = build_response(values, thread_id, latency_ms, run_id=checkpoint_id)
        created_at = datetime.fromisoformat(snap.created_at) if snap.created_at else None
        rows.append(
            row_from_response(
                response,
                turn_id=checkpoint_id,
                question=str(values["question"]),
                created_at=created_at,
            )
        )
    return rows


async def _thread_ids(dsn: str) -> list[str]:
    async with await psycopg.AsyncConnection.connect(dsn) as conn:
        cur = await conn.execute(
            "SELECT DISTINCT thread_id FROM checkpoints WHERE checkpoint_ns = '' ORDER BY 1"
        )
        return [r[0] for r in await cur.fetchall()]


async def run(settings: Settings, *, dry_run: bool = False) -> tuple[int, int]:
    """Backfill; returns (turns found in the checkpoints, rows inserted)."""
    dsn = settings.resolved_database_url
    repo = QueryLogRepo(dsn)
    embedder = TEIEmbedder.from_settings(settings)  # unused: the graph is only read
    qdrant = AsyncQdrantClient(url=settings.qdrant_url)
    found = inserted = 0
    try:
        async with postgres_checkpointer(settings) as saver:
            graph = build_graph(build_deps(settings, qdrant, embedder), saver)
            for thread_id in await _thread_ids(dsn):
                cfg: RunnableConfig = {"configurable": {"thread_id": thread_id}}
                history = [s async for s in graph.aget_state_history(cfg)]
                rows = turn_rows(thread_id, list(reversed(history)))
                found += len(rows)
                if rows and not dry_run:
                    inserted += await repo.insert(rows)
    finally:
        await qdrant.close()
        await embedder.aclose()
    return found, inserted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="Count turns, write nothing.")
    parser.add_argument(
        "--reclassify", action="store_true", help="Also recompute the topic of every logged row."
    )
    args = parser.parse_args()
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(name)s %(message)s")
    if args.reclassify and not args.dry_run:
        changed = asyncio.run(QueryLogRepo(settings.resolved_database_url).reclassify())
        log.info("topics recomputed: %d rows changed", changed)
    found, inserted = asyncio.run(run(settings, dry_run=args.dry_run))
    log.info(
        "turns found: %d, inserted: %d (already present: %d)", found, inserted, found - inserted
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
