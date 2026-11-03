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

    Router and grader also get `effort` (D-03, V-k: sent as `output_config.effort`).
    Structured outputs must use `method="json_schema"`: Sonnet 5.5 rejects a forced
    `tool_choice` (V-k).
    """
    s = settings or get_settings()
    effort = {"router": s.llm_effort_router, "grader": s.llm_effort_grader}.get(role)
    return ChatAnthropic(
        model=model_name_for(role, s),
        api_key=s.anthropic_api_key,
        max_retries=2,
        timeout=60.0,
        max_tokens=4096,
        effort=effort,
    )
