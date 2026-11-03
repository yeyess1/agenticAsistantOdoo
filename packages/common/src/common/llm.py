"""Chat model factory, one model per role (A-08, D-03), for the provider in `LLM_PROVIDER`."""

from __future__ import annotations

from typing import Literal

from langchain_core.language_models import BaseChatModel

from common.settings import Settings, get_settings

Role = Literal[
    "contextualizer", "router", "grader", "rewriter", "direct", "generator", "research", "judge"
]

MAX_RETRIES = 2
TIMEOUT_S = 60.0
MAX_TOKENS = 4096


def model_name_for(role: Role, settings: Settings) -> str:
    return str(getattr(settings, f"llm_model_{role}"))


def effort_for(role: Role, settings: Settings) -> str | None:
    """Router and grader get a reasoning effort (D-03); the other roles use the default."""
    return {"router": settings.llm_effort_router, "grader": settings.llm_effort_grader}.get(role)


def get_chat_model(role: Role, settings: Settings | None = None) -> BaseChatModel:
    """Build the chat model of a role. The model id comes from `LLM_MODEL_<ROLE>`.

    Structured outputs must use `method="json_schema"`: Sonnet 5.5 rejects a forced
    `tool_choice` (V-k); Gemini supports it natively.
    """
    s = settings or get_settings()
    if s.llm_provider == "google":
        return _google_model(role, s)
    return _anthropic_model(role, s)


def _anthropic_model(role: Role, s: Settings) -> BaseChatModel:
    """Effort is sent as `output_config.effort` (V-k). An organization-level key needs
    `ANTHROPIC_WORKSPACE_ID`, sent as the `anthropic-workspace-id` header."""
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=model_name_for(role, s),
        api_key=s.anthropic_api_key,
        max_retries=MAX_RETRIES,
        timeout=TIMEOUT_S,
        max_tokens=MAX_TOKENS,
        effort=effort_for(role, s),
        default_headers=workspace_headers(s),
    )


def _google_model(role: Role, s: Settings) -> BaseChatModel:
    """Gemini API (AI Studio key in `GOOGLE_API_KEY`); effort maps to `reasoning_effort`."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=model_name_for(role, s),
        google_api_key=s.google_api_key,
        max_retries=MAX_RETRIES,
        timeout=TIMEOUT_S,
        max_output_tokens=MAX_TOKENS,
        reasoning_effort=effort_for(role, s),
    )


def workspace_headers(settings: Settings) -> dict[str, str]:
    ws = settings.anthropic_workspace_id.strip()
    return {"anthropic-workspace-id": ws} if ws else {}
