"""Deterministic retrieval metrics over section keys (D-12, ARCHITECTURE §12).

A chunk is relevant when its section key is in the item's `relevant_sections`:
- web chunks: `(page url, anchor, None)`, anchor without the leading `#`;
- PDF chunks: `(file name, None, page)` (PDF chunks have no anchor).

`hits` is the list of relevance flags of a ranked result list (`v_k` in D-12).
Recall counts distinct relevant sections; precision counts relevant chunks.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

SectionKey = tuple[str, str | None, int | None]

_PAGE_REF = re.compile(r"^(?P<file>[^#]+\.pdf)#page=(?P<page>\d+)$")


def parse_section_ref(ref: str) -> SectionKey:
    """Parse a golden-set reference: `url#anchor` or `file.pdf#page=N`."""
    m = _PAGE_REF.match(ref)
    if m:
        return (m["file"], None, int(m["page"]))
    url, sep, anchor = ref.partition("#")
    if not sep or not url or not anchor:
        raise ValueError(f"malformed section ref {ref!r}: expected url#anchor or file.pdf#page=N")
    return (url, anchor, None)


def chunk_key(url: str, anchor: str | None = None, page: int | None = None) -> SectionKey:
    """Section key of a retrieved chunk or an answer source (`url` may carry `#anchor`)."""
    base, _, frag = url.partition("#")
    if page is not None and base.lower().endswith(".pdf"):
        return (base.rsplit("/", 1)[-1], None, page)
    anchor = (anchor or frag or "").lstrip("#") or None
    return (base, anchor, None)


def relevance_flags(keys: Sequence[SectionKey], relevant: set[SectionKey]) -> list[bool]:
    return [k in relevant for k in keys]


def recall_at_k(keys: Sequence[SectionKey], relevant: set[SectionKey], k: int) -> float | None:
    """Distinct relevant sections found in the top k / total relevant sections."""
    if not relevant:
        return None
    return len(set(keys[:k]) & relevant) / len(relevant)


def precision_at_k(hits: Sequence[bool], k: int) -> float:
    """Relevant chunks in the top k / k (a short list still divides by k)."""
    if k <= 0:
        raise ValueError("k must be positive")
    return sum(hits[:k]) / k


def reciprocal_rank(hits: Sequence[bool]) -> float:
    """1 / rank of the first relevant chunk; 0 when none is relevant."""
    for i, hit in enumerate(hits, start=1):
        if hit:
            return 1.0 / i
    return 0.0


def mean_reciprocal_rank(runs: Sequence[Sequence[bool]]) -> float | None:
    if not runs:
        return None
    return sum(reciprocal_rank(h) for h in runs) / len(runs)


def context_precision(hits: Sequence[bool], k: int | None = None) -> float | None:
    """Context precision@K: sum_k(Precision@k * v_k) / relevant chunks in the top K.

    Example from D-12: [1, 0, 1, 0] -> (1 + 2/3) / 2 = 0.83. None for an empty list;
    0.0 when no chunk is relevant.
    """
    top = list(hits[: k or len(hits)])
    if not top:
        return None
    n_rel = sum(top)
    if n_rel == 0:
        return 0.0
    total = 0.0
    found = 0
    for i, hit in enumerate(top, start=1):
        if hit:
            found += 1
            total += found / i
    return total / n_rel


def overlap_at_k(candidate: Sequence[str], reference: Sequence[str], k: int) -> float:
    """|top-k(candidate) ∩ top-k(reference)| / k: recall of ANN results vs exact (V-04)."""
    ref = set(reference[:k])
    if not ref:
        return 1.0
    return len(set(candidate[:k]) & ref) / len(ref)
