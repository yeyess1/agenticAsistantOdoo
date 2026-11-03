from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from common.ids import doc_id_for
from common.qdrant_repo import ensure_collection
from common.retriever import DenseRetriever
from common.schemas.chunk import RetrievalFilters
from common.settings import Settings
from fastapi import FastAPI
from fastapi.testclient import TestClient
from ingestion.api import routes_documents, routes_health
from ingestion.chunking.tokenizer import CharTokenCounter
from ingestion.pipeline import IngestionPipeline
from ingestion_fakes import FakeEmbedder, FakeRepo
from qdrant_client import AsyncQdrantClient

COLLECTION = "test_docs"
WEB_DOC = (
    b"---\nurl: https://odoo.test/orm.html\ntitle: ORM API\n---\n\n"
    b"# ORM API {#orm-api}\n\n## Fields {#fields}\n\n"
    + (b"Computed fields use the compute attribute. " * 30)
    + b"\n\n```python\nx = fields.Float(compute='_c')\n```\n"
)
OTHER_DOC = b"# Other\n\n## Views\n\n" + (b"Views describe the UI. " * 30)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        embeddings_dim=8,
        qdrant_collection=COLLECTION,
        chunk_size_tokens=200,
        chunk_overlap_tokens=20,
        chunk_min_tokens=10,
    )


@pytest.fixture
async def stack(settings: Settings) -> AsyncIterator[dict[str, Any]]:
    qdrant = AsyncQdrantClient(":memory:")
    await ensure_collection(qdrant, settings)
    repo, embedder = FakeRepo(), FakeEmbedder()
    pipeline = IngestionPipeline(settings, embedder, qdrant, repo, CharTokenCounter())  # type: ignore[arg-type]
    yield {"qdrant": qdrant, "repo": repo, "embedder": embedder, "pipeline": pipeline}
    await qdrant.close()


async def count(qdrant: AsyncQdrantClient) -> int:
    return (await qdrant.count(COLLECTION)).count


async def test_ingest_creates_points_with_metadata(stack: dict[str, Any]) -> None:
    res = await stack["pipeline"].ingest(WEB_DOC, "orm.md")
    assert (res.action, res.status, res.doc_id) == (
        "created",
        "indexed",
        doc_id_for("https://odoo.test/orm.html"),
    )
    assert res.n_chunks > 1
    assert await count(stack["qdrant"]) == res.n_chunks
    points, _ = await stack["qdrant"].scroll(COLLECTION, limit=50, with_payload=True)
    payload = points[0].payload
    assert payload is not None
    for key in (
        "doc_id", "chunk_index", "source", "title", "section", "anchor", "url", "page",
        "text", "n_tokens", "content_hash", "embedding_model", "ingested_at",
    ):  # fmt: skip
        assert key in payload
    assert payload["url"] == "https://odoo.test/orm.html" + payload["anchor"]
    assert payload["section"] == "ORM API > Fields"
    assert payload["page"] is None
    assert not str(payload["text"]).startswith("ORM API")  # path is NOT part of displayed text
    row = await stack["repo"].get(res.doc_id)
    assert row is not None and (row.status, row.n_chunks) == ("indexed", res.n_chunks)


async def test_section_path_is_vectorized_not_displayed(stack: dict[str, Any]) -> None:
    await stack["pipeline"].ingest(WEB_DOC, "orm.md")
    first = stack["embedder"].calls[0][0]
    assert first.startswith("ORM API > Fields\n\n")


async def test_reingest_same_content_is_unchanged(stack: dict[str, Any]) -> None:
    first = await stack["pipeline"].ingest(WEB_DOC, "orm.md")
    calls = len(stack["embedder"].calls)
    again = await stack["pipeline"].ingest(WEB_DOC, "orm.md")
    assert again.action == "unchanged"
    assert len(stack["embedder"].calls) == calls  # nothing re-embedded
    assert await count(stack["qdrant"]) == first.n_chunks  # no duplicates


async def test_changed_content_replaces_points(stack: dict[str, Any]) -> None:
    await stack["pipeline"].ingest(WEB_DOC, "orm.md")
    shorter = WEB_DOC.split(b"\n\n```python")[0].replace(b"30", b"3")[:300] + b"\n"
    res = await stack["pipeline"].ingest(shorter, "orm.md")
    assert res.action == "updated"
    assert await count(stack["qdrant"]) == res.n_chunks


async def test_force_reindexes(stack: dict[str, Any]) -> None:
    await stack["pipeline"].ingest(WEB_DOC, "orm.md")
    res = await stack["pipeline"].ingest(WEB_DOC, "orm.md", force=True)
    assert res.action == "updated"


async def test_delete_removes_points_and_row(stack: dict[str, Any]) -> None:
    a = await stack["pipeline"].ingest(WEB_DOC, "orm.md")
    b = await stack["pipeline"].ingest(OTHER_DOC, "other.md")
    assert await stack["pipeline"].delete_document(a.doc_id) is True
    assert await count(stack["qdrant"]) == b.n_chunks
    assert await stack["repo"].get(a.doc_id) is None
    assert await stack["pipeline"].delete_document(a.doc_id) is False


async def test_metadata_filter_by_doc_id(stack: dict[str, Any], settings: Settings) -> None:
    a = await stack["pipeline"].ingest(WEB_DOC, "orm.md")
    b = await stack["pipeline"].ingest(OTHER_DOC, "other.md")
    retriever = DenseRetriever(stack["qdrant"], stack["embedder"], COLLECTION)
    unfiltered = await retriever.retrieve("computed fields", k=50)
    assert {c.doc_id for c in unfiltered} == {str(a.doc_id), str(b.doc_id)}
    only_b = await retriever.retrieve("computed fields", RetrievalFilters(doc_ids=[b.doc_id]), k=50)
    assert only_b and {c.doc_id for c in only_b} == {str(b.doc_id)}
    # upload without a URL: url is the file name, no anchor
    assert all(c.url == "other.md" and c.anchor is None for c in only_b)


async def test_failure_marks_document_failed(stack: dict[str, Any]) -> None:
    class Boom(FakeEmbedder):
        async def embed_documents(self, texts: Any) -> Any:
            raise RuntimeError("tei down")

    pipeline = IngestionPipeline(
        stack["pipeline"]._s,
        Boom(),
        stack["qdrant"],
        stack["repo"],
        CharTokenCounter(),
    )
    with pytest.raises(RuntimeError):
        await pipeline.ingest(WEB_DOC, "orm.md")
    row = await stack["repo"].get(doc_id_for("https://odoo.test/orm.html"))
    assert row is not None and row.status == "failed" and "tei down" in (row.error or "")
    assert await count(stack["qdrant"]) == 0


async def test_pdf_chunks_carry_page(stack: dict[str, Any]) -> None:
    from test_parsers import make_pdf

    pdf = make_pdf(
        ["Alpha title\n" + "alpha body text. " * 20, "Beta title\n" + "beta body. " * 20]
    )
    await stack["pipeline"].ingest(pdf, "guide.pdf")
    points, _ = await stack["qdrant"].scroll(COLLECTION, limit=50, with_payload=True)
    pages = {p.payload["page"] for p in points if p.payload}
    assert pages == {1, 2}
    assert all(p.payload and p.payload["url"] == "guide.pdf" for p in points)


def make_client(stack: dict[str, Any], settings: Settings) -> TestClient:
    app = FastAPI()
    app.include_router(routes_documents.router)
    app.include_router(routes_health.router)
    app.state.settings = settings
    app.state.repo = stack["repo"]
    app.state.pipeline = stack["pipeline"]
    app.state.qdrant = stack["qdrant"]
    return TestClient(app)


def test_api_upload_list_get_delete(stack: dict[str, Any], settings: Settings) -> None:
    # TestClient runs the app in its own loop; Qdrant `:memory:` and fakes are loop-agnostic.
    client = make_client(stack, settings)
    r = client.post("/documents", files={"file": ("orm.md", WEB_DOC)})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["action"] == "created" and body["n_chunks"] > 0
    doc_id = body["doc_id"]

    listing = client.get("/documents").json()
    assert listing["total"] == 1 and listing["items"][0]["doc_id"] == doc_id
    assert client.get("/documents", params={"status": "failed"}).json()["total"] == 0
    assert client.get(f"/documents/{doc_id}").json()["name"] == "orm.md"

    assert client.delete(f"/documents/{doc_id}").status_code == 204
    assert client.delete(f"/documents/{doc_id}").status_code == 404
    assert client.get(f"/documents/{doc_id}").status_code == 404
    assert client.get("/documents").json() == {"items": [], "total": 0}


def test_api_error_codes(stack: dict[str, Any], settings: Settings) -> None:
    client = make_client(stack, settings)
    assert client.post("/documents", files={"file": ("a.docx", b"x")}).status_code == 415
    assert client.post("/documents", files={"file": ("a.md", b"  ")}).status_code == 422
    assert client.post("/documents", files={"file": ("a.pdf", b"nope")}).status_code == 422
    settings.max_upload_mb = 0
    r = client.post("/documents", files={"file": ("a.md", b"# x\n\ny")})
    assert r.status_code == 413
    assert r.json()["detail"]["error"]["code"] == "file_too_large"
    assert client.get("/documents/not-a-uuid").status_code == 422
