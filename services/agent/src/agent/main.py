"""Agent service (FastAPI): ARCHITECTURE §5.1.

Phase 1 exposes `/search` (pure retrieval, A-07) and `/health`. The query graph
(`/query`, `/query/stream`) arrives with Phases 2-3.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from common.embedder import TEIEmbedder
from common.settings import get_settings
from fastapi import FastAPI
from qdrant_client import AsyncQdrantClient

from agent.api import routes_health, routes_search


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(name)s %(message)s")
    embedder = TEIEmbedder.from_settings(settings)
    qdrant = AsyncQdrantClient(url=settings.qdrant_url)
    app.state.settings = settings
    app.state.embedder = embedder
    app.state.qdrant = qdrant
    try:
        yield
    finally:
        await embedder.aclose()
        await qdrant.close()


app = FastAPI(
    title="Odoo RAG - agent",
    version="0.1.0",
    description="Query API over the curated Odoo 19 developer documentation.",
    lifespan=lifespan,
)
app.include_router(routes_search.router)
app.include_router(routes_health.router)
