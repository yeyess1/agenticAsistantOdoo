"""Health check (A-05): reports dependency reachability."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    state = request.app.state
    deps: dict[str, bool] = {}
    try:
        await state.qdrant.collection_exists(state.settings.qdrant_collection)
        deps["qdrant"] = True
    except Exception:
        deps["qdrant"] = False
    try:
        deps["postgres"] = await state.repo.ping()
    except Exception:
        deps["postgres"] = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            deps["embeddings"] = (
                await client.get(f"{state.settings.embeddings_url}/health")
            ).is_success
    except Exception:
        deps["embeddings"] = False
    return {"status": "ok" if all(deps.values()) else "degraded", "deps": deps}
