"""`GET /insights`: basic NLP over the logged questions (frequent phrases, topics, documents)."""

from __future__ import annotations

from typing import Annotated, Literal

from common.schemas.api import ErrorResponse, Mode
from common.schemas.insights import InsightsResponse
from fastapi import APIRouter, HTTPException, Query, Request

from agent.insights.aggregate import aggregate
from agent.insights.repo import QueryLogRepo

router = APIRouter(tags=["insights"])


@router.get(
    "/insights",
    response_model=InsightsResponse,
    summary="Usage insights from query_log: phrases, topics, documents, answer length",
    responses={503: {"model": ErrorResponse, "description": "query_log not available"}},
)
async def insights(
    request: Request,
    origin: Annotated[Literal["ui", "eval"] | None, Query(description="Null: both.")] = None,
    mode: Annotated[Mode | None, Query(description="Null: agentic and linear.")] = None,
    days: Annotated[int | None, Query(ge=1, le=3650, description="Last N days only.")] = None,
    top: Annotated[int, Query(ge=1, le=100)] = 15,
) -> InsightsResponse:
    repo: QueryLogRepo | None = getattr(request.app.state, "query_log", None)
    if repo is None:
        raise HTTPException(
            503, detail={"error": {"code": "insights_unavailable", "message": "no query_log"}}
        )
    rows = await repo.fetch(origin=origin, mode=mode, days=days)
    return aggregate(rows, top=top)
