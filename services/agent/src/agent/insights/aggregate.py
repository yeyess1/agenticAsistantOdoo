"""Aggregate `query_log` rows into the insights payload (pure, unit-tested)."""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from collections.abc import Sequence
from typing import Any

from common.schemas.insights import (
    DayCount,
    DocumentStat,
    InsightsResponse,
    InsightsTotals,
    PhraseCount,
    QuestionCount,
    TokenBin,
    TopicStat,
)

from agent.insights.nlp import TOPICS, content_tokens, doc_topic, frequent_phrases, normalize

TOKEN_BIN = 100  # width of the answer-length histogram bins (tokens)


def _mean(values: Sequence[float]) -> float | None:
    return round(statistics.fmean(values), 1) if values else None


def _median(values: Sequence[float]) -> float | None:
    return round(float(statistics.median(values)), 1) if values else None


def _sources(row: dict[str, Any]) -> list[dict[str, Any]]:
    raw = row.get("sources") or []
    return json.loads(raw) if isinstance(raw, str) else list(raw)


def _questions(rows: Sequence[dict[str, Any]], top: int) -> list[QuestionCount]:
    """Most repeated questions, grouped by their content words (order and accents ignored)."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        key = " ".join(sorted(set(content_tokens(r["question"])))) or normalize(r["question"])
        groups[key].append(r)
    ranked = sorted(groups.values(), key=len, reverse=True)[:top]
    return [
        QuestionCount(
            question=g[-1]["question"],
            count=len(g),
            topic=Counter(x["topic"] for x in g).most_common(1)[0][0],
        )
        for g in ranked
    ]


def _documents(rows: Sequence[dict[str, Any]], top: int) -> list[DocumentStat]:
    retrieved: Counter[str] = Counter()
    cited: Counter[str] = Counter()
    titles: dict[str, str] = {}
    for r in rows:
        seen: set[str] = set()
        seen_cited: set[str] = set()
        for s in _sources(r):  # one turn counts a document once, even with several chunks
            if s.get("kind") != "doc" or not s.get("url"):
                continue
            url = str(s["url"]).split("#")[0]
            titles.setdefault(url, str(s.get("title") or url))
            seen.add(url)
            if s.get("cited"):
                seen_cited.add(url)
        retrieved.update(seen)
        cited.update(seen_cited)
    ranked = sorted(retrieved, key=lambda u: (cited[u], retrieved[u]), reverse=True)[:top]
    return [
        DocumentStat(
            title=titles[u], url=u, topic=doc_topic(u), retrieved=retrieved[u], cited=cited[u]
        )
        for u in ranked
    ]


def _histogram(values: Sequence[int]) -> list[TokenBin]:
    if not values:
        return []
    counts = Counter(v // TOKEN_BIN for v in values)
    return [
        TokenBin(lo=b * TOKEN_BIN, hi=(b + 1) * TOKEN_BIN, count=counts.get(b, 0))
        for b in range(min(counts), max(counts) + 1)
    ]


def aggregate(rows: Sequence[dict[str, Any]], *, top: int = 15) -> InsightsResponse:
    questions = [r["question"] for r in rows]
    answer_tokens = [int(r["answer_tokens"]) for r in rows if r["answer_tokens"]]
    topic_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        topic_rows[r["topic"]].append(r)
    n = len(rows)
    topics = sorted(
        (
            TopicStat(
                topic=t,
                label=TOPICS.get(t, t),
                count=len(rs),
                share=round(len(rs) / n, 4),
                answer_tokens_mean=_mean([x["answer_tokens"] for x in rs if x["answer_tokens"]]),
            )
            for t, rs in topic_rows.items()
        ),
        key=lambda s: s.count,
        reverse=True,
    )
    daily = Counter(r["created_at"].date() for r in rows if r.get("created_at"))
    dates = [r["created_at"] for r in rows if r.get("created_at")]
    totals = InsightsTotals(
        turns=n,
        first_at=min(dates) if dates else None,
        last_at=max(dates) if dates else None,
        answer_tokens_mean=_mean(answer_tokens),
        answer_tokens_p50=_median(answer_tokens),
        answer_chars_mean=_mean([r["answer_chars"] for r in rows if r["answer_chars"]]),
        latency_ms_p50=_median([r["latency_ms"] for r in rows if r["latency_ms"]]),
        cost_usd_total=round(sum(float(r["cost_usd"] or 0) for r in rows), 4),
        no_context_rate=round(sum(1 for r in rows if r["no_context"]) / n, 4) if n else None,
        by_agent=dict(Counter(r["answered_by"] or "none" for r in rows)),
        by_origin=dict(Counter(r["origin"] for r in rows)),
    )

    def phrases(k: int, limit: int, min_count: int) -> list[PhraseCount]:
        found = frequent_phrases(questions, n=k, top=limit, min_count=min_count)
        return [PhraseCount(text=p, count=c) for p, c in found]

    return InsightsResponse(
        totals=totals,
        terms=phrases(1, 25, 1),
        bigrams=phrases(2, top, 2),
        trigrams=phrases(3, top, 2),
        questions=_questions(rows, top),
        topics=topics,
        documents=_documents(rows, top),
        answer_tokens_hist=_histogram(answer_tokens),
        daily=[DayCount(day=d, count=c) for d, c in sorted(daily.items())],
    )
