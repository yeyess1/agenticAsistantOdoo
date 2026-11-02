"""Qdrant collection bootstrap (V-01, V-02, V-03, C-04, D-05).

The collection and its payload indexes are created BEFORE any ingestion, so that the
HNSW graph is filterable (adding indexes later forces a rebuild).
"""

from __future__ import annotations

import logging

from qdrant_client import AsyncQdrantClient, models

from common.settings import Settings

log = logging.getLogger(__name__)

DENSE_VECTOR = "dense"
SPARSE_VECTOR = "sparse"

HNSW_M = 16
HNSW_EF_CONSTRUCT = 200
# Thresholds are in KB where 1 KB = 1 vector of 256 dims (so 1 vector of 1024 dims = 4 KB).
# Defaults (full_scan 10_000 / indexing 20_000) would keep a ~2-6k point corpus in
# brute-force mode; lowered so HNSW is built and its parameters apply (V-a, V-04).
FULL_SCAN_THRESHOLD_KB = 1000
INDEXING_THRESHOLD_KB = 1000

PAYLOAD_INDEXES: dict[str, models.PayloadSchemaType] = {
    "doc_id": models.PayloadSchemaType.KEYWORD,
    "source": models.PayloadSchemaType.KEYWORD,
    "section": models.PayloadSchemaType.KEYWORD,
    "content_hash": models.PayloadSchemaType.KEYWORD,
    "ingested_at": models.PayloadSchemaType.DATETIME,
}


class CollectionMismatchError(RuntimeError):
    """The existing collection does not match the configured embedding model/dimension."""


async def ensure_collection(client: AsyncQdrantClient, settings: Settings) -> bool:
    """Create the collection and payload indexes if missing. Idempotent.

    Returns True when the collection was created, False if it already existed.
    Raises `CollectionMismatchError` when an existing collection has another dense size.
    """
    name = settings.qdrant_collection
    created = False
    if not await client.collection_exists(name):
        await client.create_collection(
            name,
            vectors_config={
                DENSE_VECTOR: models.VectorParams(
                    size=settings.embeddings_dim,
                    distance=models.Distance.COSINE,
                    hnsw_config=models.HnswConfigDiff(
                        m=HNSW_M,
                        ef_construct=HNSW_EF_CONSTRUCT,
                        full_scan_threshold=FULL_SCAN_THRESHOLD_KB,
                    ),
                )
            },
            # Reserved for challenge B (BM25); stays empty until then.
            sparse_vectors_config={
                SPARSE_VECTOR: models.SparseVectorParams(modifier=models.Modifier.IDF)
            },
            optimizers_config=models.OptimizersConfigDiff(indexing_threshold=INDEXING_THRESHOLD_KB),
            metadata={
                "embedding_model": settings.embeddings_model,
                "embedding_dim": settings.embeddings_dim,
            },
        )
        created = True
        log.info("created collection %s", name)
    else:
        await _check_dense_size(client, name, settings.embeddings_dim)

    for field, schema in PAYLOAD_INDEXES.items():
        await client.create_payload_index(name, field_name=field, field_schema=schema)
    return created


async def _check_dense_size(client: AsyncQdrantClient, name: str, expected: int) -> None:
    info = await client.get_collection(name)
    vectors = info.config.params.vectors
    params = vectors.get(DENSE_VECTOR) if isinstance(vectors, dict) else None
    if params is None or params.size != expected:
        raise CollectionMismatchError(
            f"collection {name!r} has no '{DENSE_VECTOR}' vector of size {expected}"
        )
