"""Supervisor graph (S-01..S-07): ARCHITECTURE §3.1 topology."""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent.graph.docs_subgraph import build_docs_subgraph
from agent.graph.nodes.confirm import make_confirm, route_after_confirm
from agent.graph.nodes.contextualize import make_contextualize
from agent.graph.nodes.direct import make_direct
from agent.graph.nodes.research import (
    make_finalize_external,
    make_research_llm,
    make_tools_node,
    route_after_research_llm,
)
from agent.graph.nodes.router import make_router, route_from_router
from agent.graph.runtime import GraphDeps
from agent.graph.state import GraphState


def route_after_docs(state: GraphState) -> str:
    """S-04: the docs agent signals "no context" and the supervisor delegates to research."""
    return "confirm_external_search" if state.get("no_context") else END


def build_graph(
    deps: GraphDeps,
    checkpointer: BaseCheckpointSaver | None = None,  # type: ignore[type-arg]
) -> CompiledStateGraph:  # type: ignore[type-arg]
    """Compile the agent graph. Pass the checkpointer (Postgres in prod, in-memory in tests)."""
    g = StateGraph(GraphState)
    g.add_node("contextualize", make_contextualize(deps))
    g.add_node("router", make_router(deps))
    g.add_node("direct_answer", make_direct(deps))
    g.add_node("docs_agent", build_docs_subgraph(deps))
    g.add_node("confirm_external_search", make_confirm(deps))
    g.add_node("research_llm", make_research_llm(deps))
    g.add_node("tools", make_tools_node(deps))
    g.add_node("finalize_external", make_finalize_external())

    g.add_edge(START, "contextualize")
    g.add_edge("contextualize", "router")
    g.add_conditional_edges(
        "router",
        route_from_router,
        {
            "docs": "docs_agent",
            "research": "confirm_external_search",
            "direct": "direct_answer",
        },
    )
    g.add_conditional_edges(
        "docs_agent",
        route_after_docs,
        {"confirm_external_search": "confirm_external_search", END: END},
    )
    g.add_conditional_edges(
        "confirm_external_search",
        route_after_confirm,
        {"research_llm": "research_llm", "direct_answer": "direct_answer"},
    )
    g.add_conditional_edges(
        "research_llm",
        route_after_research_llm(deps.settings.research_max_iterations),
        {"tools": "tools", "finalize_external": "finalize_external"},
    )
    g.add_edge("tools", "research_llm")
    g.add_edge("finalize_external", END)
    g.add_edge("direct_answer", END)
    return g.compile(checkpointer=checkpointer, name="agent")
