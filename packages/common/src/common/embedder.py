"""Embedder interface and TEI client (A-08, D-04).

Documents are embedded WITHOUT instruction; queries get the Qwen3 instruction prefix
`Instruct: {task}\\nQuery: {q}` prepended here, on the client side.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

import httpx

from common.settings import Settings

TEI_MAX_BATCH = 32


def format_query(task: str, query: str) -> str:
    """Qwen3-Embedding query format (V-p)."""
    return f"Instruct: {task}\nQuery: {query}"


@runtime_checkable
class Embedder(Protocol):
    @property
    def model(self) -> str: ...

    @property
    def dim(self) -> int: ...

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    async def embed_query(self, query: str, *, with_instruction: bool = True) -> list[float]: ...


class TEIEmbedder:
    """Client for a Hugging Face Text Embeddings Inference server (`POST /embed`)."""

    def __init__(
        self,
        base_url: str,
        *,
        model: str,
        dim: int,
        query_instruction: str,
        timeout_s: float = 60.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._model = model
        self._dim = dim
        self._instruction = query_instruction
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=timeout_s)

    @classmethod
    def from_settings(cls, settings: Settings) -> TEIEmbedder:
        return cls(
            settings.embeddings_url,
            model=settings.embeddings_model,
            dim=settings.embeddings_dim,
            query_instruction=settings.embeddings_query_instruction,
        )

    @property
    def model(self) -> str:
        return self._model

    @property
    def dim(self) -> int:
        return self._dim

    async def _embed(self, inputs: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(inputs), TEI_MAX_BATCH):
            batch = inputs[i : i + TEI_MAX_BATCH]
            resp = await self._client.post(
                "/embed", json={"inputs": batch, "normalize": True, "truncate": True}
            )
            resp.raise_for_status()
            out.extend(resp.json())
        return out

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return await self._embed(list(texts))

    async def embed_query(self, query: str, *, with_instruction: bool = True) -> list[float]:
        text = format_query(self._instruction, query) if with_instruction else query
        return (await self._embed([text]))[0]

    async def aclose(self) -> None:
        await self._client.aclose()
