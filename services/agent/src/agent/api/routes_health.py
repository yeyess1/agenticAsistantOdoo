"""Health check (A-05): reports dependency reachability."""

from __future__ import annotations

import httpx
import psycopg
from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    state = request.app.state
    settings = state.settings
    deps: dict[str, bool] = {}
    try:
        await state.qdrant.collection_exists(settings.qdrant_collection)
        deps["qdrant"] = True
    except Exception:
        deps["qdrant"] = False
    try:
        async with await psycopg.AsyncConnection.connect(
            settings.resolved_database_url, connect_timeout=3
        ) as conn:
            await conn.execute("SELECT 1")
        deps["postgres"] = True
    except Exception:
        deps["postgres"] = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            deps["embeddings"] = (await client.get(f"{settings.embeddings_url}/health")).is_success
    except Exception:
        deps["embeddings"] = False
    return {"status": "ok" if all(deps.values()) else "degraded", "deps": deps}
