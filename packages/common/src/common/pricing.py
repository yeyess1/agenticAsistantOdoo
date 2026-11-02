"""Per-model pricing in USD per million tokens (D-03)."""

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
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Cost of a call; unknown models cost 0.0 (never raises)."""
    price = PRICES.get(model)
    if price is None:
        return 0.0
    return (input_tokens * price.input_per_mtok + output_tokens * price.output_per_mtok) / 1e6
