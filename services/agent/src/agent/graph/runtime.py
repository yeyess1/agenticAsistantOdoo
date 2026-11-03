"""Node runtime: dependencies, event emission and per-node tracing (A-06, D-13)."""

from __future__ import annotations

import functools
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from common.llm import Role, get_chat_model, model_name_for
from common.pricing import cost_usd
from common.reranker import NoopReranker, Reranker
from common.retriever import Retriever
from common.schemas.events import (
    ErrorEvent,
    EventBase,
    NodeFinished,
    NodeStarted,
    TokenEvent,
    Usage,
)
from common.settings import Settings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langgraph.config import get_stream_writer
from langgraph.errors import GraphBubbleUp
from pydantic import BaseModel

from agent.graph.reducers import Reset
from agent.graph.state import AgentName, Step
from agent.tools.forum import ForumTools

NodeFn = Callable[[Any, "Tracker"], Awaitable[dict[str, Any]]]


@dataclass
class GraphDeps:
    """Everything the nodes need; injected so tests can pass fakes (no network)."""

    settings: Settings
    retriever: Retriever
    forum: ForumTools
    models: dict[str, BaseChatModel] | None = None
    reranker: Reranker | None = None

    def model(self, role: Role) -> BaseChatModel:
        if self.models is None:
            self.models = {}
        if role not in self.models:
            self.models[role] = get_chat_model(role, self.settings)
        return self.models[role]

    def model_name(self, role: Role) -> str:
        return model_name_for(role, self.settings)

    def get_reranker(self) -> Reranker:
        return self.reranker or NoopReranker()


def emit(event: EventBase) -> None:
    """Send an event to the custom stream; a no-op outside a graph run (direct node calls)."""
    try:
        writer = get_stream_writer()
    except RuntimeError:
        return
    writer(event)


def msg_text(message: BaseMessage) -> str:
    """Plain text of a message (content may be a string or a list of blocks)."""
    content = message.content
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "".join(parts)


class Tracker:
    """Collects model, token usage and `detail` of one node execution."""

    def __init__(self, node: str, agent: AgentName, model: str | None) -> None:
        self.node = node
        self.agent: AgentName = agent
        self.model = model
        self.detail: dict[str, Any] = {}
        self.input_tokens = 0
        self.output_tokens = 0

    def add_usage(self, message: BaseMessage | None) -> None:
        usage = getattr(message, "usage_metadata", None)
        if usage:
            self.input_tokens += int(usage.get("input_tokens", 0))
            self.output_tokens += int(usage.get("output_tokens", 0))

    def token(self, text: str) -> None:
        if text:
            emit(TokenEvent(node=self.node, text=text))

    @property
    def cost_usd(self) -> float:
        return cost_usd(self.model or "", self.input_tokens, self.output_tokens)


def traced(
    node: str, agent: AgentName, model: str | None = None
) -> Callable[[NodeFn], Callable[[Any], Awaitable[dict[str, Any]]]]:
    """Wrap a node: emits `node_started`/`node_finished` and appends a `Step` to the state."""

    def decorator(fn: NodeFn) -> Callable[[Any], Awaitable[dict[str, Any]]]:
        @functools.wraps(fn)
        async def wrapper(state: Any) -> dict[str, Any]:
            tracker = Tracker(node, agent, model)
            started_at = datetime.now(UTC)
            t0 = time.perf_counter()
            emit(NodeStarted(node=node, agent=agent))
            try:
                update = await fn(state, tracker)
            except GraphBubbleUp:
                raise
            except Exception as exc:
                emit(ErrorEvent(code="node_failed", message=str(exc)[:500], node=node))
                raise
            duration_ms = int((time.perf_counter() - t0) * 1000)
            step: Step = {
                "id": uuid.uuid4().hex,
                "node": node,
                "agent": agent,
                "started_at": started_at,
                "duration_ms": duration_ms,
                "model": tracker.model if (tracker.input_tokens or tracker.output_tokens) else None,
                "input_tokens": tracker.input_tokens,
                "output_tokens": tracker.output_tokens,
                "cost_usd": tracker.cost_usd,
                "detail": tracker.detail,
            }
            prior = update.get("steps")
            update["steps"] = Reset([*prior.items, step]) if isinstance(prior, Reset) else [step]
            has_usage = bool(tracker.input_tokens or tracker.output_tokens)
            emit(
                NodeFinished(
                    node=node,
                    agent=agent,
                    duration_ms=duration_ms,
                    model=tracker.model if has_usage else None,
                    usage=Usage(
                        input_tokens=tracker.input_tokens,
                        output_tokens=tracker.output_tokens,
                        cost_usd=tracker.cost_usd,
                    )
                    if has_usage
                    else None,
                    detail=tracker.detail,
                )
            )
            return update

        return wrapper

    return decorator


async def ainvoke_structured[T: BaseModel](
    model: BaseChatModel, schema: type[T], messages: list[BaseMessage], tracker: Tracker
) -> T | None:
    """Structured output without forced `tool_choice` (V-k); `None` if the call or parse fails."""
    runnable = model.with_structured_output(schema, method="json_schema", include_raw=True)
    try:
        out = await runnable.ainvoke(messages)
    except Exception as exc:
        tracker.detail["llm_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
        return None
    raw = out.get("raw") if isinstance(out, dict) else None
    tracker.add_usage(raw)
    parsed = out.get("parsed") if isinstance(out, dict) else out
    if isinstance(parsed, schema):
        return parsed
    tracker.detail["llm_error"] = "unparsable structured output"
    return None


async def astream_text(
    model: BaseChatModel, messages: list[BaseMessage], tracker: Tracker
) -> AIMessage:
    """Stream a completion, emitting a `token` event per text delta; returns the full message."""
    final: AIMessageChunk | None = None
    async for chunk in model.astream(messages):
        tracker.token(msg_text(chunk))
        final = chunk if final is None else final + chunk
    if final is None:
        return AIMessage(content="")
    tracker.add_usage(final)
    return AIMessage(
        content=final.content, tool_calls=final.tool_calls, id=final.id, name=final.name
    )
