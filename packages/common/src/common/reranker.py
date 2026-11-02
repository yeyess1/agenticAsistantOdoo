"""Reranker interface (A-08). `NoopReranker` is the default (`RERANKER=none`)."""

from __future__ import annotations

from typing import Protocol

from common.schemas.chunk import ScoredChunk


class Reranker(Protocol):
    async def rerank(self, query: str, chunks: list[ScoredChunk]) -> list[ScoredChunk]: ...


class NoopReranker:
    async def rerank(self, query: str, chunks: list[ScoredChunk]) -> list[ScoredChunk]:
        return chunks
