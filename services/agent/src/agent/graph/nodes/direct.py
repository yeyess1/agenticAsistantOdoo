"""`direct_answer` (S-03): greetings and out-of-scope requests, in Spanish."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agent.graph.history import trim_history
from agent.graph.prompts import load_prompt
from agent.graph.runtime import GraphDeps, Tracker, astream_text, msg_text, traced
from agent.graph.state import GraphState


def make_direct(deps: GraphDeps) -> Any:
    s = deps.settings

    @traced("direct_answer", "supervisor", deps.model_name("direct"))
    async def direct_answer(state: GraphState, t: Tracker) -> dict[str, Any]:
        # `messages` already holds the current turn's HumanMessage (added by contextualize).
        prior = list(state.get("messages", []))[:-1]
        history = trim_history(prior, s.history_max_turns, s.history_max_tokens)
        question = state["standalone_question"]
        system = load_prompt("direct")
        if state.get("external_approved") is False:
            system += "\n\nNote: the user declined the external forum search."
        messages = [SystemMessage(content=system), *history, HumanMessage(content=question)]
        reply = await astream_text(deps.model("direct"), messages, t)
        answer = msg_text(reply).strip()
        return {
            "answer": answer,
            "answered_by": "direct",
            "messages": [AIMessage(content=answer)],
        }

    return direct_answer
