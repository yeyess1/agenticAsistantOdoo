"""Fakes for the agent tests: scripted chat models, retriever and search provider (no network)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from agent.graph.runtime import GraphDeps
from agent.tools.forum import ForumTools
from common.schemas.chunk import RetrievalFilters, ScoredChunk
from common.schemas.tools import ForumHit
from common.settings import Settings
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGenerationChunk
from langchain_core.runnables import RunnableLambda
from pydantic import ConfigDict, Field

ROLES = ("contextualizer", "router", "grader", "rewriter", "direct", "generator", "research")


class ScriptedChat(GenericFakeChatModel):
    """`GenericFakeChatModel` plus scripted structured outputs and recorded inputs."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    structured: list[Any] = Field(default_factory=list)
    seen: list[list[BaseMessage]] = Field(default_factory=list)
    usage: dict[str, int] | None = None
    bound_tools: list[str] = Field(default_factory=list)

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        async def run(messages: Any) -> dict[str, Any]:
            self.seen.append(list(messages))
            item = self.structured.pop(0)
            if isinstance(item, Exception):
                raise item
            raw = AIMessage(content="", usage_metadata=self.usage)
            return {"raw": raw, "parsed": item}

        def sync(messages: Any) -> dict[str, Any]:
            raise NotImplementedError

        return RunnableLambda(sync, afunc=run)

    def bind_tools(self, tools: Any, **kwargs: Any) -> Any:
        self.bound_tools = [t.name for t in tools]
        return self

    async def _astream(self, messages: Any, *args: Any, **kwargs: Any) -> Any:
        """Stream the next scripted message word by word; tool calls ride on the last chunk."""
        self.seen.append(list(messages))
        msg = next(self.messages)
        assert isinstance(msg, AIMessage)
        words = str(msg.content).split(" ") if msg.content else []
        for i, word in enumerate(words):
            yield ChatGenerationChunk(
                message=AIMessageChunk(content=word + (" " if i < len(words) - 1 else ""))
            )
        yield ChatGenerationChunk(
            message=AIMessageChunk(content="", tool_calls=msg.tool_calls, usage_metadata=self.usage)
        )


def ai(text: str = "", calls: list[tuple[str, dict[str, Any]]] | None = None) -> AIMessage:
    tool_calls = [
        {"name": n, "args": a, "id": f"call_{i}_{n}", "type": "tool_call"}
        for i, (n, a) in enumerate(calls or [])
    ]
    return AIMessage(content=text, tool_calls=tool_calls)


def scripted(*replies: AIMessage, structured: list[Any] | None = None) -> ScriptedChat:
    it: Iterator[AIMessage] = iter(replies)
    return ScriptedChat(messages=it, structured=list(structured or []))


def chunk(
    i: int, *, doc: str = "d1", anchor: str | None = None, page: int | None = None
) -> ScoredChunk:
    return ScoredChunk(
        chunk_id=f"chunk-{i}",
        doc_id=doc,
        score=1.0 - i / 100,
        text=f"text of chunk {i}",
        title=f"Title {i}",
        section=f"Title {i} > Section {i}",
        url=f"https://www.odoo.com/documentation/19.0/page{i}.html"
        + (f"#{anchor}" if anchor else ""),
        anchor=f"#{anchor}" if anchor else None,
        page=page,
    )


class FakeRetriever:
    def __init__(self, *results: list[ScoredChunk]) -> None:
        self._results = list(results)
        self.calls: list[tuple[str, RetrievalFilters | None, int]] = []

    async def retrieve(
        self, query: str, filters: RetrievalFilters | None = None, k: int = 10
    ) -> list[ScoredChunk]:
        self.calls.append((query, filters, k))
        idx = min(len(self.calls) - 1, len(self._results) - 1)
        return self._results[idx] if self._results else []


class FakeProvider:
    """SearchProvider: scripted outcomes per call (list of hits, or an Exception to raise)."""

    def __init__(self, *outcomes: list[ForumHit] | Exception) -> None:
        self._outcomes = list(outcomes)
        self.calls: list[tuple[str, str, int]] = []

    async def search(self, query: str, *, site: str, max_results: int) -> list[ForumHit]:
        self.calls.append((query, site, max_results))
        outcome = self._outcomes[min(len(self.calls) - 1, len(self._outcomes) - 1)]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def hit(path: str, title: str = "A post", host: str = "www.odoo.com") -> ForumHit:
    return ForumHit(title=title, url=f"https://{host}{path}", snippet="snippet")


def make_settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "_env_file": None,
        "max_rewrites": 2,
        "research_max_iterations": 4,
        "search_max_retries": 1,
        "search_timeout_s": 0.05,
        "read_timeout_s": 0.05,
    }
    base.update(overrides)
    return Settings(**base)


async def _no_sleep(_: float) -> None:
    return None


def make_deps(
    *,
    retriever: FakeRetriever | None = None,
    provider: FakeProvider | None = None,
    models: dict[str, ScriptedChat] | None = None,
    http: Any = None,
    **settings: Any,
) -> GraphDeps:
    s = make_settings(**settings)
    all_models: dict[str, Any] = {r: scripted() for r in ROLES}
    all_models.update(models or {})
    forum = ForumTools(
        provider or FakeProvider([]), s, http=http, sleep=_no_sleep, min_interval_s=0
    )
    return GraphDeps(
        settings=s,
        retriever=retriever or FakeRetriever(),
        forum=forum,
        models=all_models,
    )


def model_of(deps: GraphDeps, role: str) -> ScriptedChat:
    assert deps.models is not None
    model = deps.models[role]
    assert isinstance(model, ScriptedChat)
    return model
