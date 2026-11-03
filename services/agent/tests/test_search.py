from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

import httpx
import pytest
from agent.api import routes_search
from common.embedder import TEIEmbedder
from common.qdrant_repo import DENSE_VECTOR, ensure_collection
from common.settings import Settings
from fastapi import FastAPI
from fastapi.testclient import TestClient
from qdrant_client import AsyncQdrantClient, models


class FakeEmbedder(TEIEmbedder):
    def __init__(self, fail: bool = False) -> None:
        super().__init__("http://x", model="m", dim=4, query_instruction="t")
        self.fail = fail
        self.seen: list[tuple[str, bool]] = []

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0, 0.0] for _ in texts]

    async def embed_query(self, query: str, *, with_instruction: bool = True) -> list[float]:
        if self.fail:
            raise httpx.ConnectError("tei down")
        self.seen.append((query, with_instruction))
        return [1.0, 0.0, 0.0, 0.0]


@pytest.fixture
def setup() -> tuple[TestClient, str, str, FakeEmbedder]:
    settings = Settings(_env_file=None, embeddings_dim=4, qdrant_collection="c")
    qdrant = AsyncQdrantClient(":memory:")
    import asyncio

    asyncio.run(ensure_collection(qdrant, settings))
    doc_a, doc_b = str(uuid4()), str(uuid4())

    def point(doc: str, vec: list[float], **extra: object) -> models.PointStruct:
        payload = {"doc_id": doc, "text": "t", "title": "T", "source": "s", "url": "s#a", **extra}
        return models.PointStruct(id=str(uuid4()), vector={DENSE_VECTOR: vec}, payload=payload)

    asyncio.run(
        qdrant.upsert(
            "c",
            points=[
                point(doc_a, [1, 0, 0, 0], section="A > one", anchor="#one", page=None),
                point(doc_b, [0.9, 0.1, 0, 0], section="B > two", anchor=None, page=7),
            ],
        )
    )
    embedder = FakeEmbedder()
    app = FastAPI()
    app.include_router(routes_search.router)
    app.state.settings, app.state.qdrant, app.state.embedder = settings, qdrant, embedder
    return TestClient(app), doc_a, doc_b, embedder


def test_search_returns_section_anchor_and_page(
    setup: tuple[TestClient, str, str, FakeEmbedder],
) -> None:
    client, doc_a, doc_b, embedder = setup
    body = client.post("/search", json={"query": "computed field?", "top_k": 5}).json()
    results = body["results"]
    assert [r["doc_id"] for r in results] == [doc_a, doc_b]
    assert results[0]["section"] == "A > one" and results[0]["anchor"] == "#one"
    assert results[1]["page"] == 7
    assert body["took_ms"] >= 0
    assert embedder.seen == [("computed field?", True)]


def test_search_filters_by_doc_id_and_top_k(
    setup: tuple[TestClient, str, str, FakeEmbedder],
) -> None:
    client, _doc_a, doc_b, _ = setup
    only_b = client.post(
        "/search", json={"query": "q", "filters": {"doc_ids": [doc_b]}, "with_instruction": False}
    ).json()["results"]
    assert [r["doc_id"] for r in only_b] == [doc_b]
    assert len(client.post("/search", json={"query": "q", "top_k": 1}).json()["results"]) == 1
    assert client.post("/search", json={"query": "q", "exact": True}).status_code == 200


def test_search_validation_and_upstream_error(
    setup: tuple[TestClient, str, str, FakeEmbedder],
) -> None:
    client, _, _, embedder = setup
    assert client.post("/search", json={"query": ""}).status_code == 422
    assert client.post("/search", json={"query": "q", "top_k": 0}).status_code == 422
    embedder.fail = True
    r = client.post("/search", json={"query": "q"})
    assert r.status_code == 502 and r.json()["detail"]["error"]["code"] == "embeddings_unavailable"
