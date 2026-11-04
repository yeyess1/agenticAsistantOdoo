"""Agent service (FastAPI): ARCHITECTURE §5.1.

`/query` (REST, aggregated events), `/query/stream` (SSE), `/query/resume` (HITL),
`/search` (pure retrieval, A-07), `/insights` (NLP over query_log) and `/health`.
Swagger at `/docs`.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from common.embedder import TEIEmbedder
from common.settings import get_settings
from fastapi import FastAPI
from qdrant_client import AsyncQdrantClient

from agent.api import routes_health, routes_insights, routes_query, routes_search
from agent.factory import build_deps
from agent.graph.checkpointer import postgres_checkpointer
from agent.graph.supervisor import build_graph
from agent.insights.repo import QueryLogRepo
from agent.linear import build_linear_graph


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(name)s %(message)s")
    async with AsyncExitStack() as stack:
        embedder = TEIEmbedder.from_settings(settings)
        stack.push_async_callback(embedder.aclose)
        qdrant = AsyncQdrantClient(url=settings.qdrant_url)
        stack.push_async_callback(qdrant.close)
        saver = await stack.enter_async_context(postgres_checkpointer(settings))  # D-08
        deps = build_deps(settings, qdrant, embedder)
        app.state.settings = settings
        app.state.embedder = embedder
        app.state.qdrant = qdrant
        app.state.graph = build_graph(deps, saver)
        app.state.linear_graph = build_linear_graph(deps)
        app.state.query_log = QueryLogRepo(settings.resolved_database_url)
        yield


def create_app(*, with_lifespan: bool = True) -> FastAPI:
    """Tests build the app without the lifespan and inject fakes into `app.state`."""
    app = FastAPI(
        title="Odoo RAG - agent",
        version="0.3.0",
        description=(
            "Agentic RAG over the curated Odoo 19 developer documentation: supervisor + docs "
            "agent + research agent (LangGraph), memory per `thread_id`, linear baseline."
        ),
        lifespan=lifespan if with_lifespan else None,
    )
    app.include_router(routes_query.router)
    app.include_router(routes_search.router)
    app.include_router(routes_insights.router)
    app.include_router(routes_health.router)
    return app


app = create_app()
