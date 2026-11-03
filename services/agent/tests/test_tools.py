"""Forum tools (X-01, X-02, X-04): timeout, retries, empty results, allowlist, cache."""

from __future__ import annotations

import asyncio

import httpx
from agent.tools.allowlist import is_allowed_url
from agent.tools.cache import TTLCache
from agent.tools.forum import ForumTools, parse_forum_post
from agent_fakes import FakeProvider, hit, make_settings
from common.schemas.tools import (
    ForumHit,
    ReadForumPostInput,
    SearchOdooForumInput,
    ToolStatus,
)
from common.search_provider import SearchProvider

POST_HTML = """
<html><body><h1>Compute Field Store</h1>
<div class="o_wforum_question"><div class="o_wforum_post_content">How do I store it?</div></div>
<div class="o_wforum_answer">
  <span class="vote_count">1</span>
  <span class="o_wforum_answer_correct_badge d-none">Best</span>
  <div class="o_wforum_post_content">Not accepted.</div></div>
<div class="o_wforum_answer">
  <span class="vote_count">3</span>
  <span class="o_wforum_answer_correct_badge">Best</span>
  <div class="o_wforum_post_content">Add store=True.</div></div>
</body></html>
"""


async def _no_sleep(_: float) -> None:
    return None


def tools(
    provider: SearchProvider, http: httpx.AsyncClient | None = None, **kw: object
) -> ForumTools:
    return ForumTools(provider, make_settings(**kw), http=http, sleep=_no_sleep, min_interval_s=0)


def test_allowlist() -> None:
    d = ["www.odoo.com"]
    assert is_allowed_url("https://www.odoo.com/forum/help-1/x-1", d)
    assert not is_allowed_url("https://www.odoo.com/documentation/19.0/", d)  # not /forum/
    assert not is_allowed_url("https://evil.com/forum/help-1/x", d)
    assert not is_allowed_url("https://www.odoo.com.evil.com/forum/x", d)
    assert not is_allowed_url("https://www.odoo.com/forum/help-1?search=x", d)  # robots.txt
    assert not is_allowed_url("ftp://www.odoo.com/forum/x", d)


def test_ttl_cache_expires_and_normalises_key() -> None:
    now = [0.0]
    cache = TTLCache(10, clock=lambda: now[0])
    key = TTLCache.make_key("s", q="  Compute  FIELD ")
    assert key == TTLCache.make_key("s", q="compute field")
    cache.set(key, 1)
    assert cache.get(key) == 1
    now[0] = 11
    assert cache.get(key) is None


async def test_search_ok_filters_allowlist_and_caches() -> None:
    provider = FakeProvider(
        [
            hit("/forum/help-1/a-1"),
            hit("/documentation/19.0/x"),
            hit("/forum/help-1/a-1"),
            hit("/forum/help-1/b-2", host="evil.com"),
        ]
    )
    t = tools(provider)
    out = await t.search_odoo_forum(SearchOdooForumInput(query="compute store"))
    assert out.status is ToolStatus.OK
    assert [str(h.url) for h in out.results] == ["https://www.odoo.com/forum/help-1/a-1"]
    assert provider.calls[0][1] == "www.odoo.com/forum"
    again = await t.search_odoo_forum(SearchOdooForumInput(query="Compute  STORE"))
    assert again.status is ToolStatus.OK and len(provider.calls) == 1  # cache hit


async def test_search_empty_when_everything_filtered_or_nothing() -> None:
    out = await tools(FakeProvider([hit("/x", host="evil.com")])).search_odoo_forum(
        SearchOdooForumInput(query="anything")
    )
    assert out.status is ToolStatus.EMPTY and out.message
    out = await tools(FakeProvider([])).search_odoo_forum(SearchOdooForumInput(query="anything"))
    assert out.status is ToolStatus.EMPTY


async def test_search_timeout_retries_then_reports_timeout() -> None:
    class Slow:
        calls = 0

        async def search(self, query: str, *, site: str, max_results: int) -> list[ForumHit]:
            Slow.calls += 1
            await asyncio.sleep(5)
            return []

    t = tools(Slow(), search_max_retries=2)
    out = await t.search_odoo_forum(SearchOdooForumInput(query="slow query"))
    assert out.status is ToolStatus.TIMEOUT and "3 attempts" in (out.message or "")
    assert Slow.calls == 3  # 1 + SEARCH_MAX_RETRIES


async def test_search_error_never_raises_and_retry_recovers() -> None:
    boom = FakeProvider(RuntimeError("rate limited"))
    out = await tools(boom).search_odoo_forum(SearchOdooForumInput(query="rate limit"))
    assert out.status is ToolStatus.ERROR and "rate limited" in (out.message or "")
    assert len(boom.calls) == 2

    flaky = FakeProvider(RuntimeError("once"), [hit("/forum/help-1/ok-1")])
    out = await tools(flaky).search_odoo_forum(SearchOdooForumInput(query="flaky one"))
    assert out.status is ToolStatus.OK and len(flaky.calls) == 2


async def test_failed_search_is_not_cached() -> None:
    provider = FakeProvider(RuntimeError("x"), RuntimeError("x"), [hit("/forum/help-1/a-1")])
    t = tools(provider)
    first = await t.search_odoo_forum(SearchOdooForumInput(query="not cached"))
    second = await t.search_odoo_forum(SearchOdooForumInput(query="not cached"))
    assert first.status is ToolStatus.ERROR and second.status is ToolStatus.OK


async def test_read_rejects_url_outside_allowlist_without_any_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no request must be made")

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    t = tools(FakeProvider([]), http=http)
    for url in ("https://evil.com/forum/help-1/x", "https://www.odoo.com/documentation/19.0/"):
        out = await t.read_forum_post(ReadForumPostInput(url=url))
        assert out.status is ToolStatus.ERROR and "not allowed" in (out.message or "")


async def test_read_parses_post_and_caches() -> None:
    hits = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        hits["n"] += 1
        return httpx.Response(200, text=POST_HTML)

    t = tools(FakeProvider([]), http=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    args = ReadForumPostInput(url="https://www.odoo.com/forum/help-1/x-1")
    out = await t.read_forum_post(args)
    assert out.status is ToolStatus.OK and out.title == "Compute Field Store"
    assert out.question == "How do I store it?"
    assert out.answers[0].accepted and out.answers[0].body == "Add store=True."  # accepted first
    assert out.answers[1].accepted is False
    await t.read_forum_post(args)
    assert hits["n"] == 1


async def test_read_http_error_and_timeout_statuses() -> None:
    def not_found(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    t = tools(FakeProvider([]), http=httpx.AsyncClient(transport=httpx.MockTransport(not_found)))
    args = ReadForumPostInput(url="https://www.odoo.com/forum/help-1/x-1")
    assert (await t.read_forum_post(args)).status is ToolStatus.ERROR

    async def slow(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(5)
        return httpx.Response(200)

    t = tools(FakeProvider([]), http=httpx.AsyncClient(transport=httpx.MockTransport(slow)))
    assert (await t.read_forum_post(args)).status is ToolStatus.TIMEOUT


def test_parse_empty_page() -> None:
    out = parse_forum_post("<html><body><h1>x</h1></body></html>", "https://www.odoo.com/forum/a-1")
    assert out.status is ToolStatus.EMPTY


async def test_langchain_tools_have_typed_schemas_and_return_json() -> None:
    t = tools(FakeProvider([hit("/forum/help-1/a-1")]))
    search, read = t.as_tools()
    assert search.name == "search_odoo_forum" and read.name == "read_forum_post"
    assert set(search.args) == {"query", "max_results"}
    raw = await search.ainvoke({"query": "compute store"})
    assert '"status":"ok"' in raw


def test_forum_ssl_context_is_capped_at_tls12() -> None:
    import ssl

    from agent.tools.forum import forum_ssl_context

    assert forum_ssl_context().maximum_version == ssl.TLSVersion.TLSv1_2
