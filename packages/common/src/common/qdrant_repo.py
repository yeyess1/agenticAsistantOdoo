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
# They apply per segment. Qdrant splits even a small collection into several segments
# (8 on the dev host: ~104 points = ~416 KB each), so the 1000 KB of Phase 1 never built
# the HNSW graph (V-04 found `indexed_vectors_count = 0`). 100 KB (25 vectors) builds it
# on every segment and makes unfiltered searches use it (V-a, V-04).
FULL_SCAN_THRESHOLD_KB = 100
INDEXING_THRESHOLD_KB = 100

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
        await _sync_index_thresholds(client, name)

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


async def _sync_index_thresholds(client: AsyncQdrantClient, name: str) -> None:
    """Apply the HNSW thresholds to an existing collection (no reindexing of points).

    Qdrant rebuilds the per-segment HNSW graph in the background; points and payloads
    are untouched.
    """
    info = await client.get_collection(name)
    vectors = info.config.params.vectors
    params = vectors.get(DENSE_VECTOR) if isinstance(vectors, dict) else None
    full_scan = params.hnsw_config.full_scan_threshold if params and params.hnsw_config else None
    indexing = info.config.optimizer_config.indexing_threshold
    if full_scan == FULL_SCAN_THRESHOLD_KB and indexing == INDEXING_THRESHOLD_KB:
        return
    await client.update_collection(
        name,
        vectors_config={
            DENSE_VECTOR: models.VectorParamsDiff(
                hnsw_config=models.HnswConfigDiff(full_scan_threshold=FULL_SCAN_THRESHOLD_KB)
            )
        },
        optimizers_config=models.OptimizersConfigDiff(indexing_threshold=INDEXING_THRESHOLD_KB),
    )
    log.info(
        "collection %s: full_scan_threshold %s -> %s KB, indexing_threshold %s -> %s KB",
        name,
        full_scan,
        FULL_SCAN_THRESHOLD_KB,
        indexing,
        INDEXING_THRESHOLD_KB,
    )
