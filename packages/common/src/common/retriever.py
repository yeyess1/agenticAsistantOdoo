"""Retriever interface and dense implementation (A-08, D-05, D-13)."""

from __future__ import annotations

from typing import Any, Protocol

from qdrant_client import AsyncQdrantClient, models

from common.embedder import Embedder
from common.qdrant_repo import DENSE_VECTOR
from common.schemas.chunk import RetrievalFilters, ScoredChunk

__all__ = ["DenseRetriever", "RetrievalFilters", "Retriever", "ScoredChunk", "build_filter"]


class Retriever(Protocol):
    async def retrieve(
        self, query: str, filters: RetrievalFilters | None = None, k: int = 10
    ) -> list[ScoredChunk]: ...


def build_filter(filters: RetrievalFilters | None) -> models.Filter | None:
    """Translate `RetrievalFilters` into a Qdrant filter over the payload indexes."""
    if filters is None:
        return None
    must: list[models.Condition] = []
    if filters.doc_ids:
        must.append(
            models.FieldCondition(
                key="doc_id", match=models.MatchAny(any=[str(d) for d in filters.doc_ids])
            )
        )
    if filters.sources:
        must.append(models.FieldCondition(key="source", match=models.MatchAny(any=filters.sources)))
    return models.Filter(must=must) if must else None


def to_scored_chunk(point: models.ScoredPoint) -> ScoredChunk:
    p: dict[str, Any] = point.payload or {}
    return ScoredChunk(
        chunk_id=str(point.id),
        doc_id=str(p.get("doc_id", "")),
        score=point.score,
        text=str(p.get("text", "")),
        title=str(p.get("title", "")),
        section=p.get("section"),
        url=str(p.get("url", p.get("source", ""))),
        anchor=p.get("anchor"),
        page=p.get("page"),
    )


class DenseRetriever:
    """Dense search on the `dense` named vector, with metadata filters."""

    def __init__(
        self,
        client: AsyncQdrantClient,
        embedder: Embedder,
        collection: str,
        *,
        hnsw_ef: int = 128,
        exact: bool = False,
        with_instruction: bool = True,
    ) -> None:
        self._client = client
        self._embedder = embedder
        self._collection = collection
        self._hnsw_ef = hnsw_ef
        self._exact = exact
        self._with_instruction = with_instruction

    async def retrieve(
        self, query: str, filters: RetrievalFilters | None = None, k: int = 10
    ) -> list[ScoredChunk]:
        vector = await self._embedder.embed_query(query, with_instruction=self._with_instruction)
        res = await self._client.query_points(
            self._collection,
            query=vector,
            using=DENSE_VECTOR,
            query_filter=build_filter(filters),
            limit=k,
            with_payload=True,
            search_params=models.SearchParams(hnsw_ef=self._hnsw_ef, exact=self._exact),
        )
        return [to_scored_chunk(p) for p in res.points]
