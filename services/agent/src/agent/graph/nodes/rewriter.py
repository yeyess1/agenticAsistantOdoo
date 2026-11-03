"""`rewriter` (R-03, R-07): rephrases and/or translates the query ES -> EN, bounded loop."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agent.graph.prompts import load_prompt
from agent.graph.runtime import GraphDeps, Tracker, ainvoke_structured, traced
from agent.graph.state import DocsState, RewriteOutput


def make_rewriter(deps: GraphDeps) -> Any:
    @traced("rewriter", "docs", deps.model_name("rewriter"))
    async def rewriter(state: DocsState, t: Tracker) -> dict[str, Any]:
        previous = state.get("rewrites", [])
        tried = [state["standalone_question"], *(r.query for r in previous)]
        titles = sorted({f"{c.title} > {c.section}" for c in state.get("retrieved", [])[:5]})
        out = await ainvoke_structured(
            deps.model("rewriter"),
            RewriteOutput,
            [
                SystemMessage(content=load_prompt("rewriter")),
                HumanMessage(
                    content="Original question:\n"
                    f"{state['standalone_question']}\n\nQueries already tried (all failed):\n"
                    + "\n".join(f"- {q}" for q in tried)
                    + "\n\nSections retrieved (not relevant):\n"
                    + ("\n".join(f"- {x}" for x in titles) or "- none")
                ),
            ],
            t,
        )
        if out is None:  # keep the loop bounded and moving even if the LLM failed
            out = RewriteOutput(
                query=state["standalone_question"],
                language="es",
                strategy="rephrase",
                reason="rewriter failed; reusing the question",
            )
        t.detail.update(
            {
                "rewritten": out.query,
                "language": out.language,
                "strategy": out.strategy,
                "attempt": len(previous) + 1,
            }
        )
        return {
            "query": out.query,
            "rewrite_count": state.get("rewrite_count", 0) + 1,
            "rewrites": [*previous, out],
        }

    return rewriter
