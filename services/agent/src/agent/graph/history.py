"""History trimming for LLM calls (D-08, `HISTORY_MAX_TURNS` / `HISTORY_MAX_TOKENS`)."""

from __future__ import annotations

from collections.abc import Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from agent.graph.runtime import msg_text


def approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def trim_history(
    messages: Sequence[BaseMessage], max_turns: int, max_tokens: int
) -> list[BaseMessage]:
    """Keep the last `max_turns` turns (human + assistant) within ~`max_tokens`.

    The persisted state keeps everything; only what is sent to the LLM is trimmed.
    """
    kept: list[BaseMessage] = [
        m for m in messages if isinstance(m, HumanMessage | AIMessage) and msg_text(m).strip()
    ]
    kept = kept[-(max_turns * 2) :]
    while kept and sum(approx_tokens(msg_text(m)) for m in kept) > max_tokens:
        kept.pop(0)
    while kept and not isinstance(kept[0], HumanMessage):
        kept.pop(0)
    return kept
