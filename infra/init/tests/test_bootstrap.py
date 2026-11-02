"""Bootstrap logic against in-memory Qdrant (no Docker, no network)."""

import pytest
from common.qdrant_repo import (
    DENSE_VECTOR,
    PAYLOAD_INDEXES,
    SPARSE_VECTOR,
    CollectionMismatchError,
    ensure_collection,
)
from common.settings import Settings
from qdrant_client import AsyncQdrantClient


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, qdrant_collection="test_collection")


async def test_ensure_collection_creates_vectors_and_is_idempotent(settings: Settings) -> None:
    client = AsyncQdrantClient(":memory:")
    assert await ensure_collection(client, settings) is True
    assert await ensure_collection(client, settings) is False

    info = await client.get_collection("test_collection")
    vectors = info.config.params.vectors
    assert isinstance(vectors, dict)
    dense = vectors[DENSE_VECTOR]
    assert dense.size == 1024
    assert dense.hnsw_config is not None
    assert dense.hnsw_config.m == 16
    assert dense.hnsw_config.ef_construct == 200
    sparse = info.config.params.sparse_vectors
    assert sparse is not None and SPARSE_VECTOR in sparse
    assert set(PAYLOAD_INDEXES) == {"doc_id", "source", "section", "content_hash", "ingested_at"}


async def test_dimension_mismatch_raises(settings: Settings) -> None:
    client = AsyncQdrantClient(":memory:")
    await ensure_collection(client, settings)
    other = settings.model_copy(update={"embeddings_dim": 768})
    with pytest.raises(CollectionMismatchError):
        await ensure_collection(client, other)
