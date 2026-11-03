"""In-memory TTL cache with a normalised key (D-07: 1 h by default)."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any


class TTLCache:
    def __init__(self, ttl_s: float, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_s
        self._clock = clock
        self._data: dict[str, tuple[float, Any]] = {}

    @staticmethod
    def make_key(tool: str, **args: Any) -> str:
        normalised = {
            k: (" ".join(v.lower().split()) if isinstance(v, str) else v) for k, v in args.items()
        }
        return f"{tool}:{json.dumps(normalised, sort_keys=True, default=str)}"

    def get(self, key: str) -> Any | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        expires, value = entry
        if self._clock() >= expires:
            del self._data[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        if self._ttl > 0:
            self._data[key] = (self._clock() + self._ttl, value)

    def __len__(self) -> int:
        return len(self._data)
