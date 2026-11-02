"""SearchProvider interface and `ddgs` implementation (A-08, D-07).

Timeouts, retries, cache and allowlist filtering belong to the forum tool (X-02) and
are added in Phase 2; this module only adapts the search backend.
"""

from __future__ import annotations

import asyncio
from typing import Any, Protocol

from common.schemas.tools import ForumHit


class SearchProvider(Protocol):
    async def search(self, query: str, *, site: str, max_results: int) -> list[ForumHit]: ...


class DdgsProvider:
    """Web search through the `ddgs` library (no API key), scoped with `site:`."""

    def __init__(self, *, timeout_s: float = 10.0) -> None:
        self._timeout_s = timeout_s

    def _search_sync(self, query: str, site: str, max_results: int) -> list[dict[str, Any]]:
        from ddgs import DDGS

        return list(
            DDGS(timeout=int(self._timeout_s)).text(f"site:{site} {query}", max_results=max_results)
        )

    async def search(self, query: str, *, site: str, max_results: int) -> list[ForumHit]:
        raw = await asyncio.to_thread(self._search_sync, query, site, max_results)
        hits: list[ForumHit] = []
        for r in raw:
            href = r.get("href")
            if not href:
                continue
            hits.append(
                ForumHit(title=str(r.get("title", "")), url=href, snippet=str(r.get("body", "")))
            )
        return hits
