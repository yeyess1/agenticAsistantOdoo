"""Ingestion service (FastAPI): ARCHITECTURE §5.2."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from common.documents_repo import DocumentsRepo
from common.embedder import TEIEmbedder
from common.settings import get_settings
from fastapi import FastAPI
from qdrant_client import AsyncQdrantClient

from ingestion.api import routes_documents, routes_health
from ingestion.chunking.tokenizer import load_token_counter
from ingestion.pipeline import IngestionPipeline

log = logging.getLogger("ingestion")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(name)s %(message)s")
    embedder = TEIEmbedder.from_settings(settings)
    qdrant = AsyncQdrantClient(url=settings.qdrant_url)
    repo = DocumentsRepo(settings.resolved_database_url)
    counter = await asyncio.to_thread(
        load_token_counter,
        settings.embeddings_model,
        settings.tokenizer_cache_dir,
    )
    app.state.settings = settings
    app.state.embedder = embedder
    app.state.qdrant = qdrant
    app.state.repo = repo
    app.state.pipeline = IngestionPipeline(settings, embedder, qdrant, repo, counter)
    try:
        yield
    finally:
        await embedder.aclose()
        await qdrant.close()


app = FastAPI(
    title="Odoo RAG - ingestion",
    version="0.1.0",
    description="Upload, list and delete documents (PDF, TXT, MD) in the vector index.",
    lifespan=lifespan,
)
app.include_router(routes_documents.router)
app.include_router(routes_health.router)
