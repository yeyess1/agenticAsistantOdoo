"""`POST /search`: pure retrieval, no LLM (A-07, D-13). Used by eval (recall@k) and challenge A."""

from __future__ import annotations

import time

import httpx
from common.retriever import DenseRetriever
from common.schemas.api import SearchRequest, SearchResponse
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["search"])


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Retrieve chunks (dense vector search with metadata filters)",
)
async def search(request: Request, body: SearchRequest) -> SearchResponse:
    state = request.app.state
    settings = state.settings
    retriever = DenseRetriever(
        state.qdrant,
        state.embedder,
        settings.qdrant_collection,
        hnsw_ef=body.hnsw_ef or settings.qdrant_hnsw_ef,
        exact=body.exact,
        with_instruction=body.with_instruction,
    )
    started = time.perf_counter()
    try:
        results = await retriever.retrieve(body.query, body.filters, k=body.top_k)
    except httpx.HTTPError as exc:
        raise HTTPException(
            502, detail={"error": {"code": "embeddings_unavailable", "message": str(exc)}}
        ) from exc
    return SearchResponse(results=results, took_ms=int((time.perf_counter() - started) * 1000))
