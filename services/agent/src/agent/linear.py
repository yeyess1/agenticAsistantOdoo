"""Linear RAG baseline (E-02): `retriever -> generator`, no memory.

Same `Retriever` and the same generator node (prompt, model, citations) as the docs agent,
without contextualize, router, grader or rewriter, so `mode=linear` vs `mode=agentic` on
`/query` compares only the agentic parts (ARCHITECTURE §5.1, §12).
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent.graph.nodes.generator import make_generator
from agent.graph.nodes.retriever import make_retriever
from agent.graph.runtime import GraphDeps
from agent.graph.state import DocsState


def _all_retrieved(state: DocsState) -> dict[str, Any]:
    """Hand every retrieved chunk to the generator (no grader). Untraced: not a step."""
    return {"relevant_chunks": state.get("retrieved", [])}


def build_linear_graph(deps: GraphDeps) -> CompiledStateGraph:  # type: ignore[type-arg]
    g = StateGraph(DocsState)
    g.add_node("retriever", make_retriever(deps))
    g.add_node("context", _all_retrieved)
    g.add_node("generator", make_generator(deps))
    g.add_edge(START, "retriever")
    g.add_edge("retriever", "context")
    g.add_edge("context", "generator")
    g.add_edge("generator", END)
    return g.compile(name="linear_rag")  # no checkpointer: the baseline has no memory
