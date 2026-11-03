"""Token counting with the Qwen3 tokenizer (D-06, D-04). `tokenizers` only, no torch."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

import httpx
from tokenizers import Tokenizer

log = logging.getLogger(__name__)

TOKENIZER_URL = "https://huggingface.co/{model}/resolve/main/tokenizer.json"


class TokenCounter(Protocol):
    def count(self, text: str) -> int: ...


class HFTokenCounter:
    def __init__(self, tokenizer: Tokenizer) -> None:
        self._tok = tokenizer

    @classmethod
    def from_file(cls, path: Path) -> HFTokenCounter:
        return cls(Tokenizer.from_file(str(path)))

    def count(self, text: str) -> int:
        return len(self._tok.encode(text, add_special_tokens=False).ids)


class CharTokenCounter:
    """Deterministic fallback for tests: roughly 1 token per 4 characters."""

    def count(self, text: str) -> int:
        return (len(text) + 3) // 4


def load_token_counter(
    model: str, cache_dir: str | Path, *, client: httpx.Client | None = None
) -> HFTokenCounter:
    """Load `tokenizer.json` for `model`, downloading it once into `cache_dir`."""
    path = Path(cache_dir).expanduser() / model.replace("/", "--") / "tokenizer.json"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        log.info("downloading tokenizer for %s", model)
        http = client or httpx.Client(follow_redirects=True, timeout=60.0)
        try:
            resp = http.get(TOKENIZER_URL.format(model=model))
            resp.raise_for_status()
        finally:
            if client is None:
                http.close()
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(resp.content)
        tmp.replace(path)
    return HFTokenCounter.from_file(path)
