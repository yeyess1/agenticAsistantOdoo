"""`retriever` (R-01): TEI + Qdrant top_k through the `Retriever` interface (D-13)."""

from __future__ import annotations

from typing import Any

from agent.graph.runtime import GraphDeps, Tracker, traced
from agent.graph.state import DocsState


def make_retriever(deps: GraphDeps) -> Any:
    @traced("retriever", "docs")
    async def retriever(state: DocsState, t: Tracker) -> dict[str, Any]:
        query = state.get("query") or state["standalone_question"]
        chunks = await deps.retriever.retrieve(
            query, state.get("filters"), k=deps.settings.retriever_top_k
        )
        chunks = await deps.get_reranker().rerank(query, chunks)
        t.detail.update(
            {
                "query": query,
                "n_retrieved": len(chunks),
                "top_score": round(chunks[0].score, 4) if chunks else None,
            }
        )
        return {"query": query, "retrieved": chunks}

    return retriever
