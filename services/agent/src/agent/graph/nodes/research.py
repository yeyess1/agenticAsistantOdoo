"""Research agent nodes: `research_llm`, `tools`, `finalize_external` (X-01, X-03)."""

from __future__ import annotations

from typing import Any

from common.schemas.api import SourceRef
from common.schemas.events import SourcesEvent
from common.schemas.tools import ReadForumPostOutput, SearchOdooForumOutput, ToolStatus
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from agent.citations import extract_markers
from agent.graph.prompts import load_prompt
from agent.graph.runtime import GraphDeps, Tracker, astream_text, emit, msg_text, traced
from agent.graph.state import ExternalSource, GraphState, Source

NOT_FOUND = (
    "No encontré información relevante sobre esto ni en la documentación indexada ni en el "
    "foro de Odoo, así que prefiero no inventar una respuesta. Prueba a reformular la "
    "pregunta con nombres de modelos, campos o el texto exacto del error."
)
DELEGATED_NOTE = (
    "_La documentación indexada no cubre esta pregunta; la respuesta sale del foro de Odoo._"
)
FINAL_STEP_NOTE = (
    "This is the last step: do not call tools anymore. Write the final answer in Spanish "
    "from what you have read so far, or say that nothing relevant was found."
)


def make_research_llm(deps: GraphDeps) -> Any:
    max_iter = deps.settings.research_max_iterations
    tools = deps.forum.as_tools()

    @traced("research_llm", "research", deps.model_name("research"))
    async def research_llm(state: GraphState, t: Tracker) -> dict[str, Any]:
        iteration = state.get("research_iter", 0) + 1
        last = iteration >= max_iter
        model = deps.model("research")
        runnable = model if last else model.bind_tools(tools, tool_choice="auto")
        history = list(state.get("research_messages", []))
        messages = [
            SystemMessage(content=load_prompt("research")),
            HumanMessage(content=state["standalone_question"]),
            *history,
        ]
        if last:
            messages.append(HumanMessage(content=FINAL_STEP_NOTE))
        reply = await astream_text(runnable, messages, t)  # type: ignore[arg-type]
        t.detail.update(
            {
                "iteration": iteration,
                "max_iterations": max_iter,
                "tool_calls": [c["name"] for c in reply.tool_calls],
                "final_step": last,
            }
        )
        return {"research_messages": [reply], "research_iter": iteration}

    return research_llm


def route_after_research_llm(max_iter: int) -> Any:
    def decide(state: GraphState) -> str:
        msgs = state.get("research_messages", [])
        last = msgs[-1] if msgs else None
        has_calls = isinstance(last, AIMessage) and bool(last.tool_calls)
        if has_calls and state.get("research_iter", 0) < max_iter:
            return "tools"
        return "finalize_external"

    return decide


def _format_search(out: SearchOdooForumOutput, numbers: dict[str, int]) -> str:
    if out.status is not ToolStatus.OK:
        return f"status={out.status.value}. {out.message or ''}".strip()
    return "\n\n".join(
        f"[{numbers[str(h.url)]}] {h.title}\n{h.url}\n{h.snippet[:300]}" for h in out.results
    )


def _format_read(out: ReadForumPostOutput, n: int | None) -> str:
    if out.status is not ToolStatus.OK:
        return f"status={out.status.value}. {out.message or ''}".strip()
    parts = [f"[{n}] {out.title or ''}", f"QUESTION:\n{out.question or ''}"]
    for i, a in enumerate(out.answers, start=1):
        flags = (" (accepted)" if a.accepted else "") + (
            f" (votes: {a.votes})" if a.votes is not None else ""
        )
        parts.append(f"ANSWER {i}{flags}:\n{a.body}")
    return "\n\n".join(parts)


def make_tools_node(deps: GraphDeps) -> Any:
    forum = deps.forum

    @traced("tools", "research")
    async def tools(state: GraphState, t: Tracker) -> dict[str, Any]:
        last = state["research_messages"][-1]
        assert isinstance(last, AIMessage)
        registry: dict[str, ExternalSource] = {
            s["url"]: s for s in state.get("external_sources", [])
        }
        out_messages: list[ToolMessage] = []
        calls: list[dict[str, Any]] = []
        for call in last.tool_calls:
            name, args = call["name"], call["args"]
            status = "error"
            try:
                if name == "search_odoo_forum":
                    from common.schemas.tools import SearchOdooForumInput

                    res = await forum.search_odoo_forum(SearchOdooForumInput(**args))
                    for h in res.results:
                        registry.setdefault(
                            str(h.url),
                            {
                                "n": len(registry) + 1,
                                "url": str(h.url),
                                "title": h.title,
                                "read": False,
                            },
                        )
                    content = _format_search(res, {u: s["n"] for u, s in registry.items()})
                    status = res.status.value
                elif name == "read_forum_post":
                    from common.schemas.tools import ReadForumPostInput

                    read = await forum.read_forum_post(ReadForumPostInput(**args))
                    url = str(read.url)
                    if read.status is ToolStatus.OK:
                        entry = registry.setdefault(
                            url,
                            {
                                "n": len(registry) + 1,
                                "url": url,
                                "title": read.title or url,
                                "read": False,
                            },
                        )
                        entry["read"] = True
                        entry["title"] = read.title or entry["title"]
                    content = _format_read(read, registry[url]["n"] if url in registry else None)
                    status = read.status.value
                else:
                    content = f"status=error. Unknown tool {name!r}."
            except Exception as exc:  # bad arguments from the LLM, never crash the loop
                content = f"status=error. Invalid tool call: {str(exc)[:200]}"
            calls.append({"tool": name, "status": status})
            out_messages.append(ToolMessage(content=content, tool_call_id=call["id"], name=name))
        t.detail["calls"] = calls
        return {"research_messages": out_messages, "external_sources": list(registry.values())}

    return tools


def make_finalize_external() -> Any:
    @traced("finalize_external", "research")
    async def finalize_external(state: GraphState, t: Tracker) -> dict[str, Any]:
        msgs = state.get("research_messages", [])
        draft = ""
        for m in reversed(msgs):
            if isinstance(m, AIMessage) and not m.tool_calls:
                draft = msg_text(m).strip()
                break
        registry = state.get("external_sources", [])
        cited = set(extract_markers(draft))
        used = [s for s in registry if s["read"] or s["n"] in cited]
        used = [s for s in used if s["read"]] or used  # prefer posts actually read
        if not used or not draft:
            answer, sources = NOT_FOUND, []
        else:
            sources = [
                Source(
                    n=s["n"],
                    kind="external",
                    doc_id=None,
                    chunk_id=None,
                    title=s["title"],
                    section=None,
                    url=s["url"],
                    page=None,
                    score=None,
                    cited=s["n"] in cited,
                )
                for s in used
            ]
            links = "\n".join(f"[{s['n']}] Odoo Forum — {s['title']} — {s['url']}" for s in sources)
            note = f"{DELEGATED_NOTE}\n\n" if state.get("delegated") else ""
            answer = f"{note}{draft}\n\n---\n**Fuente externa: Odoo Forum**\n{links}"
            emit(SourcesEvent(sources=[SourceRef(**s) for s in sources]))
        t.detail.update(
            {
                "n_sources": len(sources),
                "found": bool(sources),
                "delegated": bool(state.get("delegated")),
            }
        )
        return {
            "answer": answer,
            "answered_by": "research",
            "sources": sources,
            "messages": [AIMessage(content=answer)],
        }

    return finalize_external
