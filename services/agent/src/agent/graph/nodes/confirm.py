"""`confirm_external_search` (S-07, D-13): passive pass-through; `interrupt()` when HITL is on."""

from __future__ import annotations

from typing import Any

from langgraph.types import interrupt

from agent.graph.runtime import GraphDeps, Tracker, traced
from agent.graph.state import GraphState


def make_confirm(deps: GraphDeps) -> Any:
    @traced("confirm_external_search", "research")
    async def confirm(state: GraphState, t: Tracker) -> dict[str, Any]:
        approved = True
        if deps.settings.hitl_enabled:  # challenge D: wired, off by default
            decision = interrupt(
                {"kind": "confirm_external_search", "query": state["standalone_question"]}
            )
            approved = bool(
                decision.get("approved", False) if isinstance(decision, dict) else decision
            )
        t.detail.update({"approved": approved, "hitl": deps.settings.hitl_enabled})
        return {"external_approved": approved, "delegated": bool(state.get("no_context"))}

    return confirm


def route_after_confirm(state: GraphState) -> str:
    return "research_llm" if state.get("external_approved", True) else "direct_answer"
