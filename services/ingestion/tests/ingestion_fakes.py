"""In-memory fakes for the ingestion tests (no network, no Postgres)."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from common.schemas.documents import DocumentOut


class FakeEmbedder:
    """Deterministic 8-dim vectors derived from the text hash (no network)."""

    model = "fake-model"
    dim = 8

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [self._vec(t) for t in texts]

    async def embed_query(self, query: str, *, with_instruction: bool = True) -> list[float]:
        return self._vec(query)

    @staticmethod
    def _vec(text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [b / 255 + 0.01 for b in digest[:8]]


class FakeRepo:
    """In-memory stand-in for `DocumentsRepo`."""

    def __init__(self) -> None:
        self.rows: dict[UUID, dict[str, Any]] = {}

    async def ping(self) -> bool:
        return True

    def _out(self, row: dict[str, Any]) -> DocumentOut:
        return DocumentOut(**row)

    async def get(self, doc_id: UUID) -> DocumentOut | None:
        row = self.rows.get(doc_id)
        return self._out(row) if row else None

    async def list(
        self, *, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> tuple[list[DocumentOut], int]:
        rows = [r for r in self.rows.values() if status is None or r["status"] == status]
        rows.sort(key=lambda r: r["name"])
        return [self._out(r) for r in rows[offset : offset + limit]], len(rows)

    async def mark_processing(self, **kw: Any) -> None:
        now = datetime.now(UTC)
        old = self.rows.get(kw["doc_id"])
        self.rows[kw["doc_id"]] = {
            **kw,
            "n_chunks": old["n_chunks"] if old else 0,
            "status": "processing",
            "error": None,
            "created_at": old["created_at"] if old else now,
            "updated_at": now,
            "ingested_at": old["ingested_at"] if old else None,
        }

    async def mark_indexed(self, doc_id: UUID, n_chunks: int) -> None:
        self.rows[doc_id].update(
            status="indexed", n_chunks=n_chunks, ingested_at=datetime.now(UTC), error=None
        )

    async def mark_failed(self, doc_id: UUID, error: str) -> None:
        self.rows[doc_id].update(status="failed", error=error)

    async def delete(self, doc_id: UUID) -> bool:
        return self.rows.pop(doc_id, None) is not None
