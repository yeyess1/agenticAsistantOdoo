"""`docs_agent`: compiled subgraph (R-01): retriever, grader, generator, rewriter loop."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent.graph.nodes.generator import make_generator, make_no_context
from agent.graph.nodes.grader import make_grader, route_after_grader
from agent.graph.nodes.retriever import make_retriever
from agent.graph.nodes.rewriter import make_rewriter
from agent.graph.runtime import GraphDeps
from agent.graph.state import DocsState


def build_docs_subgraph(deps: GraphDeps) -> CompiledStateGraph:  # type: ignore[type-arg]
    g = StateGraph(DocsState)
    g.add_node("retriever", make_retriever(deps))
    g.add_node("grader", make_grader(deps))
    g.add_node("generator", make_generator(deps))
    g.add_node("rewriter", make_rewriter(deps))
    g.add_node("no_context", make_no_context())
    g.add_edge(START, "retriever")
    g.add_edge("retriever", "grader")
    g.add_conditional_edges(
        "grader",
        route_after_grader(deps.settings.max_rewrites),
        {"generator": "generator", "rewriter": "rewriter", "no_context": "no_context"},
    )
    g.add_edge("rewriter", "retriever")  # bounded by MAX_REWRITES in the grader decision
    g.add_edge("generator", END)
    g.add_edge("no_context", END)
    return g.compile(name="docs_agent")
