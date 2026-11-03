"""Faithfulness (E-03, D-12): supported claims / total claims, judged against the context.

Measures hallucination, not correctness: a claim is supported when it can be inferred
from the context that reached the generator (post-grader in agentic mode, all retrieved
chunks in linear mode). The answer is in Spanish and the context in English.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, Field

from metrics.judge import Judge


class ClaimVerdict(BaseModel):
    claim: str = Field(description="One atomic factual claim of the answer, in Spanish.")
    supported: bool = Field(description="True if the claim can be inferred from the context.")


class FaithfulnessVerdict(BaseModel):
    claims: list[ClaimVerdict]


def faithfulness_score(verdict: FaithfulnessVerdict) -> float | None:
    if not verdict.claims:
        return None
    return sum(c.supported for c in verdict.claims) / len(verdict.claims)


def format_context(chunks: Sequence[tuple[int, str, str]]) -> str:
    """`(n, heading, text)` -> numbered excerpts, as the generator saw them."""
    return "\n\n".join(f"[{n}] {heading}\n{text}" for n, heading, text in chunks)


async def judge_faithfulness(
    judge: Judge, question: str, answer: str, context: str
) -> tuple[float | None, FaithfulnessVerdict]:
    user = (
        f"<question>\n{question}\n</question>\n\n"
        f"<context>\n{context}\n</context>\n\n<answer>\n{answer}\n</answer>"
    )
    verdict = await judge.ask("faithfulness", FaithfulnessVerdict, user)
    return faithfulness_score(verdict), verdict
