from pathlib import Path

from common.db.migrate import list_migrations
from common.llm import get_chat_model, model_name_for
from common.pricing import cost_usd
from common.settings import Settings


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


def test_llm_role_model_comes_from_settings() -> None:
    s = Settings(_env_file=None, llm_model_router="custom-model", anthropic_api_key="k")
    assert model_name_for("router", s) == "custom-model"
    assert get_chat_model("generator", s).model == "claude-sonnet-5-5"
