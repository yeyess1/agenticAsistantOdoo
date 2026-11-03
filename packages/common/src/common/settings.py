"""Application settings (pydantic-settings) and feature flags (A-09, D-13, D-14)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal
from urllib.parse import quote

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_QUERY_INSTRUCTION = (
    "Given a developer question about Odoo 19, retrieve relevant documentation passages "
    "that answer the question"
)


class Settings(BaseSettings):
    """All configuration comes from the environment / `.env` (see `.env.example`)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- LLM (D-03): one model per role -------------------------------------------------
    anthropic_api_key: SecretStr = SecretStr("")
    llm_model_contextualizer: str = "claude-haiku-5-5"
    llm_model_router: str = "claude-haiku-5-5"
    llm_model_grader: str = "claude-haiku-5-5"
    llm_model_rewriter: str = "claude-haiku-5-5"
    llm_model_direct: str = "claude-haiku-5-5"
    llm_model_generator: str = "claude-sonnet-5-5"
    llm_model_research: str = "claude-sonnet-5-5"
    llm_model_judge: str = "claude-opus-5-5"
    llm_effort_router: str = "low"
    llm_effort_grader: str = "low"

    # --- Embeddings (D-04, TEI) -----------------------------------------------------------
    embeddings_url: str = "http://embeddings:80"
    embeddings_model: str = "Qwen/Qwen3-Embedding-0.6B"
    embeddings_dim: int = 1024
    embeddings_query_instruction: str = DEFAULT_QUERY_INSTRUCTION
    hf_token: SecretStr = SecretStr("")

    # --- Qdrant (D-05) --------------------------------------------------------------------
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "odoo19_dev"
    qdrant_hnsw_ef: int = 128

    # --- Postgres (D-08) ------------------------------------------------------------------
    postgres_user: str = "odoo_rag"
    postgres_password: SecretStr = SecretStr("")
    postgres_db: str = "odoo_rag"
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    database_url: SecretStr | None = Field(
        default=None, description="Composed from POSTGRES_* when empty."
    )

    # --- Chunking (D-06) ------------------------------------------------------------------
    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 64
    chunk_min_tokens: int = 100

    tokenizer_cache_dir: str = "~/.cache/odoo-rag/tokenizers"

    # --- Agent limits ---------------------------------------------------------------------
    retriever_top_k: int = 10
    max_rewrites: int = 2
    research_max_iterations: int = 4
    history_max_turns: int = 6
    history_max_tokens: int = 4000

    # --- Feature flags (D-13, A-09) -------------------------------------------------------
    hitl_enabled: bool = False
    retriever: Literal["dense", "hybrid"] = "dense"
    reranker: Literal["none", "qwen3"] = "none"
    tracing: Literal["none", "langfuse"] = "none"
    search_provider: Literal["ddgs", "searxng"] = "ddgs"

    # --- External tools (D-07) ------------------------------------------------------------
    searxng_url: str = "http://searxng:8080"
    forum_allowed_domains: str = "www.odoo.com"
    search_timeout_s: float = 10.0
    read_timeout_s: float = 15.0
    search_max_retries: int = 2
    search_cache_ttl_s: int = 3600
    http_user_agent: str = "odoo-rag-assistant/0.1 (+https://github.com/OWNER/finanzauto)"

    # --- Observability (challenge E) ------------------------------------------------------
    langfuse_public_key: SecretStr = SecretStr("")
    langfuse_secret_key: SecretStr = SecretStr("")
    langfuse_host: str = ""

    # --- Misc -----------------------------------------------------------------------------
    max_upload_mb: int = 20
    agent_url: str = "http://agent:8000"
    ingestion_url: str = "http://ingestion:8001"
    log_level: str = "INFO"

    @property
    def forum_allowed_domain_list(self) -> list[str]:
        return [d.strip().lower() for d in self.forum_allowed_domains.split(",") if d.strip()]

    @property
    def resolved_database_url(self) -> str:
        """Connection string for psycopg (explicit `DATABASE_URL` wins)."""
        if self.database_url is not None and self.database_url.get_secret_value():
            return self.database_url.get_secret_value()
        user = quote(self.postgres_user, safe="")
        password = quote(self.postgres_password.get_secret_value(), safe="")
        return (
            f"postgresql://{user}:{password}@{self.postgres_host}:{self.postgres_port}"
            f"/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
