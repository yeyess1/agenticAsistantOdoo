"""Chat model factory, one model per role (A-08, D-03)."""

from __future__ import annotations

from typing import Literal

from langchain_anthropic import ChatAnthropic

from common.settings import Settings, get_settings

Role = Literal[
    "contextualizer", "router", "grader", "rewriter", "direct", "generator", "research", "judge"
]


def model_name_for(role: Role, settings: Settings) -> str:
    return str(getattr(settings, f"llm_model_{role}"))


def get_chat_model(role: Role, settings: Settings | None = None) -> ChatAnthropic:
    """Build the chat model of a role. The model id comes from `LLM_MODEL_<ROLE>`.

    The `effort` parameter for router/grader (D-03, V-k) is wired in Phase 2 after the
    early check against `langchain-anthropic`.
    """
    s = settings or get_settings()
    return ChatAnthropic(
        model=model_name_for(role, s),
        api_key=s.anthropic_api_key,
        max_retries=2,
        timeout=60.0,
    )
