"""Production wiring of the graph dependencies from settings."""

from __future__ import annotations

from common.embedder import TEIEmbedder
from common.reranker import NoopReranker
from common.retriever import DenseRetriever
from common.search_provider import DdgsProvider, SearchProvider
from common.settings import Settings
from qdrant_client import AsyncQdrantClient

from agent.graph.runtime import GraphDeps
from agent.tools.forum import ForumTools


def build_search_provider(settings: Settings) -> SearchProvider:
    if settings.search_provider != "ddgs":  # SearXNG is plan B (RK-04), not implemented yet
        raise NotImplementedError(f"search provider {settings.search_provider!r}")
    return DdgsProvider(timeout_s=settings.search_timeout_s)


def build_deps(settings: Settings, qdrant: AsyncQdrantClient, embedder: TEIEmbedder) -> GraphDeps:
    retriever = DenseRetriever(
        qdrant, embedder, settings.qdrant_collection, hnsw_ef=settings.qdrant_hnsw_ef
    )
    return GraphDeps(
        settings=settings,
        retriever=retriever,
        forum=ForumTools(build_search_provider(settings), settings),
        reranker=NoopReranker(),
    )
