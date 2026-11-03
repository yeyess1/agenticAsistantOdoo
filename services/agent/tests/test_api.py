"""API layer tests (A-01..A-04, E-02): httpx ASGI client, fake models/retriever, no network."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from agent.graph.state import ChunkVerdict, GradeBatch, RouteDecision, StandaloneQuestion
from agent.graph.supervisor import build_graph
from agent.linear import build_linear_graph
from agent.main import create_app
from agent_fakes import FakeProvider, FakeRetriever, ai, chunk, make_deps, model_of, scripted
from langgraph.checkpoint.memory import InMemorySaver


def route(r: str) -> RouteDecision:
    return RouteDecision(route=r, reason="because")


def grade(*flags: bool) -> GradeBatch:
    return GradeBatch(
        verdicts=[
            ChunkVerdict(chunk_id=f"c{i}", relevant=f, reason="r") for i, f in enumerate(flags, 1)
        ]
    )


def client_for(deps: Any) -> httpx.AsyncClient:
    app = create_app(with_lifespan=False)
    app.state.settings = deps.settings
    app.state.graph = build_graph(deps, InMemorySaver())
    app.state.linear_graph = build_linear_graph(deps)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def docs_deps(**kw: Any) -> Any:
    return make_deps(
        retriever=FakeRetriever([chunk(1, anchor="computed-fields"), chunk(2), chunk(3, page=7)]),
        models={
            "router": scripted(structured=[route("docs"), route("docs")]),
            "contextualizer": scripted(
                structured=[StandaloneQuestion(question="¿Cómo hago editable un campo computado?")]
            ),
            "grader": scripted(structured=[grade(True, False, True), grade(True, True, True)]),
            "generator": scripted(
                ai("Usa `@api.depends` [1] y mira la guía [2]."), ai("Con `inverse` [1].")
            ),
        },
        **kw,
    )


async def test_query_returns_answer_agent_nodes_and_sources() -> None:
    async with client_for(docs_deps()) as client:
        r = await client.post("/query", json={"question": "¿cómo defino un campo computado?"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["answered_by"] == "docs" and body["route"] == "docs" and body["mode"] == "agentic"
    assert body["nodes"] == ["contextualize", "router", "retriever", "grader", "generator"]
    assert [s["n"] for s in body["sources"]] == [1, 2]
    assert body["sources"][0]["url"].endswith("#computed-fields") and body["sources"][0]["cited"]
    assert body["thread_id"] and body["run_id"] and not body["external"]
    assert set(body["usage"]) == {"input_tokens", "output_tokens", "cost_usd"}
    assert body["interrupt"] is None and body["latency_ms"] >= 0


async def test_follow_up_on_same_thread_uses_memory() -> None:
    deps = docs_deps()
    async with client_for(deps) as client:
        first = (
            await client.post("/query", json={"question": "¿Qué es un campo computado?"})
        ).json()
        second = (
            await client.post(
                "/query",
                json={"question": "¿y cómo lo hago editable?", "thread_id": first["thread_id"]},
            )
        ).json()
    assert second["thread_id"] == first["thread_id"]
    assert second["standalone_question"] == "¿Cómo hago editable un campo computado?"
    seen = str(model_of(deps, "contextualizer").seen[0][1].content)
    assert "Usa `@api.depends`" in seen  # the first answer is in the history


async def test_linear_mode_skips_agentic_nodes_and_memory() -> None:
    deps = make_deps(
        retriever=FakeRetriever([chunk(1), chunk(2)]),
        models={"generator": scripted(ai("Respuesta lineal [1][2]."))},
    )
    async with client_for(deps) as client:
        r = await client.post("/query", json={"question": "campo computado", "mode": "linear"})
    body = r.json()
    assert r.status_code == 200, r.text
    assert body["mode"] == "linear" and body["answered_by"] == "docs" and body["route"] == "docs"
    assert body["nodes"] == ["retriever", "generator"]  # no contextualize/router/grader
    assert [s["n"] for s in body["sources"]] == [1, 2] and all(s["cited"] for s in body["sources"])
    assert model_of(deps, "router").seen == [] and model_of(deps, "grader").seen == []


async def test_stream_emits_typed_sse_events_ending_with_final() -> None:
    async with client_for(docs_deps()) as client:
        r = await client.post("/query/stream", json={"question": "campo computado"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    frames = [f for f in r.text.split("\n\n") if f.strip()]
    parsed = []
    for frame in frames:
        event_line, data_line = frame.split("\n")
        kind = event_line.removeprefix("event: ")
        data = json.loads(data_line.removeprefix("data: "))
        assert data["type"] == kind
        parsed.append(data)
    kinds = [p["type"] for p in parsed]
    assert kinds[0] == "node_started" and kinds[-1] == "final"
    assert {"node_finished", "sources", "token"} <= set(kinds)
    assert [p["seq"] for p in parsed] == list(range(1, len(parsed) + 1))
    assert parsed[-1]["response"]["answered_by"] == "docs"


@pytest.mark.parametrize(
    "payload",
    [
        {"question": ""},
        {"question": "x" * 4001},
        {"question": "q", "mode": "other"},
        {"question": "q", "thread_id": "bad id with spaces"},
        {},
    ],
)
async def test_query_validation_returns_422(payload: dict[str, Any]) -> None:
    async with client_for(docs_deps()) as client:
        r = await client.post("/query", json=payload)
    assert r.status_code == 422


class _FailingRetriever(FakeRetriever):
    def __init__(self, exc: Exception) -> None:
        super().__init__()
        self.exc = exc

    async def retrieve(self, *args: Any, **kwargs: Any) -> Any:
        raise self.exc


@pytest.mark.parametrize(
    ("exc", "status", "code"),
    [
        (httpx.ConnectError("tei down"), 502, "retrieval_unavailable"),
        (httpx.ReadTimeout("slow"), 504, "upstream_timeout"),
    ],
)
async def test_upstream_failures_map_to_typed_errors(
    exc: Exception, status: int, code: str
) -> None:
    deps = make_deps(
        retriever=_FailingRetriever(exc), models={"router": scripted(structured=[route("docs")])}
    )
    async with client_for(deps) as client:
        r = await client.post("/query", json={"question": "campo computado"})
    assert r.status_code == status
    assert r.json()["detail"]["error"]["code"] == code


async def test_hitl_interrupt_then_resume() -> None:
    deps = make_deps(
        hitl_enabled=True,
        provider=FakeProvider([]),
        models={
            "router": scripted(structured=[route("research")]),
            "direct": scripted(ai("Entendido, no busco en el foro.")),
        },
    )
    async with client_for(deps) as client:
        paused = (await client.post("/query", json={"question": "algo del foro"})).json()
        assert paused["interrupt"]["kind"] == "confirm_external_search"
        assert paused["interrupt"]["payload"]["query"] == "algo del foro" and paused["answer"] == ""
        thread = paused["thread_id"]
        done = await client.post("/query/resume", json={"thread_id": thread, "approved": False})
        assert done.status_code == 200 and done.json()["answered_by"] == "direct"
        again = await client.post("/query/resume", json={"thread_id": thread, "approved": True})
        assert again.status_code == 404
        assert again.json()["detail"]["error"]["code"] == "no_pending_interrupt"


async def test_openapi_documents_query_routes() -> None:
    async with client_for(docs_deps()) as client:
        spec = (await client.get("/openapi.json")).json()
    assert {"/query", "/query/stream", "/query/resume", "/search", "/health"} <= set(spec["paths"])
    schemas = spec["components"]["schemas"]
    assert {"QueryRequest", "QueryResponse", "ErrorResponse", "SourceRef"} <= set(schemas)
