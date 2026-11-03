"""LLM judge plumbing (D-12): versioned prompts, structured output, usage and cost.

The judge is `LLM_MODEL_JUDGE` (Opus 5.5 by default), a different model from the
generator (Sonnet 5.5) to avoid self-evaluation bias. Structured output uses
`method="json_schema"` (no forced `tool_choice`, V-k).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from common.pricing import cost_usd
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@cache
def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8").strip()


@dataclass
class JudgeUsage:
    calls: int = 0
    failures: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    by_metric: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "calls": self.calls,
            "failures": self.failures,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 4),
            "cost_by_metric": {k: round(v, 4) for k, v in self.by_metric.items()},
        }


class JudgeError(RuntimeError):
    """The judge call failed or returned an unparsable verdict."""


class Judge:
    """Shared structured-output caller with a concurrency limit and cost accounting."""

    def __init__(
        self, model: BaseChatModel, model_name: str, *, concurrency: int = 4, retries: int = 1
    ) -> None:
        self._model = model
        self.model_name = model_name
        self._sem = asyncio.Semaphore(concurrency)
        self._retries = retries
        self.usage = JudgeUsage()

    async def ask[T: BaseModel](self, metric: str, schema: type[T], user: str) -> T:
        runnable = self._model.with_structured_output(
            schema, method="json_schema", include_raw=True
        )
        messages = [SystemMessage(content=load_prompt(metric)), HumanMessage(content=user)]
        last_error = ""
        for _ in range(self._retries + 1):
            async with self._sem:
                try:
                    out = await runnable.ainvoke(messages)
                except Exception as exc:
                    last_error = f"{type(exc).__name__}: {str(exc)[:200]}"
                    self.usage.failures += 1
                    continue
            self._account(metric, out.get("raw") if isinstance(out, dict) else None)
            parsed = out.get("parsed") if isinstance(out, dict) else out
            if isinstance(parsed, schema):
                return parsed
            last_error = "unparsable structured output"
            self.usage.failures += 1
        raise JudgeError(f"{metric}: {last_error}")

    def _account(self, metric: str, raw: object) -> None:
        usage = getattr(raw, "usage_metadata", None) or {}
        tin = int(usage.get("input_tokens", 0))
        tout = int(usage.get("output_tokens", 0))
        cost = cost_usd(self.model_name, tin, tout)
        self.usage.calls += 1
        self.usage.input_tokens += tin
        self.usage.output_tokens += tout
        self.usage.cost_usd += cost
        self.usage.by_metric[metric] = self.usage.by_metric.get(metric, 0.0) + cost
