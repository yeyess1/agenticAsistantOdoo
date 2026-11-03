"""State reducers (D-02). Lists accumulate within a turn and are reset at the next one.

The checkpointer persists the state across turns of a thread, so per-turn lists
(`steps`, `sources`...) need an explicit RESET: `contextualize` returns `Reset([])`.
Keyed reducers also make the docs subgraph safe: a subgraph that shares a key receives
the parent's list and returns it extended, and the keyed merge drops the duplicates.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Reset:
    """Return it from a node to replace (not extend) a list channel."""

    items: list[Any] = field(default_factory=list)


def make_list_reducer(
    key: Callable[[Any], Any] | None = None, *, newer_wins: bool = False
) -> Callable[[list[Any] | None, list[Any] | Reset], list[Any]]:
    """Build a list reducer with RESET; `key` de-duplicates, `newer_wins` updates in place."""

    def reducer(old: list[Any] | None, new: list[Any] | Reset) -> list[Any]:
        if isinstance(new, Reset):
            return list(new.items)
        merged = list(old or [])
        if key is None:
            return merged + list(new)
        index = {key(item): i for i, item in enumerate(merged)}
        for item in new:
            k = key(item)
            if k not in index:
                index[k] = len(merged)
                merged.append(item)
            elif newer_wins:
                merged[index[k]] = item
        return merged

    return reducer


add_or_reset = make_list_reducer()
steps_reducer = make_list_reducer(key=lambda s: s["id"])
sources_reducer = make_list_reducer(key=lambda s: (s["kind"], s["n"]), newer_wins=True)
external_reducer = make_list_reducer(key=lambda s: s["url"], newer_wins=True)
