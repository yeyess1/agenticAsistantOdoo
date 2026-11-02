from common.settings import Settings


def make(**kw: object) -> Settings:
    return Settings(_env_file=None, **kw)  # type: ignore[arg-type]


def test_defaults_match_design() -> None:
    s = make()
    assert s.llm_model_generator == "claude-sonnet-5-5"
    assert s.llm_model_judge == "claude-opus-5-5"
    assert s.embeddings_dim == 1024
    assert s.qdrant_collection == "odoo19_dev"
    assert (s.retriever_top_k, s.max_rewrites, s.research_max_iterations) == (10, 2, 4)
    assert s.hitl_enabled is False
    assert (s.retriever, s.reranker, s.tracing, s.search_provider) == (
        "dense",
        "none",
        "none",
        "ddgs",
    )


def test_database_url_is_composed_and_quoted() -> None:
    s = make(postgres_user="u", postgres_password="p@ss/w", postgres_db="d")
    assert s.resolved_database_url == "postgresql://u:p%40ss%2Fw@postgres:5432/d"


def test_explicit_database_url_wins() -> None:
    s = make(database_url="postgresql://x:y@h:1/z")
    assert s.resolved_database_url == "postgresql://x:y@h:1/z"


def test_secrets_are_not_leaked_in_repr() -> None:
    s = make(anthropic_api_key="sk-secret", postgres_password="pw")
    assert "sk-secret" not in repr(s)
    assert "pw'" not in repr(s)


def test_forum_domains_parsing() -> None:
    assert make(forum_allowed_domains="www.odoo.com, Odoo.com").forum_allowed_domain_list == [
        "www.odoo.com",
        "odoo.com",
    ]


def test_flags_reject_invalid_values() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        make(retriever="bm25")


def test_env_example_is_complete_and_loadable() -> None:
    """Every setting is documented in `.env.example`, and the file parses into Settings."""
    from pathlib import Path

    env_example = next(p for p in Path(__file__).parents if (p / ".env.example").exists()) / (
        ".env.example"
    )
    keys = {
        line.split("=", 1)[0].strip().lower()
        for line in env_example.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }
    assert set(Settings.model_fields) <= keys
    s = Settings(_env_file=env_example)
    assert s.qdrant_collection == "odoo19_dev"
    assert s.resolved_database_url.startswith("postgresql://odoo_rag:")
