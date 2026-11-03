"""E-11: deterministic metrics (context precision, recall@k, precision@k, MRR, routing)."""

from __future__ import annotations

import pytest
from metrics.citations import citation_correctness
from metrics.correctness import CorrectnessVerdict, claim_f1, correctness_scores
from metrics.faithfulness import ClaimVerdict, FaithfulnessVerdict, faithfulness_score
from metrics.relevancy import cosine, relevancy_score
from metrics.retrieval import (
    chunk_key,
    context_precision,
    mean_reciprocal_rank,
    overlap_at_k,
    parse_section_ref,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    relevance_flags,
)
from metrics.routing import routing_report
from metrics.stats import mean, percentile

URL = "https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html"
A = (URL, "computed-fields", None)
B = (URL, "odoo.fields.Many2one", None)
C = (URL, "fields", None)
PDF8 = ("coding_guidelines.pdf", None, 8)


# ------------------------------------------------------------------ section keys
def test_parse_section_ref_web_and_pdf() -> None:
    assert parse_section_ref(f"{URL}#computed-fields") == A
    assert parse_section_ref("coding_guidelines.pdf#page=8") == PDF8


@pytest.mark.parametrize("bad", [URL, f"{URL}#", "#anchor", ""])
def test_parse_section_ref_rejects_malformed(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_section_ref(bad)


def test_chunk_key_matches_payload_and_source_shapes() -> None:
    # Qdrant payload: url already carries the anchor; /search also returns `anchor`.
    assert chunk_key(f"{URL}#computed-fields", "#computed-fields") == A
    # Answer sources: `url#anchor`, no separate anchor.
    assert chunk_key(f"{URL}#computed-fields") == A
    assert chunk_key(URL, "computed-fields") == A
    # PDF chunks: no anchor, matched on (file, page), whatever the path prefix.
    assert chunk_key("coding_guidelines.pdf", None, 8) == PDF8
    assert chunk_key("/data/corpus/coding_guidelines.pdf", None, 8) == PDF8
    assert chunk_key("coding_guidelines.pdf", None, 9) != PDF8


# ------------------------------------------------------------------ ranking metrics
def test_context_precision_d12_example() -> None:
    # D-12: [1, 0, 1, 0] -> (1 + 2/3) / 2 = 0.83
    assert context_precision([True, False, True, False]) == pytest.approx(5 / 6)


def test_context_precision_edges() -> None:
    assert context_precision([]) is None
    assert context_precision([False, False]) == 0.0
    assert context_precision([True, True, True]) == 1.0
    assert context_precision([False, True]) == pytest.approx(0.5)
    # K truncates the list before averaging.
    assert context_precision([True, False, False, True], k=2) == 1.0


def test_recall_at_k_counts_distinct_sections() -> None:
    relevant = {A, B, PDF8}
    keys = [A, A, C, PDF8, B]
    assert recall_at_k(keys, relevant, 1) == pytest.approx(1 / 3)
    assert recall_at_k(keys, relevant, 2) == pytest.approx(1 / 3)  # duplicate chunk of A
    assert recall_at_k(keys, relevant, 4) == pytest.approx(2 / 3)
    assert recall_at_k(keys, relevant, 10) == 1.0
    assert recall_at_k(keys, set(), 5) is None


def test_precision_at_k_counts_chunks_and_divides_by_k() -> None:
    hits = relevance_flags([A, C, A, B], {A, B})
    assert hits == [True, False, True, True]
    assert precision_at_k(hits, 1) == 1.0
    assert precision_at_k(hits, 2) == 0.5
    assert precision_at_k(hits, 4) == 0.75
    assert precision_at_k(hits, 8) == 0.375  # short list
    with pytest.raises(ValueError):
        precision_at_k(hits, 0)


def test_reciprocal_rank_and_mrr() -> None:
    assert reciprocal_rank([False, False, True]) == pytest.approx(1 / 3)
    assert reciprocal_rank([True]) == 1.0
    assert reciprocal_rank([False, False]) == 0.0
    assert mean_reciprocal_rank([[True], [False, True], [False]]) == pytest.approx(0.5)
    assert mean_reciprocal_rank([]) is None


def test_overlap_at_k_hnsw_vs_exact() -> None:
    exact = ["a", "b", "c", "d"]
    assert overlap_at_k(["a", "b", "c", "d"], exact, 4) == 1.0
    assert overlap_at_k(["b", "a", "x", "c"], exact, 4) == 0.75  # order does not matter
    assert overlap_at_k(["x"], exact, 1) == 0.0
    assert overlap_at_k([], [], 3) == 1.0


def test_citation_correctness() -> None:
    assert citation_correctness([A, C], {A, B}) == 0.5
    assert citation_correctness([], {A}) is None


# ------------------------------------------------------------------ routing
def test_routing_report_accuracy_confusion_and_per_class() -> None:
    expected = ["docs", "docs", "research", "research", "direct", "direct"]
    predicted = ["docs", "research", "research", "docs", "direct", None]
    r = routing_report(expected, predicted)
    assert r["n"] == 6
    assert r["correct"] == 3
    assert r["accuracy"] == 0.5
    assert r["confusion"]["docs"] == {"docs": 1, "research": 1, "direct": 0, "none": 0}
    assert r["confusion"]["direct"]["none"] == 1
    docs = r["per_class"]["docs"]
    assert docs["precision"] == 0.5  # 1 of the 2 predicted docs
    assert docs["recall"] == 0.5
    assert docs["f1"] == 0.5
    direct = r["per_class"]["direct"]
    assert direct["precision"] == 1.0
    assert direct["recall"] == 0.5


def test_routing_report_validates_input() -> None:
    with pytest.raises(ValueError):
        routing_report(["docs"], [])
    with pytest.raises(ValueError):
        routing_report(["web"], ["docs"])
    empty = routing_report([], [])
    assert empty["accuracy"] is None


# ------------------------------------------------------------------ judge-derived scores
def test_claim_f1_and_correctness_scores() -> None:
    assert claim_f1(3, 1, 2) == pytest.approx(6 / 9)
    assert claim_f1(0, 0, 0) is None
    s = correctness_scores(CorrectnessVerdict(tp=["a", "b"], fp=["c"], fn=["d", "e"]))
    assert s["f1"] == pytest.approx(4 / 7)
    assert s["precision"] == pytest.approx(2 / 3)
    assert s["recall"] == pytest.approx(0.5)


def test_faithfulness_score() -> None:
    v = FaithfulnessVerdict(
        claims=[
            ClaimVerdict(claim="x", supported=True),
            ClaimVerdict(claim="y", supported=False),
            ClaimVerdict(claim="z", supported=True),
        ]
    )
    assert faithfulness_score(v) == pytest.approx(2 / 3)
    assert faithfulness_score(FaithfulnessVerdict(claims=[])) is None


def test_relevancy_cosine_mean() -> None:
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert cosine([1.0, 1.0], [2.0, 2.0]) == pytest.approx(1.0)
    assert cosine([0.0, 0.0], [1.0, 0.0]) == 0.0
    assert relevancy_score([1.0, 0.0], [[1.0, 0.0], [0.0, 1.0]]) == pytest.approx(0.5)
    assert relevancy_score([1.0, 0.0], []) == 0.0


def test_stats_helpers() -> None:
    assert mean([1, None, 3]) == 2.0
    assert mean([None]) is None
    values = list(range(1, 21))
    assert percentile(values, 50) == 10
    assert percentile(values, 95) == 19
    assert percentile(values, 100) == 20
    assert percentile([], 50) is None
