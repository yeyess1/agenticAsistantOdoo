"""Postgres access for the `documents` registry (V-05, I-06). One short connection per call."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from common.schemas.documents import DocumentOut

_COLUMNS = (
    "doc_id, name, source, mime_type, content_hash, embedding_model, n_chunks, status, "
    "error, created_at, updated_at, ingested_at"
)


class DocumentsRepo:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connect(self) -> Any:
        return psycopg.AsyncConnection.connect(self._dsn, autocommit=True, row_factory=dict_row)

    async def ping(self) -> bool:
        async with await self._connect() as conn:
            await conn.execute("SELECT 1")
        return True

    async def get(self, doc_id: UUID) -> DocumentOut | None:
        async with await self._connect() as conn:
            cur = await conn.execute(
                f"SELECT {_COLUMNS} FROM documents WHERE doc_id = %s", (doc_id,)
            )
            row = await cur.fetchone()
        return DocumentOut(**row) if row else None

    async def list(
        self, *, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> tuple[list[DocumentOut], int]:
        where = "WHERE status = %s" if status else ""
        params: tuple[Any, ...] = (status,) if status else ()
        async with await self._connect() as conn:
            cur = await conn.execute(f"SELECT count(*) AS n FROM documents {where}", params)
            total_row = await cur.fetchone()
            cur = await conn.execute(
                f"SELECT {_COLUMNS} FROM documents {where} ORDER BY name LIMIT %s OFFSET %s",
                (*params, limit, offset),
            )
            rows = await cur.fetchall()
        return [DocumentOut(**r) for r in rows], int(total_row["n"]) if total_row else 0

    async def mark_processing(
        self,
        *,
        doc_id: UUID,
        name: str,
        source: str,
        mime_type: str,
        content_hash: str,
        embedding_model: str,
    ) -> None:
        """Insert the row, or reset it to `processing` when the document is re-ingested."""
        async with await self._connect() as conn:
            await conn.execute(
                """
                INSERT INTO documents
                  (doc_id, name, source, mime_type, content_hash, embedding_model, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'processing')
                ON CONFLICT (doc_id) DO UPDATE SET
                  name = EXCLUDED.name, mime_type = EXCLUDED.mime_type,
                  content_hash = EXCLUDED.content_hash,
                  embedding_model = EXCLUDED.embedding_model,
                  status = 'processing', error = NULL, updated_at = now()
                """,
                (doc_id, name, source, mime_type, content_hash, embedding_model),
            )

    async def mark_indexed(self, doc_id: UUID, n_chunks: int) -> bool:
        """False when the row no longer exists (the document was deleted mid-ingestion)."""
        async with await self._connect() as conn:
            cur = await conn.execute(
                """
                UPDATE documents SET status = 'indexed', n_chunks = %s, error = NULL,
                  ingested_at = now(), updated_at = now() WHERE doc_id = %s
                """,
                (n_chunks, doc_id),
            )
            return bool(cur.rowcount > 0)

    async def mark_failed(self, doc_id: UUID, error: str) -> None:
        async with await self._connect() as conn:
            await conn.execute(
                "UPDATE documents SET status = 'failed', error = %s, updated_at = now() "
                "WHERE doc_id = %s",
                (error[:2000], doc_id),
            )

    async def delete(self, doc_id: UUID) -> bool:
        async with await self._connect() as conn:
            cur = await conn.execute("DELETE FROM documents WHERE doc_id = %s", (doc_id,))
            return bool(cur.rowcount > 0)
