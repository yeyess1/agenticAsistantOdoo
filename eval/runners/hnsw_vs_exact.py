"""V-04: recall@k of HNSW vs exact (brute-force) search, and search latency.

Queries are embedded once (TEI, with the Qwen3 query instruction, as the retriever does)
and sent straight to Qdrant, so the latency measures only the vector search (through
`/search` it is dominated by the ~0.3 s CPU embedding). Same `query_points` call and
parameters as `DenseRetriever` (`/search` with `exact` / `hnsw_ef`).
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any

from common.embedder import Embedder
from common.qdrant_repo import DENSE_VECTOR
from metrics.retrieval import overlap_at_k
from metrics.stats import mean, percentile, rnd
from qdrant_client import AsyncQdrantClient, models

EF_VALUES: tuple[int, ...] = (10, 16, 32, 64, 128, 256)
K_VALUES: tuple[int, ...] = (1, 5, 10)
TOP_K = 10
REPEATS = 5


async def collection_state(client: AsyncQdrantClient, collection: str) -> dict[str, Any]:
    info = await client.get_collection(collection)
    vectors = info.config.params.vectors
    params = vectors.get(DENSE_VECTOR) if isinstance(vectors, dict) else None
    hnsw = params.hnsw_config if params else None
    return {
        "points_count": info.points_count,
        "indexed_vectors_count": info.indexed_vectors_count,
        "segments_count": info.segments_count,
        "m": hnsw.m if hnsw else None,
        "ef_construct": hnsw.ef_construct if hnsw else None,
        "full_scan_threshold_kb": hnsw.full_scan_threshold if hnsw else None,
        "indexing_threshold_kb": info.config.optimizer_config.indexing_threshold,
    }


async def _search(
    client: AsyncQdrantClient,
    collection: str,
    vector: list[float],
    *,
    exact: bool,
    hnsw_ef: int | None,
) -> tuple[list[str], float]:
    started = time.perf_counter()
    res = await client.query_points(
        collection,
        query=vector,
        using=DENSE_VECTOR,
        limit=TOP_K,
        with_payload=False,
        search_params=models.SearchParams(hnsw_ef=hnsw_ef, exact=exact),
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    return [str(p.id) for p in res.points], elapsed_ms


async def run_hnsw_vs_exact(
    client: AsyncQdrantClient,
    embedder: Embedder,
    collection: str,
    queries: Sequence[str],
    *,
    ef_values: Sequence[int] = EF_VALUES,
    repeats: int = REPEATS,
) -> dict[str, Any]:
    vectors = [await embedder.embed_query(q) for q in queries]
    exact_ids: list[list[str]] = []
    exact_lat: list[float] = []
    for v in vectors:
        ids, _ = await _search(client, collection, v, exact=True, hnsw_ef=None)  # warm-up
        exact_ids.append(ids)
        for _ in range(repeats):
            exact_lat.append((await _search(client, collection, v, exact=True, hnsw_ef=None))[1])

    sweeps: list[dict[str, Any]] = []
    for ef in ef_values:
        recalls: dict[int, list[float]] = {k: [] for k in K_VALUES}
        lat: list[float] = []
        for v, ref in zip(vectors, exact_ids, strict=True):
            ids, _ = await _search(client, collection, v, exact=False, hnsw_ef=ef)
            for k in K_VALUES:
                recalls[k].append(overlap_at_k(ids, ref, k))
            for _ in range(repeats):
                lat.append((await _search(client, collection, v, exact=False, hnsw_ef=ef))[1])
        sweeps.append(
            {
                "hnsw_ef": ef,
                **{f"recall@{k}": rnd(mean(recalls[k])) for k in K_VALUES},
                "min_recall@10": rnd(min(recalls[10])),
                "latency_ms_p50": rnd(percentile(lat, 50), 3),
                "latency_ms_p95": rnd(percentile(lat, 95), 3),
            }
        )
    return {
        "n_queries": len(queries),
        "top_k": TOP_K,
        "repeats": repeats,
        "collection": await collection_state(client, collection),
        "exact": {
            "latency_ms_p50": rnd(percentile(exact_lat, 50), 3),
            "latency_ms_p95": rnd(percentile(exact_lat, 95), 3),
        },
        "hnsw": sweeps,
    }
