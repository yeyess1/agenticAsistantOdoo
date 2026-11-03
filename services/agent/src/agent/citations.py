"""Citation helpers: numbered sources and `[n]` post-processing (R-04, ARCHITECTURE §6.3)."""

from __future__ import annotations

import re

from common.schemas.chunk import ScoredChunk

from agent.graph.state import Source

_MARKER = re.compile(r"\[(\d{1,3})\]")


def source_url(chunk: ScoredChunk) -> str:
    """Web chunks link to the exact section (`url#anchor`); PDF chunks keep file + page."""
    if chunk.anchor and "#" not in chunk.url:
        return f"{chunk.url}{chunk.anchor if chunk.anchor.startswith('#') else '#' + chunk.anchor}"
    return chunk.url


def build_doc_sources(chunks: list[ScoredChunk]) -> list[Source]:
    return [
        {
            "n": i,
            "kind": "doc",
            "doc_id": c.doc_id,
            "title": c.title,
            "section": c.section,
            "url": source_url(c),
            "page": c.page,
            "score": c.score,
            "cited": False,
        }
        for i, c in enumerate(chunks, start=1)
    ]


def extract_markers(text: str) -> list[int]:
    """Citation numbers in order of first appearance."""
    seen: list[int] = []
    for m in _MARKER.finditer(text):
        n = int(m.group(1))
        if n not in seen:
            seen.append(n)
    return seen


def mark_cited(sources: list[Source], text: str) -> tuple[list[Source], list[int]]:
    """Set `cited=True` on the sources the text references; also returns invalid markers."""
    used = set(extract_markers(text))
    valid = {s["n"] for s in sources}
    marked: list[Source] = [{**s, "cited": s["n"] in used} for s in sources]
    return marked, sorted(used - valid)
