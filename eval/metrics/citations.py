"""Citation correctness (D-12): cited sections that belong to the relevant sections."""

from __future__ import annotations

from collections.abc import Sequence

from metrics.retrieval import SectionKey


def citation_correctness(cited: Sequence[SectionKey], relevant: set[SectionKey]) -> float | None:
    """Cited sources whose section is relevant / cited sources. None without citations."""
    if not cited:
        return None
    return sum(k in relevant for k in cited) / len(cited)
