import json

import httpx
import respx
from common.embedder import Embedder, TEIEmbedder, format_query


def make_embedder() -> TEIEmbedder:
    return TEIEmbedder(
        "http://tei",
        model="Qwen/Qwen3-Embedding-0.6B",
        dim=3,
        query_instruction="find docs",
    )


def test_format_query_is_qwen3_format() -> None:
    assert format_query("task", "q") == "Instruct: task\nQuery: q"


def test_implements_protocol() -> None:
    assert isinstance(make_embedder(), Embedder)


@respx.mock
async def test_query_gets_instruction_documents_do_not() -> None:
    route = respx.post("http://tei/embed").mock(
        return_value=httpx.Response(200, json=[[0.1, 0.2, 0.3]])
    )
    emb = make_embedder()
    await emb.embed_query("how do I x")
    body = json.loads(route.calls.last.request.read())
    assert body["inputs"] == ["Instruct: find docs\nQuery: how do I x"]

    await emb.embed_documents(["doc text"])
    body = json.loads(route.calls.last.request.read())
    assert body["inputs"] == ["doc text"]


@respx.mock
async def test_documents_are_batched() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        n = len(json.loads(request.read())["inputs"])
        return httpx.Response(200, json=[[0.0, 0.0, 0.0]] * n)

    route = respx.post("http://tei/embed").mock(side_effect=handler)
    vectors = await make_embedder().embed_documents([f"t{i}" for i in range(70)])
    assert len(vectors) == 70
    assert route.call_count == 3
