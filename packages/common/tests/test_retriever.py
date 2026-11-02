from uuid import uuid4

from common.embedder import TEIEmbedder
from common.qdrant_repo import DENSE_VECTOR, ensure_collection
from common.reranker import NoopReranker
from common.retriever import DenseRetriever, build_filter
from common.schemas.chunk import RetrievalFilters
from common.settings import Settings
from qdrant_client import AsyncQdrantClient, models


class FakeEmbedder(TEIEmbedder):
    def __init__(self) -> None:
        super().__init__("http://x", model="m", dim=4, query_instruction="t")

    async def embed_query(self, query: str, *, with_instruction: bool = True) -> list[float]:
        return [1.0, 0.0, 0.0, 0.0]


def test_build_filter() -> None:
    assert build_filter(None) is None
    assert build_filter(RetrievalFilters()) is None
    doc = uuid4()
    f = build_filter(RetrievalFilters(doc_ids=[doc], sources=["a"]))
    assert f is not None and isinstance(f.must, list) and len(f.must) == 2


async def test_dense_retriever_with_doc_filter() -> None:
    settings = Settings(_env_file=None, embeddings_dim=4, qdrant_collection="c")
    client = AsyncQdrantClient(":memory:")
    await ensure_collection(client, settings)
    doc_a, doc_b = uuid4(), uuid4()
    await client.upsert(
        "c",
        points=[
            models.PointStruct(
                id=str(uuid4()),
                vector={DENSE_VECTOR: [1.0, 0.0, 0.0, 0.0]},
                payload={
                    "doc_id": str(doc_a),
                    "text": "A",
                    "title": "ta",
                    "url": "u#a",
                    "section": "S > A",
                    "anchor": "#a",
                    "page": None,
                    "source": "sa",
                },
            ),
            models.PointStruct(
                id=str(uuid4()),
                vector={DENSE_VECTOR: [0.9, 0.1, 0.0, 0.0]},
                payload={
                    "doc_id": str(doc_b),
                    "text": "B",
                    "title": "tb",
                    "url": "u#b",
                    "source": "sb",
                },
            ),
        ],
    )
    retriever = DenseRetriever(client, FakeEmbedder(), "c")
    results = await retriever.retrieve("q", k=5)
    assert [r.text for r in results] == ["A", "B"]
    only_b = await retriever.retrieve("q", RetrievalFilters(doc_ids=[doc_b]), k=5)
    assert [r.text for r in only_b] == ["B"]
    assert await NoopReranker().rerank("q", only_b) == only_b
