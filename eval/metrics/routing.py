"""Supervisor routing accuracy + 3x3 confusion matrix with per-class P/R (E-04, D-12)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

LABELS: tuple[str, ...] = ("docs", "research", "direct")
NONE_LABEL = "none"  # the run produced no agent (error / pending interrupt)


def routing_report(
    expected: Sequence[str], predicted: Sequence[str | None], labels: Sequence[str] = LABELS
) -> dict[str, Any]:
    """Accuracy, confusion[expected][predicted] and precision/recall/F1 per class.

    A `None` prediction counts as wrong and lands in a `none` column.
    """
    if len(expected) != len(predicted):
        raise ValueError("expected and predicted must have the same length")
    cols = [*labels, NONE_LABEL]
    confusion = {e: dict.fromkeys(cols, 0) for e in labels}
    for e, p in zip(expected, predicted, strict=True):
        if e not in confusion:
            raise ValueError(f"unknown expected label {e!r}")
        confusion[e][p if p is not None and p in labels else NONE_LABEL] += 1
    n = len(expected)
    correct = sum(confusion[c][c] for c in labels)
    per_class: dict[str, dict[str, float | int | None]] = {}
    for c in labels:
        tp = confusion[c][c]
        predicted_c = sum(confusion[e][c] for e in labels)
        support = sum(confusion[c].values())
        precision = tp / predicted_c if predicted_c else None
        recall = tp / support if support else None
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and precision + recall > 0
            else None
        )
        per_class[c] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        }
    return {
        "n": n,
        "correct": correct,
        "accuracy": correct / n if n else None,
        "labels": list(labels),
        "confusion": confusion,
        "per_class": per_class,
    }
