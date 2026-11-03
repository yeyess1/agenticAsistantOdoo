"""Answer relevancy (E-03, D-12): mean cos(question, generated question_i), i = 1..N.

The judge writes N questions the answer would answer; the original and the generated
questions are embedded with Qwen3 (TEI, symmetric: no query instruction). Measures
pertinence, not correctness.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from common.embedder import Embedder
from pydantic import BaseModel, Field

from metrics.judge import Judge

N_QUESTIONS = 3


class RelevancyVerdict(BaseModel):
    questions: list[str] = Field(description="Questions (Spanish) that the answer answers.")
    noncommittal: bool = Field(
        description="True if the answer is evasive or declines to answer the question."
    )


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def relevancy_score(original: Sequence[float], generated: Sequence[Sequence[float]]) -> float:
    if not generated:
        return 0.0
    return sum(cosine(original, g) for g in generated) / len(generated)


async def judge_relevancy(
    judge: Judge, embedder: Embedder, question: str, answer: str
) -> tuple[float, RelevancyVerdict]:
    user = f"N = {N_QUESTIONS}\n\n<answer>\n{answer}\n</answer>"
    verdict = await judge.ask("relevancy", RelevancyVerdict, user)
    generated = [q for q in verdict.questions if q.strip()][:N_QUESTIONS]
    vectors = await embedder.embed_documents([question, *generated])
    return relevancy_score(vectors[0], vectors[1:]), verdict
