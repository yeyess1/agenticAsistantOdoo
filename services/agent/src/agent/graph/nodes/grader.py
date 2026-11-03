"""`grader` (R-02): relevance per chunk, one batched LLM call (approved 2026-11-02)."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agent.graph.prompts import load_prompt
from agent.graph.runtime import GraphDeps, Tracker, ainvoke_structured, traced
from agent.graph.state import DocsState, GradeBatch

GRADER_CHUNK_CHARS = 1500


def make_grader(deps: GraphDeps) -> Any:
    @traced("grader", "docs", deps.model_name("grader"))
    async def grader(state: DocsState, t: Tracker) -> dict[str, Any]:
        chunks = state.get("retrieved", [])
        if not chunks:
            t.detail.update({"n_relevant": 0, "n_graded": 0})
            return {"relevant_chunks": []}
        listing = "\n\n".join(
            f"[c{i}] {c.title} > {c.section or '-'}\n{c.text[:GRADER_CHUNK_CHARS]}"
            for i, c in enumerate(chunks, start=1)
        )
        out = await ainvoke_structured(
            deps.model("grader"),
            GradeBatch,
            [
                SystemMessage(content=load_prompt("grader")),
                HumanMessage(
                    content=f"Question: {state['standalone_question']}\n\nChunks:\n\n{listing}"
                ),
            ],
            t,
        )
        if out is None:  # fail open: better to answer from unfiltered chunks than from nothing
            t.detail.update({"n_relevant": len(chunks), "n_graded": 0, "fail_open": True})
            return {"relevant_chunks": list(chunks)}
        relevant_ids = {v.chunk_id.strip().lower() for v in out.verdicts if v.relevant}
        relevant = [c for i, c in enumerate(chunks, start=1) if f"c{i}" in relevant_ids]
        t.detail.update(
            {
                "n_relevant": len(relevant),
                "n_graded": len(out.verdicts),
                "verdicts": {v.chunk_id: v.relevant for v in out.verdicts},
            }
        )
        return {"relevant_chunks": relevant}

    return grader


def route_after_grader(max_rewrites: int) -> Any:
    def decide(state: DocsState) -> str:
        if state.get("relevant_chunks"):
            return "generator"
        if state.get("rewrite_count", 0) < max_rewrites:
            return "rewriter"
        return "no_context"

    return decide
