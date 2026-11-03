"""`generator` (R-04): Spanish answer with `[n]` citations, streamed."""

from __future__ import annotations

from typing import Any

from common.schemas.api import SourceRef
from common.schemas.events import SourcesEvent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agent.citations import build_doc_sources, mark_cited
from agent.graph.prompts import load_prompt
from agent.graph.runtime import GraphDeps, Tracker, astream_text, emit, msg_text, traced
from agent.graph.state import DocsState


def make_generator(deps: GraphDeps) -> Any:
    @traced("generator", "docs", deps.model_name("generator"))
    async def generator(state: DocsState, t: Tracker) -> dict[str, Any]:
        chunks = state["relevant_chunks"]
        sources = build_doc_sources(chunks)
        emit(SourcesEvent(sources=[SourceRef(**s) for s in sources]))
        context = "\n\n".join(
            f"[{s['n']}] {c.title} > {c.section or '-'}\n{c.text}"
            for s, c in zip(sources, chunks, strict=True)
        )
        reply = await astream_text(
            deps.model("generator"),
            [
                SystemMessage(content=load_prompt("generator")),
                HumanMessage(
                    content=f"Documentation excerpts:\n\n{context}\n\n"
                    f"Question: {state['standalone_question']}"
                ),
            ],
            t,
        )
        answer = msg_text(reply).strip()
        marked, invalid = mark_cited(sources, answer)
        t.detail.update(
            {
                "n_sources": len(sources),
                "n_cited": sum(s["cited"] for s in marked),
                "invalid_citations": invalid,
            }
        )
        return {
            "answer": answer,
            "answered_by": "docs",
            "sources": marked,
            "no_context": False,
            "messages": [AIMessage(content=answer)],
        }

    return generator


def make_no_context() -> Any:
    @traced("no_context", "docs")
    async def no_context(state: DocsState, t: Tracker) -> dict[str, Any]:
        t.detail.update({"rewrites": state.get("rewrite_count", 0)})
        return {"no_context": True}

    return no_context
