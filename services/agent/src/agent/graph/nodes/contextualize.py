"""`contextualize` (S-06, D-08): rewrites a follow-up into a standalone question."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agent.graph.history import trim_history
from agent.graph.prompts import load_prompt
from agent.graph.reducers import Reset
from agent.graph.runtime import GraphDeps, Tracker, ainvoke_structured, msg_text, traced
from agent.graph.state import GraphState, StandaloneQuestion


def make_contextualize(deps: GraphDeps) -> Any:
    s = deps.settings

    @traced("contextualize", "supervisor", deps.model_name("contextualizer"))
    async def contextualize(state: GraphState, t: Tracker) -> dict[str, Any]:
        question = state["question"].strip()
        history = trim_history(
            list(state.get("messages", [])), s.history_max_turns, s.history_max_tokens
        )
        # Per-turn fields are reset here: the checkpointer carries the state across turns.
        update: dict[str, Any] = {
            "messages": [HumanMessage(content=question)],
            "route": None,
            "route_reason": "",
            "no_context": False,
            "delegated": False,
            "answered_by": None,
            "answer": "",
            "external_approved": True,
            "research_messages": Reset([]),
            "research_iter": 0,
            "external_sources": Reset([]),
            "steps": Reset([]),
            "sources": Reset([]),
        }
        standalone = question
        if history:
            transcript = "\n".join(
                f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {msg_text(m)[:800]}"
                for m in history
            )
            out = await ainvoke_structured(
                deps.model("contextualizer"),
                StandaloneQuestion,
                [
                    SystemMessage(content=load_prompt("contextualize")),
                    HumanMessage(
                        content=f"Conversation so far:\n{transcript}\n\n"
                        f"Latest user message:\n{question}"
                    ),
                ],
                t,
            )
            if out is not None and out.question.strip():
                standalone = out.question.strip()
            t.detail["history_messages"] = len(history)
        else:
            t.detail["passthrough"] = True
        t.detail["rewritten"] = standalone != question
        t.detail["standalone_question"] = standalone
        update["standalone_question"] = standalone
        return update

    return contextualize
