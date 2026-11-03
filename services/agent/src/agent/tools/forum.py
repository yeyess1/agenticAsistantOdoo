"""Odoo forum tools for the research agent (X-01, X-02, D-07, ARCHITECTURE §8).

Both tools have typed input/output, a timeout, retries with exponential backoff and
jitter, a TTL cache and the domain allowlist. They never raise to the LLM: failures come
back as `status=timeout|error|empty` with a message the model can act on.
"""

from __future__ import annotations

import asyncio
import logging
import random
import ssl
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import httpx
from bs4 import BeautifulSoup
from common.schemas.tools import (
    ForumAnswer,
    ForumHit,
    ReadForumPostInput,
    ReadForumPostOutput,
    SearchOdooForumInput,
    SearchOdooForumOutput,
    ToolStatus,
)
from common.search_provider import SearchProvider
from common.settings import Settings
from langchain_core.tools import BaseTool, StructuredTool

from agent.tools.allowlist import is_allowed_url
from agent.tools.cache import TTLCache

log = logging.getLogger(__name__)
T = TypeVar("T")

MIN_REQUEST_INTERVAL_S = 1.0  # politeness pause between requests to the forum
MAX_ANSWER_CHARS = 2500
MAX_QUESTION_CHARS = 2000
MAX_ANSWERS = 3


def forum_ssl_context() -> ssl.SSLContext:
    """TLS context for www.odoo.com, capped at TLS 1.2.

    Found in the Phase 2 smoke run: with ALPN `http/1.1` over TLS 1.3 the server stalls the
    response forever from the `python:3.12-slim` image (OpenSSL 3.0.22), while TLS 1.2 answers
    in ~1 s. The cap is harmless for read-only public pages.
    """
    ctx = ssl.create_default_context()
    ctx.maximum_version = ssl.TLSVersion.TLSv1_2
    return ctx


class ForumTools:
    def __init__(
        self,
        provider: SearchProvider,
        settings: Settings,
        *,
        http: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        min_interval_s: float = MIN_REQUEST_INTERVAL_S,
    ) -> None:
        self._provider = provider
        self._s = settings
        self._http = http or httpx.AsyncClient(
            headers={"User-Agent": settings.http_user_agent},
            follow_redirects=True,
            verify=forum_ssl_context(),
        )
        self._sleep = sleep
        self._min_interval = min_interval_s
        self._last_request = 0.0
        self._pace_lock = asyncio.Lock()
        self._cache = TTLCache(settings.search_cache_ttl_s)
        self.domains = settings.forum_allowed_domain_list

    async def aclose(self) -> None:
        await self._http.aclose()

    # --- shared plumbing ---------------------------------------------------------------

    async def _pace(self) -> None:
        async with self._pace_lock:
            wait = self._last_request + self._min_interval - time.monotonic()
            if wait > 0:
                await self._sleep(wait)
            self._last_request = time.monotonic()

    async def _with_retries(
        self, call: Callable[[], Awaitable[T]], timeout_s: float
    ) -> tuple[T | None, ToolStatus, str | None]:
        """Run `call` with timeout and `SEARCH_MAX_RETRIES` retries (backoff + jitter)."""
        attempts = self._s.search_max_retries + 1
        status, message = ToolStatus.ERROR, None
        for attempt in range(attempts):
            try:
                await self._pace()
                return await asyncio.wait_for(call(), timeout_s), ToolStatus.OK, None
            except TimeoutError:
                status, message = ToolStatus.TIMEOUT, f"timed out after {timeout_s:g}s"
            except Exception as exc:
                status, message = ToolStatus.ERROR, f"{type(exc).__name__}: {str(exc)[:200]}"
            log.warning("forum tool attempt %d/%d failed: %s", attempt + 1, attempts, message)
            if attempt < attempts - 1:
                await self._sleep(min(8.0, 0.5 * 2**attempt) * (0.5 + random.random()))
        return None, status, f"{message} (after {attempts} attempts)"

    # --- search_odoo_forum -------------------------------------------------------------

    async def search_odoo_forum(self, args: SearchOdooForumInput) -> SearchOdooForumOutput:
        key = TTLCache.make_key("search", q=args.query, n=args.max_results)
        if (cached := self._cache.get(key)) is not None:
            return SearchOdooForumOutput.model_validate(cached)

        site = f"{self.domains[0]}/forum" if self.domains else "www.odoo.com/forum"
        hits, status, message = await self._with_retries(
            lambda: self._provider.search(
                args.query, site=site, max_results=min(10, args.max_results * 2)
            ),
            self._s.search_timeout_s,
        )
        if hits is None:
            return SearchOdooForumOutput(status=status, message=message)
        allowed = self._dedupe([h for h in hits if is_allowed_url(str(h.url), self.domains)])
        allowed = allowed[: args.max_results]
        if not allowed:
            out = SearchOdooForumOutput(
                status=ToolStatus.EMPTY,
                message="No forum posts found. Try different English keywords "
                "(API or model names, exact error text).",
            )
        else:
            out = SearchOdooForumOutput(status=ToolStatus.OK, results=allowed)
        self._cache.set(key, out.model_dump(mode="json"))
        return out

    @staticmethod
    def _dedupe(hits: list[ForumHit]) -> list[ForumHit]:
        seen: set[str] = set()
        unique: list[ForumHit] = []
        for h in hits:
            if str(h.url) not in seen:
                seen.add(str(h.url))
                unique.append(h)
        return unique

    # --- read_forum_post ---------------------------------------------------------------

    async def read_forum_post(self, args: ReadForumPostInput) -> ReadForumPostOutput:
        url = str(args.url)
        if not is_allowed_url(url, self.domains):
            return ReadForumPostOutput(
                status=ToolStatus.ERROR,
                url=args.url,
                message=f"URL not allowed: only posts under {', '.join(self.domains)}/forum/ "
                "can be read.",
            )
        key = TTLCache.make_key("read", url=url)
        if (cached := self._cache.get(key)) is not None:
            return ReadForumPostOutput.model_validate(cached)

        async def fetch() -> str:
            resp = await self._http.get(url, timeout=self._s.read_timeout_s)
            resp.raise_for_status()
            return resp.text

        html, status, message = await self._with_retries(fetch, self._s.read_timeout_s)
        if html is None:
            return ReadForumPostOutput(status=status, url=args.url, message=message)
        out = parse_forum_post(html, args.url)
        if out.status is ToolStatus.OK:
            self._cache.set(key, out.model_dump(mode="json"))
        return out

    # --- LangChain tools (bound to the research model) ------------------------------------

    def as_tools(self) -> list[BaseTool]:
        async def _search(query: str, max_results: int = 5) -> str:
            out = await self.search_odoo_forum(
                SearchOdooForumInput(query=query, max_results=max_results)
            )
            return out.model_dump_json()

        async def _read(url: str) -> str:
            out = await self.read_forum_post(ReadForumPostInput(url=url))
            return out.model_dump_json()

        return [
            StructuredTool.from_function(
                coroutine=_search,
                name="search_odoo_forum",
                description="Search the official Odoo forum (www.odoo.com/forum). Use concise "
                "English keywords. Returns title, url and snippet of matching posts.",
                args_schema=SearchOdooForumInput,
            ),
            StructuredTool.from_function(
                coroutine=_read,
                name="read_forum_post",
                description="Read one Odoo forum post (question and answers). The URL must "
                "come from search_odoo_forum.",
                args_schema=ReadForumPostInput,
            ),
        ]


def parse_forum_post(html: str, url: Any) -> ReadForumPostOutput:
    """Extract question and answers from an Odoo forum post page."""
    soup = BeautifulSoup(html, "lxml")
    h1 = soup.select_one("h1")
    title = h1.get_text(" ", strip=True) if h1 else None
    question_el = soup.select_one(".o_wforum_question .o_wforum_post_content")
    question = question_el.get_text("\n", strip=True)[:MAX_QUESTION_CHARS] if question_el else None
    answers: list[ForumAnswer] = []
    for el in soup.select(".o_wforum_answer"):
        body_el = el.select_one(".o_wforum_post_content")
        if body_el is None:
            continue
        votes_el = el.select_one(".vote_count")
        try:
            votes = int(votes_el.get_text(strip=True)) if votes_el else None
        except ValueError:
            votes = None
        badge = el.select_one(".o_wforum_answer_correct_badge")
        accepted = bool(badge) and "d-none" not in (badge.get("class") or [])  # type: ignore[union-attr]
        answers.append(
            ForumAnswer(
                body=body_el.get_text("\n", strip=True)[:MAX_ANSWER_CHARS],
                votes=votes,
                accepted=accepted,
            )
        )
    answers.sort(key=lambda a: (not a.accepted, -(a.votes or 0)))
    if not question and not answers:
        return ReadForumPostOutput(
            status=ToolStatus.EMPTY,
            url=url,
            title=title,
            message="No readable content in the post.",
        )
    return ReadForumPostOutput(
        status=ToolStatus.OK, url=url, title=title, question=question, answers=answers[:MAX_ANSWERS]
    )
