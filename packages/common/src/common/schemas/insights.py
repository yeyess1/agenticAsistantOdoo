"""`GET /insights` schemas: basic NLP over the logged questions (query_log)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

_OUT = ConfigDict(json_schema_serialization_defaults_required=True)


class PhraseCount(BaseModel):
    model_config = _OUT

    text: str
    count: int


class TopicStat(BaseModel):
    model_config = _OUT

    topic: str
    label: str
    count: int
    share: float
    answer_tokens_mean: float | None = None


class DocumentStat(BaseModel):
    model_config = _OUT

    title: str
    url: str
    topic: str | None = None
    retrieved: int
    cited: int


class QuestionCount(BaseModel):
    model_config = _OUT

    question: str
    count: int
    topic: str


class DayCount(BaseModel):
    model_config = _OUT

    day: date
    count: int


class TokenBin(BaseModel):
    model_config = _OUT

    lo: int
    hi: int
    count: int


class InsightsTotals(BaseModel):
    model_config = _OUT

    turns: int
    first_at: datetime | None = None
    last_at: datetime | None = None
    answer_tokens_mean: float | None = None
    answer_tokens_p50: float | None = None
    answer_chars_mean: float | None = None
    latency_ms_p50: float | None = None
    cost_usd_total: float = 0.0
    no_context_rate: float | None = None
    by_agent: dict[str, int]
    by_origin: dict[str, int]


class InsightsResponse(BaseModel):
    model_config = _OUT

    totals: InsightsTotals
    terms: list[PhraseCount]
    bigrams: list[PhraseCount]
    trigrams: list[PhraseCount]
    questions: list[QuestionCount]
    topics: list[TopicStat]
    documents: list[DocumentStat]
    answer_tokens_hist: list[TokenBin]
    daily: list[DayCount]
