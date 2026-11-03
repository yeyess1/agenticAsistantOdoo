"""Golden set loader and validation (E-01, D-12; schema in ARCHITECTURE §12).

Relevant sections are written as:
- web pages: `<page url>#<anchor>` (H1-H4 anchors, matched exactly on url + anchor);
- the coding guidelines PDF: `coding_guidelines.pdf#page=N`, matched on (url, page).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Literal

import yaml
from metrics.retrieval import SectionKey, parse_section_ref
from pydantic import BaseModel, Field, field_validator, model_validator

Category = Literal["covered", "not_covered", "out_of_scope", "follow_up"]
Agent = Literal["docs", "research", "direct"]

DEFAULT_GOLDEN = Path(__file__).resolve().parent.parent / "golden" / "golden_set.yaml"

# Category -> agent that must answer (ARCHITECTURE §12).
EXPECTED_AGENT: dict[str, Agent] = {
    "covered": "docs",
    "follow_up": "docs",
    "not_covered": "research",
    "out_of_scope": "direct",
}


class GoldenItem(BaseModel):
    id: str = Field(pattern=r"^q\d{2,3}$")
    category: Category
    question: str = Field(min_length=1)
    question_en: str = Field(min_length=1)
    expected_answer: str = Field(min_length=1)
    relevant_sections: list[str] = Field(default_factory=list)
    expected_agent: Agent
    expects_rewrite: bool = False
    thread: str | None = None
    turn: int | None = Field(default=None, ge=1)
    notes: str = ""

    @field_validator("relevant_sections")
    @classmethod
    def _parse_refs(cls, refs: list[str]) -> list[str]:
        for ref in refs:
            parse_section_ref(ref)  # raises ValueError on malformed refs
        if len(set(refs)) != len(refs):
            raise ValueError("duplicated relevant_sections")
        return refs

    @model_validator(mode="after")
    def _consistent(self) -> GoldenItem:
        if self.expected_agent != EXPECTED_AGENT[self.category]:
            raise ValueError(
                f"{self.id}: expected_agent {self.expected_agent!r} does not match "
                f"category {self.category!r}"
            )
        needs_sections = self.category in ("covered", "follow_up")
        if needs_sections != bool(self.relevant_sections):
            raise ValueError(f"{self.id}: relevant_sections required only for docs items")
        is_follow = self.category == "follow_up"
        if is_follow != (self.thread is not None and self.turn is not None):
            raise ValueError(f"{self.id}: thread/turn are required only on follow_up items")
        return self

    @property
    def section_keys(self) -> set[SectionKey]:
        return {parse_section_ref(r) for r in self.relevant_sections}

    @property
    def is_follow_up_turn(self) -> bool:
        """Turn >= 2: unanswerable without the previous turns of its thread."""
        return (self.turn or 1) > 1


class GoldenSet(BaseModel):
    items: list[GoldenItem]

    @model_validator(mode="after")
    def _unique_and_threads(self) -> GoldenSet:
        ids = Counter(i.id for i in self.items)
        dup = [k for k, n in ids.items() if n > 1]
        if dup:
            raise ValueError(f"duplicated ids: {dup}")
        for thread, turns in self.threads().items():
            numbers = [i.turn for i in turns]
            if numbers != list(range(1, len(turns) + 1)):
                raise ValueError(f"thread {thread!r}: turns must be 1..n, got {numbers}")
        return self

    def threads(self) -> dict[str, list[GoldenItem]]:
        """Follow-up items grouped by thread, sorted by turn."""
        out: dict[str, list[GoldenItem]] = {}
        for item in self.items:
            if item.thread is not None:
                out.setdefault(item.thread, []).append(item)
        return {k: sorted(v, key=lambda i: i.turn or 0) for k, v in out.items()}

    def by_id(self) -> dict[str, GoldenItem]:
        return {i.id: i for i in self.items}

    def counts(self) -> dict[str, int]:
        return dict(Counter(i.category for i in self.items))


def load_golden(path: Path = DEFAULT_GOLDEN) -> GoldenSet:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return GoldenSet.model_validate(data)
