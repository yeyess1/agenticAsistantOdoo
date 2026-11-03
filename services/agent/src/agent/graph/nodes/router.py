"""`router` (S-02): docs / research / direct."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agent.graph.prompts import load_prompt
from agent.graph.runtime import GraphDeps, Tracker, ainvoke_structured, traced
from agent.graph.state import GraphState, RouteDecision


def make_router(deps: GraphDeps) -> Any:
    @traced("router", "supervisor", deps.model_name("router"))
    async def router(state: GraphState, t: Tracker) -> dict[str, Any]:
        out = await ainvoke_structured(
            deps.model("router"),
            RouteDecision,
            [
                SystemMessage(content=load_prompt("router")),
                HumanMessage(content=state["standalone_question"]),
            ],
            t,
        )
        if out is None:  # fail towards the main path: the docs agent can still delegate
            route, reason = "docs", "router failed; defaulting to docs"
        else:
            route, reason = out.route, out.reason
        t.detail.update({"route": route, "reason": reason})
        return {"route": route, "route_reason": reason}

    return router


def route_from_router(state: GraphState) -> str:
    return state.get("route") or "docs"
