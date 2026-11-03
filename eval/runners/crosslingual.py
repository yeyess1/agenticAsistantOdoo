"""Retrieval quality via `/search` (recall@k, precision@k, MRR, context precision) and the
cross-lingual experiment E-09: Spanish question vs its manual English translation.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from metrics.retrieval import (
    SectionKey,
    chunk_key,
    context_precision,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    relevance_flags,
)
from metrics.stats import mean, rnd

from runners.client import AgentClient
from runners.golden import GoldenItem

K_VALUES: tuple[int, ...] = (1, 3, 5, 10)
TOP_K = 10


def ranked_keys(results: Sequence[dict[str, Any]]) -> list[SectionKey]:
    return [chunk_key(r["url"], r.get("anchor"), r.get("page")) for r in results]


def ranking_metrics(keys: Sequence[SectionKey], relevant: set[SectionKey]) -> dict[str, Any]:
    hits = relevance_flags(keys, relevant)
    out: dict[str, Any] = {}
    for k in K_VALUES:
        out[f"recall@{k}"] = rnd(recall_at_k(keys, relevant, k))
        out[f"precision@{k}"] = rnd(precision_at_k(hits, k))
    out["rr"] = rnd(reciprocal_rank(hits))
    out["context_precision@10"] = rnd(context_precision(hits, TOP_K))
    out["hits"] = [int(h) for h in hits]
    return out


async def search_metrics(
    client: AgentClient, query: str, relevant: set[SectionKey]
) -> dict[str, Any]:
    resp = await client.search(query, top_k=TOP_K)
    keys = ranked_keys(resp["results"])
    out = ranking_metrics(keys, relevant)
    out["took_ms"] = resp.get("took_ms")
    return out


def retrieval_items(items: Sequence[GoldenItem]) -> list[GoldenItem]:
    """Items with labelled sections whose question stands alone (follow-up turn 1 included)."""
    return [i for i in items if i.relevant_sections and not i.is_follow_up_turn]


async def run_crosslingual(
    client: AgentClient, items: Sequence[GoldenItem], concurrency: int = 4
) -> dict[str, dict[str, Any]]:
    """Per item `{es: metrics, en: metrics}` over `/search` (no LLM involved)."""
    sem = asyncio.Semaphore(concurrency)

    async def one(item: GoldenItem) -> tuple[str, dict[str, Any]]:
        async with sem:
            es = await search_metrics(client, item.question, item.section_keys)
            en = await search_metrics(client, item.question_en, item.section_keys)
        return item.id, {"es": es, "en": en}

    pairs = await asyncio.gather(*(one(i) for i in items))
    return dict(pairs)


def aggregate_ranking(per_item: Sequence[dict[str, Any]]) -> dict[str, Any]:
    keys = [f"recall@{k}" for k in K_VALUES] + [f"precision@{k}" for k in K_VALUES]
    out: dict[str, Any] = {"n": len(per_item)}
    for key in keys:
        out[key] = rnd(mean(m[key] for m in per_item))
    out["mrr"] = rnd(mean(m["rr"] for m in per_item))
    out["context_precision@10"] = rnd(mean(m["context_precision@10"] for m in per_item))
    return out


def summarize_crosslingual(per_item: dict[str, dict[str, Any]]) -> dict[str, Any]:
    es = aggregate_ranking([v["es"] for v in per_item.values()])
    en = aggregate_ranking([v["en"] for v in per_item.values()])
    delta = {
        k: rnd(en[k] - es[k]) for k in es if k != "n" and es[k] is not None and en[k] is not None
    }
    wins = {
        "en_better": sorted(
            i for i, v in per_item.items() if v["en"]["recall@10"] > v["es"]["recall@10"]
        ),
        "es_better": sorted(
            i for i, v in per_item.items() if v["es"]["recall@10"] > v["en"]["recall@10"]
        ),
    }
    return {"es": es, "en": en, "delta_en_minus_es": delta, "recall@10_wins": wins}
