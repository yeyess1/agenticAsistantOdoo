"""Graph tests with fake models: routing, rewrite loop, delegation, events, memory (§14)."""

from __future__ import annotations

from typing import Any

import httpx
from agent.events import stream_events
from agent.graph.reducers import Reset, make_list_reducer, steps_reducer
from agent.graph.state import (
    ChunkVerdict,
    GradeBatch,
    RewriteOutput,
    RouteDecision,
    StandaloneQuestion,
)
from agent.graph.supervisor import build_graph
from agent_fakes import (
    FakeProvider,
    FakeRetriever,
    ai,
    chunk,
    hit,
    make_deps,
    model_of,
    scripted,
)
from common.schemas.events import (
    Event,
    FinalEvent,
    InterruptEvent,
    NodeFinished,
    NodeStarted,
    TokenEvent,
)
from langgraph.checkpoint.memory import InMemorySaver
from test_tools import POST_HTML


def route(r: str) -> RouteDecision:
    return RouteDecision(route=r, reason="because")


def grade(*flags: bool) -> GradeBatch:
    return GradeBatch(
        verdicts=[
            ChunkVerdict(chunk_id=f"c{i}", relevant=f, reason="r") for i, f in enumerate(flags, 1)
        ]
    )


def rewrite(q: str = "computed field depends") -> RewriteOutput:
    return RewriteOutput(query=q, language="en", strategy="rephrase_and_translate", reason="en")


async def run(
    deps: Any, question: str, thread: str = "t1", graph: Any = None, **kw: Any
) -> list[Event]:
    g = graph or build_graph(deps, InMemorySaver())
    return [e async for e in stream_events(g, question, thread, **kw)]


def nodes(events: list[Event]) -> list[str]:
    return [e.node for e in events if isinstance(e, NodeStarted)]


def final(events: list[Event]) -> Any:
    assert isinstance(events[-1], FinalEvent), events[-1]
    return events[-1].response


def check_event_envelope(events: list[Event]) -> None:
    """Every event carries run metadata, seq is 1..n, started/finished pair up per node."""
    assert [e.seq for e in events] == list(range(1, len(events) + 1))
    assert len({e.run_id for e in events}) == 1 and all(e.thread_id for e in events)
    started = [e.node for e in events if isinstance(e, NodeStarted)]
    finished = [e.node for e in events if isinstance(e, NodeFinished)]
    assert started == finished
    assert isinstance(events[-1], FinalEvent)


# --- S-02 / S-03 / S-05: routing, one test per route ---------------------------------------


async def test_route_direct_greeting() -> None:
    deps = make_deps(
        models={
            "router": scripted(structured=[route("direct")]),
            "direct": scripted(ai("¡Hola! Soy un asistente de Odoo 19.")),
        }
    )
    events = await run(deps, "hola")
    assert nodes(events) == ["contextualize", "router", "direct_answer"]
    r = final(events)
    assert r.route == "direct" and r.answered_by == "direct" and r.sources == []
    assert r.answer.startswith("¡Hola!")
    assert any(isinstance(e, TokenEvent) and e.node == "direct_answer" for e in events)
    check_event_envelope(events)


async def test_route_docs_answers_with_valid_citations() -> None:
    retriever = FakeRetriever([chunk(1, anchor="computed-fields"), chunk(2), chunk(3, page=7)])
    deps = make_deps(
        retriever=retriever,
        models={
            "router": scripted(structured=[route("docs")]),
            "grader": scripted(structured=[grade(True, False, True)]),
            "generator": scripted(ai("Usa `@api.depends` [1] y revisa la guía [2].")),
        },
    )
    events = await run(deps, "¿cómo defino un campo computado?")
    assert nodes(events) == ["contextualize", "router", "retriever", "grader", "generator"]
    r = final(events)
    assert r.answered_by == "docs" and not r.no_context and not r.delegated
    assert [s.n for s in r.sources] == [1, 2]  # chunk 2 was graded out: numbering follows relevant
    assert r.sources[0].url.endswith("page1.html#computed-fields")
    assert r.sources[1].page == 7 and r.sources[1].kind == "doc"
    assert all(s.cited for s in r.sources)
    assert (
        retriever.calls[0][0] == "¿cómo defino un campo computado?" and retriever.calls[0][2] == 10
    )
    # `sources` is emitted before the first token (§3.2)
    kinds = [e.type for e in events]
    assert kinds.index("sources") < kinds.index("token")
    grader_step = next(s for s in r.steps if s.node == "grader")
    assert grader_step.detail["n_relevant"] == 2
    check_event_envelope(events)


async def test_invalid_citation_markers_are_reported() -> None:
    deps = make_deps(
        retriever=FakeRetriever([chunk(1)]),
        models={
            "router": scripted(structured=[route("docs")]),
            "grader": scripted(structured=[grade(True)]),
            "generator": scripted(ai("Dato [1] y otro inventado [9].")),
        },
    )
    r = final(await run(deps, "pregunta"))
    gen = next(s for s in r.steps if s.node == "generator")
    assert gen.detail["invalid_citations"] == [9] and gen.detail["n_cited"] == 1


async def test_route_research_goes_through_confirm_and_tools() -> None:
    http = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, text=POST_HTML))
    )
    url = "https://www.odoo.com/forum/help-1/x-1"
    deps = make_deps(
        provider=FakeProvider([hit("/forum/help-1/x-1", "Compute Field Store")]),
        http=http,
        models={
            "router": scripted(structured=[route("research")]),
            "research": scripted(
                ai("", [("search_odoo_forum", {"query": "compute field store"})]),
                ai("", [("read_forum_post", {"url": url})]),
                ai("En el foro recomiendan `store=True` [1]."),
            ),
        },
    )
    events = await run(deps, "¿alguien ha paralelizado nóminas en lote?")
    assert nodes(events) == [
        "contextualize",
        "router",
        "confirm_external_search",
        "research_llm",
        "tools",
        "research_llm",
        "tools",
        "research_llm",
        "finalize_external",
    ]
    r = final(events)
    assert r.answered_by == "research" and not r.delegated
    assert "Fuente externa: Odoo Forum" in r.answer and url in r.answer
    assert [(s.kind, s.n, s.cited) for s in r.sources] == [("external", 1, True)]
    tools_steps = [s for s in r.steps if s.node == "tools"]
    assert tools_steps[0].detail["calls"] == [{"tool": "search_odoo_forum", "status": "ok"}]
    assert tools_steps[1].detail["calls"] == [{"tool": "read_forum_post", "status": "ok"}]
    check_event_envelope(events)


async def test_research_empty_results_say_not_found_without_inventing() -> None:
    deps = make_deps(
        provider=FakeProvider([]),
        models={
            "router": scripted(structured=[route("research")]),
            "research": scripted(
                ai("", [("search_odoo_forum", {"query": "obscure thing"})]),
                ai("Probablemente se hace así..."),  # LLM draft without any source behind it
            ),
        },
    )
    r = final(await run(deps, "algo muy raro"))
    assert r.answered_by == "research" and r.sources == []
    assert "No encontré información" in r.answer and "Probablemente" not in r.answer


async def test_research_loop_is_bounded_by_max_iterations() -> None:
    always_search = [ai("", [("search_odoo_forum", {"query": f"query {i}"})]) for i in range(10)]
    deps = make_deps(
        provider=FakeProvider([]),
        research_max_iterations=3,
        models={
            "router": scripted(structured=[route("research")]),
            "research": scripted(*always_search),
        },
    )
    events = await run(deps, "algo")
    assert nodes(events).count("research_llm") == 3 and nodes(events).count("tools") == 2
    assert nodes(events)[-1] == "finalize_external"
    assert "No encontré información" in final(events).answer


# --- R-03 / R-06: rewrite loop and its limit ----------------------------------------------------


async def test_rewrite_loop_recovers_after_translation() -> None:
    retriever = FakeRetriever([chunk(1)], [chunk(2)])
    deps = make_deps(
        retriever=retriever,
        models={
            "router": scripted(structured=[route("docs")]),
            "grader": scripted(structured=[grade(False), grade(True)]),
            "rewriter": scripted(structured=[rewrite("computed field depends")]),
            "generator": scripted(ai("Respuesta [1].")),
        },
    )
    events = await run(deps, "campo calculado que dependa de otro")
    assert nodes(events) == [
        "contextualize", "router", "retriever", "grader", "rewriter", "retriever", "grader", "generator",
    ]  # fmt: skip
    assert [c[0] for c in retriever.calls] == [
        "campo calculado que dependa de otro",
        "computed field depends",  # R-07: the rewritten (EN) query is what is retrieved next
    ]
    r = final(events)
    assert r.answered_by == "docs" and not r.no_context
    rw = next(s for s in r.steps if s.node == "rewriter")
    assert rw.detail["language"] == "en" and rw.detail["attempt"] == 1


async def test_rewrite_limit_then_no_context_delegates_to_research() -> None:
    retriever = FakeRetriever([chunk(1)])
    http = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, text=POST_HTML))
    )
    deps = make_deps(
        retriever=retriever,
        provider=FakeProvider([hit("/forum/help-1/x-1", "Post")]),
        http=http,
        max_rewrites=2,
        models={
            "router": scripted(structured=[route("docs")]),
            "grader": scripted(structured=[grade(False)] * 3),
            "rewriter": scripted(structured=[rewrite("q1"), rewrite("q2")]),
            "research": scripted(
                ai("", [("read_forum_post", {"url": "https://www.odoo.com/forum/help-1/x-1"})]),
                ai("Según el foro [1]."),
            ),
        },
    )
    events = await run(deps, "pregunta sin cobertura")
    seq = nodes(events)
    assert seq[:2] == ["contextualize", "router"]
    assert seq.count("retriever") == 3 and seq.count("rewriter") == 2  # MAX_REWRITES=2: bounded
    assert seq[seq.index("no_context") + 1] == "confirm_external_search"  # S-04: delegation
    assert seq[-1] == "finalize_external" and "generator" not in seq
    r = final(events)
    assert r.answered_by == "research" and r.delegated and r.no_context
    assert r.answer.startswith("_La documentación indexada no cubre")
    assert len(retriever.calls) == 3


async def test_empty_retrieval_also_rewrites_without_calling_the_grader_llm() -> None:
    deps = make_deps(
        retriever=FakeRetriever([]),
        max_rewrites=1,
        models={
            "router": scripted(structured=[route("docs")]),
            "rewriter": scripted(structured=[rewrite()]),
            "research": scripted(ai("nada")),
        },
    )
    events = await run(deps, "q")
    seq = nodes(events)
    assert seq.count("retriever") == 2 and "no_context" in seq
    assert model_of(deps, "grader").seen == []


# --- resilience of LLM nodes ---------------------------------------------------------------------


async def test_router_failure_defaults_to_docs_and_grader_fails_open() -> None:
    deps = make_deps(
        retriever=FakeRetriever([chunk(1)]),
        models={
            "router": scripted(structured=[RuntimeError("api down")]),
            "grader": scripted(structured=[RuntimeError("api down")]),
            "generator": scripted(ai("ok [1]")),
        },
    )
    r = final(await run(deps, "q"))
    assert r.route == "docs" and r.answered_by == "docs"
    assert next(s for s in r.steps if s.node == "grader").detail["fail_open"] is True


# --- A-06: usage and cost per node ----------------------------------------------------------


async def test_node_finished_reports_usage_and_cost() -> None:
    router_model = scripted(structured=[route("direct")])
    router_model.usage = {"input_tokens": 1000, "output_tokens": 100, "total_tokens": 1100}
    deps = make_deps(models={"router": router_model, "direct": scripted(ai("hola"))})
    events = await run(deps, "hola")
    fin = next(e for e in events if isinstance(e, NodeFinished) and e.node == "router")
    assert fin.usage is not None and fin.usage.input_tokens == 1000
    assert fin.model == "claude-haiku-5-5"
    assert abs(fin.usage.cost_usd - (1000 * 0.10 + 100 * 0.50) / 1e6) < 1e-12
    r = final(events)
    assert r.usage.input_tokens == 1000 and r.usage.cost_usd > 0


# --- D-08 / S-06: memory per thread and follow-up contextualization -------------------------------


async def test_follow_up_is_contextualized_with_thread_memory() -> None:
    retriever = FakeRetriever([chunk(1)])
    router_model = scripted(structured=[route("docs"), route("docs")])
    deps = make_deps(
        retriever=retriever,
        models={
            "router": router_model,
            "contextualizer": scripted(
                structured=[StandaloneQuestion(question="¿Cómo hago editable un campo computado?")]
            ),
            "grader": scripted(structured=[grade(True), grade(True)]),
            "generator": scripted(ai("Primera respuesta [1]."), ai("Segunda respuesta [1].")),
        },
    )
    graph = build_graph(deps, InMemorySaver())
    first = final(await run(deps, "¿Qué es un campo computado?", "thread-A", graph))
    second_events = await run(deps, "¿y cómo lo hago editable?", "thread-A", graph)
    second = final(second_events)

    # turn 1: no history -> pass-through, no LLM call
    assert first.steps[0].detail["passthrough"] is True
    assert str(model_of(deps, "contextualizer").seen[0][1].content).startswith(
        "Conversation so far:"
    )
    assert "Primera respuesta" in str(model_of(deps, "contextualizer").seen[0][1].content)
    # turn 2: standalone question is what the router and retriever see
    assert second.standalone_question == "¿Cómo hago editable un campo computado?"
    assert retriever.calls[1][0] == second.standalone_question
    assert router_model.seen[1][1].content == second.standalone_question
    # per-turn lists are reset (steps do not accumulate across turns)
    assert [s.node for s in second.steps] == nodes(second_events)
    state = await graph.aget_state({"configurable": {"thread_id": "thread-A"}})
    assert len(state.values["messages"]) == 4  # 2 turns x (human + ai)
    other = await graph.aget_state({"configurable": {"thread_id": "thread-B"}})
    assert not other.values  # another thread has its own (empty) memory


# --- D-13: passive HITL node ------------------------------------------------------------------------


async def test_hitl_enabled_interrupts_and_resumes() -> None:
    def build(hitl: bool) -> Any:
        return make_deps(
            hitl_enabled=hitl,
            provider=FakeProvider([]),
            models={
                "router": scripted(structured=[route("research")]),
                "research": scripted(ai("sin resultados")),
                "direct": scripted(ai("Entendido, no busco en el foro.")),
            },
        )

    # flag off: pass-through, no interrupt
    off = await run(build(False), "algo del foro")
    assert not any(isinstance(e, InterruptEvent) for e in off)

    deps = build(True)
    graph = build_graph(deps, InMemorySaver())
    first = await run(deps, "algo del foro", "h1", graph)
    assert isinstance(first[-1], InterruptEvent) and first[-1].payload["query"] == "algo del foro"
    assert "research_llm" not in nodes(first)
    declined = [e async for e in stream_events(graph, None, "h1", resume={"approved": False})]
    r = final(declined)
    assert r.answered_by == "direct" and "no busco" in r.answer


# --- structure ----------------------------------------------------------------------------------------


def test_graph_topology_matches_architecture_3_1() -> None:
    deps = make_deps()
    drawn = build_graph(deps).get_graph(xray=True)
    names = {n.split(":")[-1] for n in drawn.nodes}
    assert names >= {
        "contextualize", "router", "direct_answer", "confirm_external_search", "research_llm",
        "tools", "finalize_external", "retriever", "grader", "generator", "rewriter", "no_context",
    }  # fmt: skip
    edges = {(e.source, e.target) for e in drawn.edges}
    expected = {
        ("__start__", "contextualize"),
        ("contextualize", "router"),
        ("router", "docs_agent:__start__"),
        ("router", "confirm_external_search"),
        ("router", "direct_answer"),
        ("docs_agent:retriever", "docs_agent:grader"),
        ("docs_agent:grader", "docs_agent:generator"),
        ("docs_agent:grader", "docs_agent:rewriter"),
        ("docs_agent:grader", "docs_agent:no_context"),
        ("docs_agent:rewriter", "docs_agent:retriever"),
        ("docs_agent:__end__", "confirm_external_search"),
        ("docs_agent:__end__", "__end__"),
        ("confirm_external_search", "research_llm"),
        ("confirm_external_search", "direct_answer"),
        ("research_llm", "tools"),
        ("tools", "research_llm"),
        ("research_llm", "finalize_external"),
        ("finalize_external", "__end__"),
        ("direct_answer", "__end__"),
    }
    assert expected <= edges, expected - edges


def test_reducers_reset_and_dedupe() -> None:
    a = {"id": "1"}
    b = {"id": "2"}
    assert steps_reducer([a], [b]) == [a, b]
    assert steps_reducer([a, b], [a]) == [a, b]  # shared key through the subgraph: no duplicates
    assert steps_reducer([a, b], Reset([])) == []
    assert make_list_reducer()([1], [1]) == [1, 1]
    keyed = make_list_reducer(key=lambda x: x["k"], newer_wins=True)
    assert keyed([{"k": 1, "v": 1}], [{"k": 1, "v": 2}]) == [{"k": 1, "v": 2}]
