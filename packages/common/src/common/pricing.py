"""Per-model pricing in USD per million tokens (D-03).

Gemini: paid tier, standard (non-batch), prompts <= 200k tokens, output includes thinking
tokens; source https://aistudio.google.com/docs/pricing (checked 2026-11-03). The free tier
costs 0, so these values are what the same traffic would cost on the paid tier.
gemini-3.8-flash doubles from 2027-01-01 (input 1.50, output 7.50): update it then.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelPrice:
    input_per_mtok: float
    output_per_mtok: float


PRICES: dict[str, ModelPrice] = {
    "claude-haiku-5-5": ModelPrice(0.10, 0.50),
    "claude-sonnet-5-5": ModelPrice(2.0, 10.0),
    "claude-opus-5-5": ModelPrice(4.0, 20.0),
    "gemini-3.5-flash-lite": ModelPrice(0.30, 2.50),
    "gemini-3.8-flash": ModelPrice(0.75, 3.75),
    "gemini-3.1-pro-preview": ModelPrice(2.0, 12.0),
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Cost of a call; unknown models cost 0.0 (never raises)."""
    price = PRICES.get(model)
    if price is None:
        return 0.0
    return (input_tokens * price.input_per_mtok + output_tokens * price.output_per_mtok) / 1e6
