"""Answer correctness (E-10, D-12) and expected-behaviour check.

Correctness: the judge splits the answer and the expected answer into atomic claims:
TP = answer claims supported by the expected answer, FP = answer claims not supported
by it (extra or wrong), FN = expected claims missing from the answer.
F1 = 2·TP / (2·TP + FP + FN).

Behaviour (not_covered / out_of_scope): their `expected_answer` describes what the
system must do (delegate to the forum, decline politely), so a pass/fail verdict is
used instead of a claim F1.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from metrics.judge import Judge


class CorrectnessVerdict(BaseModel):
    tp: list[str] = Field(description="Answer claims supported by the expected answer.")
    fp: list[str] = Field(description="Answer claims not supported by the expected answer.")
    fn: list[str] = Field(description="Expected-answer claims missing from the answer.")


class BehaviourVerdict(BaseModel):
    passed: bool = Field(description="True if the answer meets the expected behaviour.")
    reason: str = Field(description="One sentence, in English.")


def claim_f1(tp: int, fp: int, fn: int) -> float | None:
    denom = 2 * tp + fp + fn
    if denom == 0:
        return None
    return 2 * tp / denom


def correctness_scores(v: CorrectnessVerdict) -> dict[str, float | int | None]:
    tp, fp, fn = len(v.tp), len(v.fp), len(v.fn)
    return {
        "f1": claim_f1(tp, fp, fn),
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


async def judge_correctness(
    judge: Judge, question: str, answer: str, expected: str
) -> tuple[dict[str, float | int | None], CorrectnessVerdict]:
    user = (
        f"<question>\n{question}\n</question>\n\n"
        f"<expected_answer>\n{expected}\n</expected_answer>\n\n<answer>\n{answer}\n</answer>"
    )
    verdict = await judge.ask("correctness", CorrectnessVerdict, user)
    return correctness_scores(verdict), verdict


async def judge_behaviour(
    judge: Judge, question: str, answer: str, expected: str, facts: str
) -> BehaviourVerdict:
    user = (
        f"<question>\n{question}\n</question>\n\n"
        f"<expected_behaviour>\n{expected}\n</expected_behaviour>\n\n"
        f"<run_facts>\n{facts}\n</run_facts>\n\n<answer>\n{answer}\n</answer>"
    )
    return await judge.ask("behaviour", BehaviourVerdict, user)
