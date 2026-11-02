"""Typed schemas for the external research tools (ARCHITECTURE §8, D-07)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class ToolStatus(StrEnum):
    OK = "ok"
    EMPTY = "empty"
    TIMEOUT = "timeout"
    ERROR = "error"


class SearchOdooForumInput(BaseModel):
    query: str = Field(min_length=3, description="Keywords in English: module, model, version.")
    max_results: int = Field(5, ge=1, le=10)


class ForumHit(BaseModel):
    title: str
    url: HttpUrl
    snippet: str


class SearchOdooForumOutput(BaseModel):
    status: ToolStatus
    results: list[ForumHit] = Field(default_factory=list)
    message: str | None = None


class ReadForumPostInput(BaseModel):
    url: HttpUrl


class ForumAnswer(BaseModel):
    body: str
    votes: int | None = None
    accepted: bool = False


class ReadForumPostOutput(BaseModel):
    status: ToolStatus
    url: HttpUrl
    title: str | None = None
    question: str | None = None
    answers: list[ForumAnswer] = Field(default_factory=list)
    message: str | None = None
