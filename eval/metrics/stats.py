"""Small aggregation helpers (mean / percentiles ignoring missing values)."""

from __future__ import annotations

import math
from collections.abc import Iterable


def present(values: Iterable[float | int | None]) -> list[float]:
    return [float(v) for v in values if v is not None]


def mean(values: Iterable[float | int | None]) -> float | None:
    vals = present(values)
    return sum(vals) / len(vals) if vals else None


def percentile(values: Iterable[float | int | None], p: float) -> float | None:
    """Nearest-rank percentile (p in 0..100)."""
    vals = sorted(present(values))
    if not vals:
        return None
    if not 0 <= p <= 100:
        raise ValueError("p must be in 0..100")
    rank = max(1, math.ceil(p / 100 * len(vals)))
    return vals[rank - 1]


def summary(values: Iterable[float | int | None]) -> dict[str, float | int | None]:
    vals = present(values)
    return {
        "n": len(vals),
        "mean": mean(vals),
        "p50": percentile(vals, 50),
        "p95": percentile(vals, 95),
    }


def rnd(value: float | None, digits: int = 4) -> float | None:
    return None if value is None else round(value, digits)
