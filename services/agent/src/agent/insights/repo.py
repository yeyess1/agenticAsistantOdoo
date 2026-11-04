"""`query_log` rows (one per answered turn) and their Postgres access."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

import psycopg
from common.schemas.api import QueryResponse
from psycopg.rows import dict_row

from agent.insights.nlp import classify_topic

Origin = Literal["ui", "eval"]
# Nodes whose output is the user-facing answer (supervisor, docs and research agents).
ANSWER_NODES = frozenset({"generator", "direct_answer", "research_llm"})


def origin_of(thread_id: str) -> Origin:
    """Eval threads are named `eval-<tag>-<mode>-<item>` (eval/runners/run_eval.py)."""
    return "eval" if thread_id.startswith("eval-") else "ui"


@dataclass(slots=True)
class LogRow:
    turn_id: str
    thread_id: str
    origin: Origin
    mode: str
    question: str
    standalone_question: str
    answered_by: str | None
    route: str | None
    topic: str
    answer_tokens: int
    answer_chars: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    no_context: bool
    sources: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime | None = None


def row_from_response(
    response: QueryResponse,
    *,
    turn_id: str,
    question: str,
    created_at: datetime | None = None,
) -> LogRow:
    answer_steps = [s for s in response.steps if s.node in ANSWER_NODES]
    sources = [
        {"kind": s.kind, "title": s.title, "url": s.url, "cited": s.cited} for s in response.sources
    ]
    question = question or response.standalone_question
    return LogRow(
        turn_id=turn_id,
        thread_id=response.thread_id,
        origin=origin_of(response.thread_id),
        mode=response.mode,
        question=question,
        standalone_question=response.standalone_question,
        answered_by=response.answered_by,
        route=response.route,
        topic=classify_topic(response.standalone_question or question, sources),
        answer_tokens=answer_steps[-1].output_tokens if answer_steps else 0,
        answer_chars=len(response.answer),
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        cost_usd=response.usage.cost_usd,
        latency_ms=response.latency_ms,
        no_context=response.no_context,
        sources=sources,
        created_at=created_at,
    )


_INSERT = """
INSERT INTO query_log (
  turn_id, thread_id, origin, mode, question, standalone_question, answered_by, route, topic,
  answer_tokens, answer_chars, input_tokens, output_tokens, cost_usd, latency_ms, no_context,
  sources, created_at
) VALUES (
  %(turn_id)s, %(thread_id)s, %(origin)s, %(mode)s, %(question)s, %(standalone_question)s,
  %(answered_by)s, %(route)s, %(topic)s, %(answer_tokens)s, %(answer_chars)s, %(input_tokens)s,
  %(output_tokens)s, %(cost_usd)s, %(latency_ms)s, %(no_context)s, %(sources)s,
  COALESCE(%(created_at)s, now())
) ON CONFLICT (turn_id) DO NOTHING
"""


class QueryLogRepo:
    """One short connection per call (same pattern as `DocumentsRepo`)."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connect(self) -> Any:
        return psycopg.AsyncConnection.connect(self._dsn, autocommit=True, row_factory=dict_row)

    async def insert(self, rows: Sequence[LogRow]) -> int:
        """Insert rows, skipping turn ids already present. Returns how many were new."""
        if not rows:
            return 0
        params = [{**asdict(r), "sources": json.dumps(r.sources)} for r in rows]
        async with await self._connect() as conn, conn.cursor() as cur:
            inserted = 0
            for p in params:
                await cur.execute(_INSERT, p)
                inserted += cur.rowcount
        return inserted

    async def reclassify(self) -> int:
        """Recompute `topic` for every row (after a lexicon change). Returns rows changed."""
        async with await self._connect() as conn:
            cur = await conn.execute(
                "SELECT turn_id, question, standalone_question, topic, sources FROM query_log"
            )
            changed = [
                (topic, r["turn_id"])
                for r in await cur.fetchall()
                if (
                    topic := classify_topic(
                        r["standalone_question"] or r["question"], list(r["sources"] or [])
                    )
                )
                != r["topic"]
            ]
            async with conn.cursor() as c:
                await c.executemany("UPDATE query_log SET topic = %s WHERE turn_id = %s", changed)
        return len(changed)

    async def fetch(
        self, *, origin: Origin | None = None, mode: str | None = None, days: int | None = None
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        args: list[Any] = []
        if origin:
            clauses.append("origin = %s")
            args.append(origin)
        if mode:
            clauses.append("mode = %s")
            args.append(mode)
        if days:
            clauses.append("created_at >= now() - make_interval(days => %s)")
            args.append(days)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        async with await self._connect() as conn:
            cur = await conn.execute(
                "SELECT question, standalone_question, topic, answered_by, answer_tokens, "
                "answer_chars, latency_ms, cost_usd, no_context, sources, created_at, origin, mode "
                f"FROM query_log {where} ORDER BY created_at",
                args,
            )
            rows: list[dict[str, Any]] = await cur.fetchall()
        return rows
