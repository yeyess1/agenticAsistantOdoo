"""Thin async client for the agent API (`/query`, `/query/resume`, `/search`)."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

RETRY_STATUSES = {502, 503, 504}


class AgentClient:
    def __init__(self, base_url: str, *, timeout_s: float = 300.0, retries: int = 1) -> None:
        self._http = httpx.AsyncClient(base_url=base_url, timeout=timeout_s)
        self._retries = retries

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        last: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                resp = await self._http.post(path, json=body)
                if resp.status_code in RETRY_STATUSES and attempt < self._retries:
                    await asyncio.sleep(2.0)
                    continue
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
                return data
            except httpx.TransportError as exc:  # connection reset, read timeout
                last = exc
                await asyncio.sleep(2.0)
        raise RuntimeError(f"POST {path} failed: {last}")

    async def query(self, question: str, thread_id: str, mode: str) -> dict[str, Any]:
        """One turn. A pending HITL interrupt is approved via `/query/resume`.

        Latency is measured client-side over the whole turn (including the resume).
        Usage, steps and nodes of the paused part are merged into the final response.
        """
        started = time.perf_counter()
        body = {"question": question, "thread_id": thread_id, "mode": mode}
        resp = await self._post("/query", body)
        interrupts = 0
        while resp.get("interrupt") and interrupts < 3:
            interrupts += 1
            paused = resp
            resp = await self._post("/query/resume", {"thread_id": thread_id, "approved": True})
            resp = _merge_paused(paused, resp)
        resp["client_latency_ms"] = int((time.perf_counter() - started) * 1000)
        resp["interrupts"] = interrupts
        return resp

    async def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        exact: bool = False,
        hnsw_ef: int | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"query": query, "top_k": top_k, "exact": exact}
        if hnsw_ef is not None:
            body["hnsw_ef"] = hnsw_ef
        return await self._post("/search", body)

    async def aclose(self) -> None:
        await self._http.aclose()


def _merge_paused(paused: dict[str, Any], final: dict[str, Any]) -> dict[str, Any]:
    seen = {s["id"] for s in final.get("steps", [])}
    earlier = [s for s in paused.get("steps", []) if s["id"] not in seen]
    merged = dict(final)
    merged["steps"] = earlier + list(final.get("steps", []))
    merged["nodes"] = [s["node"] for s in merged["steps"]]
    merged["usage"] = {
        "input_tokens": sum(s["input_tokens"] for s in merged["steps"]),
        "output_tokens": sum(s["output_tokens"] for s in merged["steps"]),
        "cost_usd": sum(s["cost_usd"] for s in merged["steps"]),
    }
    return merged
