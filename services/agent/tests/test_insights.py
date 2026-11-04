"""Insights: NLP helpers, aggregation, live query_log hook and checkpoint backfill (no network)."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

import httpx
from agent.graph.supervisor import build_graph
from agent.insights.aggregate import aggregate
from agent.insights.backfill import turn_rows
from agent.insights.nlp import classify_topic, doc_topic, frequent_phrases, normalize
from agent.insights.repo import LogRow, origin_of
from agent.linear import build_linear_graph
from agent.main import create_app
from langgraph.checkpoint.memory import InMemorySaver
from test_api import docs_deps

ORM_URL = "https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html#fields"
SEC_URL = "https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html"


def app_with(deps: Any, repo: Any) -> Any:
    app = create_app(with_lifespan=False)
    app.state.settings = deps.settings
    app.state.graph = build_graph(deps, InMemorySaver())
    app.state.linear_graph = build_linear_graph(deps)
    app.state.query_log = repo
    return app


def client(app: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


class FakeLogRepo:
    def __init__(self) -> None:
        self.rows: list[LogRow] = []

    async def insert(self, rows: list[LogRow]) -> int:
        new = [r for r in rows if r.turn_id not in {x.turn_id for x in self.rows}]
        self.rows.extend(new)
        return len(new)

    async def fetch(self, **_: Any) -> list[dict[str, Any]]:
        now = datetime.now(UTC)
        return [{**asdict(r), "created_at": r.created_at or now} for r in self.rows]


def test_normalize_and_phrases() -> None:
    assert normalize("¿Cómo Defino?") == "¿como defino?"
    qs = [
        "¿Cómo defino un campo computado?",
        "campo computado editable",
        "¿Qué es un campo computado almacenado?",
    ]
    assert frequent_phrases(qs, n=2)[0] == ("campo computado", 3)
    assert frequent_phrases(qs, n=3) == []  # nothing repeats twice


def test_topics_from_lexicon_and_documents() -> None:
    assert classify_topic("¿Cómo defino un campo computado?") == "orm"
    assert classify_topic("Agregar un botón en la vista formulario con xpath") == "views"
    assert classify_topic("reglas de registro y grupos de acceso") == "security"
    assert classify_topic("llamar a Odoo por XML-RPC desde Python") == "api"
    assert classify_topic("hola") == "general"
    # No keyword: the cited documentation decides.
    assert (
        classify_topic("¿y eso cómo funciona?", [{"kind": "doc", "url": SEC_URL, "cited": True}])
        == "security"
    )
    assert doc_topic("tutorials__server_framework_101__06_basicviews.md") == "views"
    assert doc_topic("https://www.odoo.com/forum/help-1/xyz") is None
    # Short keys match whole words only: "rest" in "restricción" is not the API topic.
    assert classify_topic("restricción SQL única") == "orm"


def _row(i: int, question: str, topic: str, tokens: int, urls: list[str]) -> dict[str, Any]:
    return {
        "question": question,
        "topic": topic,
        "answered_by": "docs",
        "answer_tokens": tokens,
        "answer_chars": tokens * 4,
        "latency_ms": 1000 + i,
        "cost_usd": 0.01,
        "no_context": False,
        "origin": "ui",
        "created_at": datetime(2026, 11, 3, 10, i, tzinfo=UTC),
        "sources": [{"kind": "doc", "url": u, "title": u, "cited": True} for u in urls],
    }


def test_aggregate() -> None:
    rows = [
        _row(0, "campo computado", "orm", 120, [ORM_URL, ORM_URL.replace("#fields", "#compute")]),
        _row(1, "¿Campo computado?", "orm", 280, [ORM_URL]),
        _row(2, "grupos de acceso", "security", 0, [SEC_URL]),
    ]
    out = aggregate(rows)
    assert out.totals.turns == 3 and out.totals.answer_tokens_mean == 200.0
    assert [t.topic for t in out.topics] == ["orm", "security"] and out.topics[0].share == 0.6667
    assert out.questions[0].count == 2  # same content words, accents and order ignored
    doc = out.documents[0]
    assert doc.url == ORM_URL.split("#")[0] and doc.retrieved == 2 and doc.topic == "orm"
    assert [(b.lo, b.count) for b in out.answer_tokens_hist] == [(100, 1), (200, 1)]
    assert out.daily[0].count == 3
    assert aggregate([]).totals.turns == 0


def test_origin_from_thread_id() -> None:
    assert origin_of("eval-20261103-agentic-q01") == "eval" and origin_of("abc") == "ui"


async def test_turns_are_logged_and_backfill_uses_the_same_key() -> None:
    repo = FakeLogRepo()
    app = app_with(docs_deps(), repo)
    async with client(app) as c:
        first = (await c.post("/query", json={"question": "¿Qué es un campo computado?"})).json()
        await c.post(
            "/query",
            json={"question": "¿y cómo lo hago editable?", "thread_id": first["thread_id"]},
        )
        insights = (await c.get("/insights")).json()
    graph = app.state.graph
    assert [r.question for r in repo.rows] == [
        "¿Qué es un campo computado?",
        "¿y cómo lo hago editable?",
    ]
    assert all(r.topic == "orm" and r.origin == "ui" and r.answered_by == "docs" for r in repo.rows)
    assert repo.rows[0].answer_chars == len("Usa `@api.depends` [1] y mira la guía [2].")
    assert repo.rows[0].sources and repo.rows[0].mode == "agentic"
    assert insights["totals"]["turns"] == 2 and insights["topics"][0]["topic"] == "orm"

    cfg = {"configurable": {"thread_id": first["thread_id"]}}
    history = [s async for s in graph.aget_state_history(cfg)]
    backfilled = turn_rows(first["thread_id"], list(reversed(history)))
    assert [r.turn_id for r in backfilled] == [r.turn_id for r in repo.rows]
    assert await repo.insert(backfilled) == 0  # idempotent


async def test_insights_without_repo_is_503() -> None:
    async with client(app_with(docs_deps(), None)) as c:
        r = await c.get("/insights")
    assert r.status_code == 503
