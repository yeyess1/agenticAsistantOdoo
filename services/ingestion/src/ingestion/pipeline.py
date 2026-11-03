"""Ingestion pipeline: parse -> chunk -> embed -> Qdrant upsert -> registry (I-01…I-06, §7)."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from datetime import UTC, datetime
from uuid import UUID

from common.documents_repo import DocumentsRepo
from common.embedder import Embedder
from common.ids import doc_id_for, point_id_for
from common.qdrant_repo import DENSE_VECTOR
from common.schemas.documents import IngestResult
from common.settings import Settings
from qdrant_client import AsyncQdrantClient, models

from ingestion.chunking.chunker import Chunk, chunk_markdown
from ingestion.chunking.tokenizer import TokenCounter
from ingestion.parsers import ParsedDocument, parse_document

log = logging.getLogger(__name__)

UPSERT_BATCH = 64


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def embed_text(title: str, chunk: Chunk) -> str:
    """Text that is vectorized: section path prepended, the displayed text stays clean (D-06)."""
    path = chunk.section or ""
    if path and not path.startswith(title):
        path = f"{title} > {path}"
    header = path or title
    return f"{header}\n\n{chunk.text}"


def build_payload(
    doc: ParsedDocument, doc_id: UUID, chunk: Chunk, *, model: str, vector_text: str, now: str
) -> dict[str, object]:
    is_web = doc.source.startswith(("http://", "https://"))
    anchor = f"#{chunk.anchor}" if chunk.anchor and is_web else None
    return {
        "doc_id": str(doc_id),
        "chunk_index": chunk.index,
        "source": doc.source,
        "title": doc.title,
        "section": chunk.section,
        "anchor": anchor,
        "url": doc.source + (anchor or ""),
        "page": chunk.page,
        "text": chunk.text,
        "n_tokens": chunk.n_tokens,
        "content_hash": sha256(model + vector_text),
        "embedding_model": model,
        "ingested_at": now,
    }


class IngestionPipeline:
    def __init__(
        self,
        settings: Settings,
        embedder: Embedder,
        qdrant: AsyncQdrantClient,
        repo: DocumentsRepo,
        counter: TokenCounter,
    ) -> None:
        self._s = settings
        self._embedder = embedder
        self._qdrant = qdrant
        self._repo = repo
        self._counter = counter

    def chunk(self, doc: ParsedDocument) -> list[Chunk]:
        return chunk_markdown(
            doc.markdown,
            self._counter,
            size=self._s.chunk_size_tokens,
            overlap=self._s.chunk_overlap_tokens,
            min_tokens=self._s.chunk_min_tokens,
            structured=doc.structured,
        )

    async def ingest(
        self,
        data: bytes,
        filename: str,
        *,
        source_url: str | None = None,
        force: bool = False,
    ) -> IngestResult:
        started = time.perf_counter()
        # PDF parsing is CPU-bound: keep the event loop free.
        doc = await asyncio.to_thread(parse_document, data, filename, source_url)
        doc_id = doc_id_for(doc.source)
        content_hash = sha256(doc.markdown)
        model = self._embedder.model

        existing = await self._repo.get(doc_id)
        if (
            existing
            and not force
            and existing.status == "indexed"
            and existing.content_hash == content_hash
            and existing.embedding_model == model
        ):
            return IngestResult(
                doc_id=doc_id,
                name=existing.name,
                source=doc.source,
                status="indexed",
                n_chunks=existing.n_chunks,
                content_hash=content_hash,
                action="unchanged",
                took_ms=_ms(started),
            )

        await self._repo.mark_processing(
            doc_id=doc_id,
            name=filename,
            source=doc.source,
            mime_type=doc.mime_type,
            content_hash=content_hash,
            embedding_model=model,
        )
        try:
            chunks = await asyncio.to_thread(self.chunk, doc)
            if not chunks:
                raise ValueError("document produced no chunks")
            texts = [embed_text(doc.title, c) for c in chunks]
            vectors = await self._embedder.embed_documents(texts)
            now = datetime.now(UTC).isoformat()
            points = [
                models.PointStruct(
                    id=str(point_id_for(doc_id, c.index)),
                    vector={DENSE_VECTOR: vec},
                    payload=build_payload(doc, doc_id, c, model=model, vector_text=t, now=now),
                )
                for c, t, vec in zip(chunks, texts, vectors, strict=True)
            ]
            await self.delete_points(doc_id)
            for i in range(0, len(points), UPSERT_BATCH):
                await self._qdrant.upsert(
                    self._s.qdrant_collection, points=points[i : i + UPSERT_BATCH], wait=True
                )
            await self._repo.mark_indexed(doc_id, len(chunks))
        except Exception as exc:
            log.exception("ingestion failed for %s", doc.source)
            await self._repo.mark_failed(doc_id, f"{type(exc).__name__}: {exc}")
            raise
        return IngestResult(
            doc_id=doc_id,
            name=filename,
            source=doc.source,
            status="indexed",
            n_chunks=len(chunks),
            content_hash=content_hash,
            action="updated" if existing else "created",
            took_ms=_ms(started),
        )

    async def delete_points(self, doc_id: UUID) -> None:
        await self._qdrant.delete(
            self._s.qdrant_collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="doc_id", match=models.MatchValue(value=str(doc_id))
                        )
                    ]
                )
            ),
            wait=True,
        )

    async def delete_document(self, doc_id: UUID) -> bool:
        if await self._repo.get(doc_id) is None:
            return False
        await self.delete_points(doc_id)
        return await self._repo.delete(doc_id)


def _ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
