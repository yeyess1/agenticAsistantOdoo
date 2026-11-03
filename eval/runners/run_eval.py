"""Evaluation runner (Phase 4, D-12): `python -m runners.run_eval`.

Steps (ARCHITECTURE §12):
1. load and validate the golden set (E-01);
2. retrieval via `/search`: recall@k, precision@k, MRR, context precision, ES vs EN (E-09);
3. HNSW vs exact search straight on Qdrant (V-04);
4. every question through `POST /query` in `agentic` and `linear` mode (E-05); follow-up
   turns run in order on the same `thread_id`, HITL interrupts are approved via
   `/query/resume`;
5. judges (Opus): faithfulness, answer relevancy (E-03), answer correctness (E-10), and
   expected behaviour for not_covered / out_of_scope;
6. routing accuracy (E-04), aggregates, per-node cost and the evidence for E-07;
7. `reports/<timestamp>.json` + `latest.json` + `latest.md` (README tables) +
   `dashboard.json` (slim copy for `/analytics`, U-12) (E-12).

Runs inside the Compose network (`make eval`, profile `eval`, E-13). `--only q01,q28`
selects items (a follow-up turn pulls in the earlier turns of its thread);
`--from-report` reuses the answers (and judge verdicts) of a previous report.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from common.embedder import Embedder, TEIEmbedder
from common.llm import get_chat_model, model_name_for
from common.settings import Settings, get_settings
from metrics.citations import citation_correctness
from metrics.correctness import judge_behaviour, judge_correctness
from metrics.faithfulness import format_context, judge_faithfulness
from metrics.judge import Judge, JudgeError
from metrics.relevancy import judge_relevancy
from metrics.retrieval import (
    chunk_key,
    context_precision,
    recall_at_k,
    relevance_flags,
)
from metrics.stats import rnd
from qdrant_client import AsyncQdrantClient

from runners.client import AgentClient
from runners.crosslingual import retrieval_items, run_crosslingual, search_metrics
from runners.golden import DEFAULT_GOLDEN, GoldenItem, GoldenSet, load_golden
from runners.hnsw_vs_exact import run_hnsw_vs_exact
from runners.report import build_report, dashboard_view, render_markdown

log = logging.getLogger("eval")

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
MODES: tuple[str, ...] = ("agentic", "linear")
DOCS_CATEGORIES = ("covered", "follow_up")


# ------------------------------------------------------------------------------ selection
def select_items(golden: GoldenSet, only: Sequence[str] | None) -> list[GoldenItem]:
    if not only:
        return list(golden.items)
    wanted = set(only)
    by_id = golden.by_id()
    unknown = wanted - by_id.keys()
    if unknown:
        raise SystemExit(f"unknown ids: {sorted(unknown)}")
    for thread_items in golden.threads().values():
        ids = [i.id for i in thread_items]
        for pos, item_id in enumerate(ids):
            if item_id in wanted:
                wanted.update(ids[:pos])  # earlier turns are needed for the memory
    return [i for i in golden.items if i.id in wanted]


def units(items: Sequence[GoldenItem], mode: str) -> list[list[GoldenItem]]:
    """Execution units: a follow-up thread runs in order (agentic only; linear has no memory)."""
    out: list[list[GoldenItem]] = []
    threads: dict[str, list[GoldenItem]] = {}
    for item in items:
        if mode == "agentic" and item.thread is not None:
            if item.thread not in threads:
                threads[item.thread] = []
                out.append(threads[item.thread])
            threads[item.thread].append(item)
        else:
            out.append([item])
    for group in out:
        group.sort(key=lambda i: i.turn or 0)
    return out


# ------------------------------------------------------------------------------ queries
async def run_queries(
    client: AgentClient,
    items: Sequence[GoldenItem],
    mode: str,
    tag: str,
    concurrency: int,
) -> dict[str, dict[str, Any]]:
    sem = asyncio.Semaphore(concurrency)
    results: dict[str, dict[str, Any]] = {}

    async def run_unit(group: list[GoldenItem]) -> None:
        thread_id = f"eval-{tag}-{mode}-{group[0].thread or group[0].id}"
        async with sem:
            for item in group:
                started = time.perf_counter()
                try:
                    resp = await client.query(item.question, thread_id, mode)
                except Exception as exc:
                    log.warning("%s %s failed: %s", mode, item.id, exc)
                    resp = {"error": str(exc)[:500], "thread_id": thread_id}
                log.info(
                    "%-7s %s -> %s (%.1f s)",
                    mode,
                    item.id,
                    resp.get("answered_by"),
                    time.perf_counter() - started,
                )
                results[item.id] = resp

    await asyncio.gather(*(run_unit(g) for g in units(items, mode)))
    return results


# ------------------------------------------------------------------------------ run record
def compact_steps(steps: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            k: s.get(k)
            for k in (
                "node",
                "agent",
                "duration_ms",
                "model",
                "input_tokens",
                "output_tokens",
                "cost_usd",
                "detail",
            )
        }
        for s in steps
    ]


def run_record(item: GoldenItem, resp: dict[str, Any]) -> dict[str, Any]:
    """Deterministic part of a run: routing, context metrics, citations, cost."""
    if "error" in resp:
        return {"error": resp["error"], "answered_by": None, "route": None}
    relevant = item.section_keys
    sources = resp.get("sources", [])
    doc_sources = [s for s in sources if s.get("kind") == "doc"]
    keys = [chunk_key(s["url"], None, s.get("page")) for s in doc_sources]
    hits = relevance_flags(keys, relevant)
    cited_keys = [k for k, s in zip(keys, doc_sources, strict=True) if s.get("cited")]
    steps = compact_steps(resp.get("steps", []))
    gen = next((s for s in steps if s["node"] == "generator"), None)
    rewrites = [s for s in steps if s["node"] == "rewriter"]
    return {
        "answer": resp.get("answer", ""),
        "answered_by": resp.get("answered_by"),
        "route": resp.get("route"),
        "delegated": resp.get("delegated", False),
        "external": resp.get("external", False),
        "no_context": resp.get("no_context", False),
        "standalone_question": resp.get("standalone_question", ""),
        "thread_id": resp.get("thread_id"),
        "interrupts": resp.get("interrupts", 0),
        "nodes": resp.get("nodes", []),
        "n_rewrites": len(rewrites),
        "rewritten_queries": [s["detail"].get("rewritten") for s in rewrites],
        "latency_ms": resp.get("latency_ms"),
        "client_latency_ms": resp.get("client_latency_ms"),
        "usage": resp.get("usage", {}),
        "generator_usage": (
            {
                "input_tokens": gen["input_tokens"],
                "output_tokens": gen["output_tokens"],
                "cost_usd": gen["cost_usd"],
            }
            if gen
            else None
        ),
        "sources": [
            {
                "n": s["n"],
                "kind": s["kind"],
                "url": s["url"],
                "page": s.get("page"),
                "chunk_id": s.get("chunk_id"),
                "cited": s.get("cited", False),
                "relevant": h,
            }
            for s, h in zip(doc_sources, hits, strict=True)
        ]
        + [
            {"n": s["n"], "kind": s["kind"], "url": s["url"], "cited": s.get("cited", False)}
            for s in sources
            if s.get("kind") != "doc"
        ],
        "context": {
            "n_chunks": len(doc_sources),
            "n_relevant_chunks": sum(hits),
            "context_precision": rnd(context_precision(hits)) if relevant else None,
            "context_recall": rnd(recall_at_k(keys, relevant, len(keys))) if relevant else None,
        },
        "n_cited": len(cited_keys),
        "citation_correctness": rnd(citation_correctness(cited_keys, relevant))
        if relevant
        else None,
        "steps": steps,
    }


# ------------------------------------------------------------------------------ judges
async def fetch_context(
    qdrant: AsyncQdrantClient, collection: str, sources: Sequence[dict[str, Any]]
) -> str:
    docs = [s for s in sources if s.get("kind") == "doc" and s.get("chunk_id")]
    if not docs:
        return ""
    points = await qdrant.retrieve(
        collection, ids=[s["chunk_id"] for s in docs], with_payload=["text", "title", "section"]
    )
    by_id = {str(p.id): p.payload or {} for p in points}
    chunks = []
    for s in docs:
        p = by_id.get(s["chunk_id"], {})
        heading = f"{p.get('title', '')} > {p.get('section') or '-'}"
        chunks.append((int(s["n"]), heading, str(p.get("text", ""))))
    return format_context(chunks)


def judge_question(item: GoldenItem, golden: GoldenSet) -> str:
    """Turn >= 2 questions are judged together with the earlier turns of the thread."""
    if not item.is_follow_up_turn or item.thread is None:
        return item.question
    earlier = [
        i.question for i in golden.threads()[item.thread] if (i.turn or 0) < (item.turn or 0)
    ]
    return "\n".join([*earlier, item.question])


async def judge_run(
    judge: Judge,
    embedder: Embedder,
    qdrant: AsyncQdrantClient,
    collection: str,
    golden: GoldenSet,
    item: GoldenItem,
    rec: dict[str, Any],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    answer = rec.get("answer") or ""
    if "error" in rec or not answer.strip():
        return {"skipped": "no answer"}
    question = judge_question(item, golden)
    tasks: dict[str, Any] = {}
    if item.category in DOCS_CATEGORIES:
        context = await fetch_context(qdrant, collection, rec.get("sources", []))
        if context:
            tasks["faithfulness"] = judge_faithfulness(judge, question, answer, context)
        tasks["relevancy"] = judge_relevancy(judge, embedder, question, answer)
        tasks["correctness"] = judge_correctness(judge, question, answer, item.expected_answer)
    else:
        facts = json.dumps(
            {
                "answered_by": rec.get("answered_by"),
                "delegated_to_forum": rec.get("delegated"),
                "external_sources": [
                    s["url"] for s in rec.get("sources", []) if s["kind"] != "doc"
                ],
                "doc_sources": len([s for s in rec.get("sources", []) if s["kind"] == "doc"]),
                "nodes": rec.get("nodes"),
            },
            ensure_ascii=False,
        )
        tasks["behaviour"] = judge_behaviour(judge, question, answer, item.expected_answer, facts)
    names = list(tasks)
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    for name, res in zip(names, results, strict=True):
        if isinstance(res, BaseException):
            log.warning("judge %s failed on %s: %s", name, item.id, res)
            out[name] = {"error": str(res)[:300]}
            continue
        if name == "faithfulness":
            score, v = res
            out[name] = {
                "score": rnd(score),
                "n_claims": len(v.claims),
                "unsupported": [c.claim for c in v.claims if not c.supported],
            }
        elif name == "relevancy":
            score, v = res
            out[name] = {
                "score": rnd(score),
                "noncommittal": v.noncommittal,
                "questions": v.questions,
            }
        elif name == "correctness":
            scores, v = res
            out[name] = {
                **{k: rnd(x) if isinstance(x, float) else x for k, x in scores.items()},
                "fp_claims": v.fp,
                "fn_claims": v.fn,
            }
        else:
            out[name] = {"passed": res.passed, "reason": res.reason}
    return out


def judge_failed(rec: dict[str, Any]) -> bool:
    """A previous judge call failed (API error, credit, unparsable): judge this run again."""
    judges = rec.get("judges") or {}
    return "error" in judges or any(isinstance(v, dict) and "error" in v for v in judges.values())


# ------------------------------------------------------------------------------ E-07 evidence
async def node_evidence(
    client: AgentClient,
    items: Sequence[GoldenItem],
    per_question: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Retrieval with the raw question vs the query the graph actually used.

    - contextualize: follow-up turn >= 2, raw question vs `standalone_question`;
    - rewriter: items where the rewriter ran, original vs last rewritten query.
    """
    contextualize: list[dict[str, Any]] = []
    rewriter: list[dict[str, Any]] = []
    for item in items:
        rec = per_question.get(item.id, {}).get("runs", {}).get("agentic", {})
        if not item.relevant_sections or "error" in rec or not rec:
            continue
        if item.is_follow_up_turn and rec.get("standalone_question"):
            raw = await search_metrics(client, item.question, item.section_keys)
            standalone = await search_metrics(client, rec["standalone_question"], item.section_keys)
            contextualize.append(
                {
                    "id": item.id,
                    "standalone_question": rec["standalone_question"],
                    "raw": {k: raw[k] for k in ("recall@10", "rr")},
                    "standalone": {k: standalone[k] for k in ("recall@10", "rr")},
                }
            )
        queries = [q for q in rec.get("rewritten_queries", []) if q]
        if queries:
            base = rec.get("standalone_question") or item.question
            before = await search_metrics(client, base, item.section_keys)
            after = await search_metrics(client, queries[-1], item.section_keys)
            rewriter.append(
                {
                    "id": item.id,
                    "expects_rewrite": item.expects_rewrite,
                    "rewritten": queries[-1],
                    "before": {k: before[k] for k in ("recall@10", "rr")},
                    "after": {k: after[k] for k in ("recall@10", "rr")},
                }
            )
    return {"contextualize": contextualize, "rewriter": rewriter}


# ------------------------------------------------------------------------------ main
def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    p.add_argument("--only", type=lambda s: [x.strip() for x in s.split(",") if x.strip()])
    p.add_argument("--modes", default=",".join(MODES))
    p.add_argument("--concurrency", type=int, default=3)
    p.add_argument("--judge-concurrency", type=int, default=4)
    p.add_argument("--no-judges", action="store_true", help="skip the LLM judges")
    p.add_argument("--no-queries", action="store_true", help="retrieval and HNSW only")
    p.add_argument("--no-hnsw", action="store_true")
    p.add_argument("--from-report", type=Path, help="reuse answers/judges of a report")
    p.add_argument("--rejudge", action="store_true", help="with --from-report: judge again")
    p.add_argument("--out-dir", type=Path, default=REPORTS_DIR)
    p.add_argument("--label", default="")
    p.add_argument("--validate-only", action="store_true", help="load the golden set and exit")
    return p.parse_args(argv)


def run_meta(settings: Settings, args: argparse.Namespace, golden: GoldenSet) -> dict[str, Any]:
    roles = (
        "contextualizer",
        "router",
        "grader",
        "rewriter",
        "direct",
        "generator",
        "research",
        "judge",
    )
    return {
        "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_sha": os.environ.get("GIT_SHA", "unknown"),
        "label": args.label,
        "golden_counts": golden.counts(),
        "models": {r: model_name_for(r, settings) for r in roles},  # type: ignore[arg-type]
        "settings": {
            "retriever_top_k": settings.retriever_top_k,
            "max_rewrites": settings.max_rewrites,
            "qdrant_hnsw_ef": settings.qdrant_hnsw_ef,
            "embeddings_model": settings.embeddings_model,
            "hitl_enabled": settings.hitl_enabled,
            "retriever": settings.retriever,
            "reranker": settings.reranker,
        },
    }


async def amain(args: argparse.Namespace) -> int:
    golden = load_golden(args.golden)
    log.info("golden set OK: %s", golden.counts())
    if args.validate_only:
        return 0
    settings = get_settings()
    items = select_items(golden, args.only)
    modes = [m for m in args.modes.split(",") if m]
    previous: dict[str, Any] = (
        json.loads(args.from_report.read_text(encoding="utf-8")) if args.from_report else {}
    )
    prev_q = {q["id"]: q for q in previous.get("per_question", [])}

    client = AgentClient(settings.agent_url)
    qdrant = AsyncQdrantClient(url=settings.qdrant_url, timeout=60)
    embedder = TEIEmbedder.from_settings(settings)
    judge = Judge(
        get_chat_model("judge", settings),
        model_name_for("judge", settings),
        concurrency=args.judge_concurrency,
    )
    tag = datetime.now(UTC).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:4]
    try:
        log.info("retrieval via /search (ES vs EN) on %d items", len(retrieval_items(items)))
        crosslingual = await run_crosslingual(client, retrieval_items(items))

        hnsw: dict[str, Any] | None = previous.get("hnsw_vs_exact")
        if not args.no_hnsw:
            queries = [q for i in items for q in (i.question, i.question_en)]
            log.info("HNSW vs exact on %d queries", len(queries))
            hnsw = await run_hnsw_vs_exact(qdrant, embedder, settings.qdrant_collection, queries)

        per_question: dict[str, dict[str, Any]] = {
            i.id: {
                "id": i.id,
                "category": i.category,
                "question": i.question,
                "expected_agent": i.expected_agent,
                "expects_rewrite": i.expects_rewrite,
                "thread": i.thread,
                "turn": i.turn,
                "retrieval": crosslingual.get(i.id),
                "runs": {},
            }
            for i in items
        }
        if not args.no_queries:
            for mode in modes:
                if args.from_report:
                    for i in items:
                        run = prev_q.get(i.id, {}).get("runs", {}).get(mode)
                        if run is not None:
                            per_question[i.id]["runs"][mode] = run
                    continue
                log.info("POST /query mode=%s on %d items", mode, len(items))
                responses = await run_queries(client, items, mode, tag, args.concurrency)
                for i in items:
                    per_question[i.id]["runs"][mode] = run_record(i, responses[i.id])

            if not args.no_judges:
                jobs = []
                for i in items:
                    for mode, rec in per_question[i.id]["runs"].items():
                        if rec.get("judges") and not args.rejudge and not judge_failed(rec):
                            continue
                        jobs.append((i, mode, rec))
                log.info("judging %d answers with %s", len(jobs), judge.model_name)

                async def run_job(i: GoldenItem, mode: str, rec: dict[str, Any]) -> None:
                    try:
                        rec["judges"] = await judge_run(
                            judge, embedder, qdrant, settings.qdrant_collection, golden, i, rec
                        )
                    except JudgeError as exc:
                        rec["judges"] = {"error": str(exc)}

                await asyncio.gather(*(run_job(*j) for j in jobs))

        evidence = await node_evidence(client, items, per_question) if not args.no_queries else {}
        report = build_report(
            meta=run_meta(settings, args, golden),
            items=items,
            per_question=list(per_question.values()),
            hnsw=hnsw,
            evidence=evidence,
            judge_usage=judge.usage.as_dict(),
            previous_judge_usage=previous.get("run_meta", {}).get("judge_usage"),
        )
    finally:
        await client.aclose()
        await qdrant.close()
        await embedder.aclose()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    body = json.dumps(report, ensure_ascii=False, indent=2)
    (args.out_dir / f"{stamp}.json").write_text(body, encoding="utf-8")
    (args.out_dir / "latest.json").write_text(body, encoding="utf-8")
    (args.out_dir / "latest.md").write_text(render_markdown(report), encoding="utf-8")
    (args.out_dir / "dashboard.json").write_text(
        json.dumps(dashboard_view(report), ensure_ascii=False, indent=1), encoding="utf-8"
    )
    log.info("report: %s (judge cost $%.4f)", args.out_dir / f"{stamp}.json", judge.usage.cost_usd)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    for noisy in ("httpx", "httpcore", "anthropic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return asyncio.run(amain(parse_args(argv)))


if __name__ == "__main__":
    sys.exit(main())
