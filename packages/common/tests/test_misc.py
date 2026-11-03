from pathlib import Path

from common.db.migrate import list_migrations
from common.llm import get_chat_model, model_name_for, workspace_headers
from common.pricing import cost_usd
from common.settings import Settings
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI


def test_migrations_are_ordered_and_present() -> None:
    files = list_migrations()
    assert files[0].name == "001_documents.sql"
    assert files == sorted(files)
    sql = Path(files[0]).read_text()
    assert "CREATE TABLE IF NOT EXISTS documents" in sql
    assert "'processing','indexed','failed'" in sql


def test_cost() -> None:
    assert cost_usd("claude-haiku-5-5", 1_000_000, 1_000_000) == 0.6
    assert cost_usd("unknown", 10, 10) == 0.0
    assert cost_usd("gemini-3.8-flash", 1_000_000, 1_000_000) == 4.5


def test_llm_role_model_comes_from_settings() -> None:
    s = Settings(_env_file=None, llm_model_router="custom-model", anthropic_api_key="k")
    assert model_name_for("router", s) == "custom-model"
    generator = get_chat_model("generator", s)
    assert isinstance(generator, ChatAnthropic)
    assert generator.model == "claude-sonnet-5-5"


def test_workspace_header_only_when_configured() -> None:
    assert workspace_headers(Settings(_env_file=None)) == {}
    s = Settings(_env_file=None, anthropic_workspace_id=" wrkspc_123 ")
    assert workspace_headers(s) == {"anthropic-workspace-id": "wrkspc_123"}
    router = get_chat_model("router", s)
    assert isinstance(router, ChatAnthropic)
    assert router.default_headers == {"anthropic-workspace-id": "wrkspc_123"}


def test_google_provider_builds_gemini_model() -> None:
    s = Settings(
        _env_file=None,
        llm_provider="google",
        google_api_key="k",
        llm_model_router="gemini-x",
        llm_effort_router="low",
    )
    router = get_chat_model("router", s)
    assert isinstance(router, ChatGoogleGenerativeAI)
    assert router.model.removeprefix("models/") == "gemini-x"
    assert router.reasoning_effort == "low"
    generator = get_chat_model("generator", s)
    assert isinstance(generator, ChatGoogleGenerativeAI)
    assert generator.reasoning_effort is None
