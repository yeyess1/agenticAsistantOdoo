"""Report assembly (E-12): aggregates per mode and category, routing, per-node cost,
retrieval, HNSW and the Markdown tables for the README.

JSON layout (ARCHITECTURE §12): `{run_meta, per_question, aggregates: {agentic, linear},
routing, retrieval, crosslingual, hnsw_vs_exact, node_evidence, per_node, costs}`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from metrics.routing import routing_report
from metrics.stats import mean, percentile, rnd, summary

from runners.crosslingual import summarize_crosslingual
from runners.golden import GoldenItem

SCOPES: dict[str, tuple[str, ...]] = {
    "all": ("covered", "not_covered", "out_of_scope", "follow_up"),
    "docs_questions": ("covered", "follow_up"),
    "covered": ("covered",),
    "follow_up": ("follow_up",),
    "not_covered": ("not_covered",),
    "out_of_scope": ("out_of_scope",),
}


def _judge(rec: dict[str, Any], metric: str, field: str) -> Any:
    value = (rec.get("judges") or {}).get(metric) or {}
    return value.get(field) if isinstance(value, dict) else None


def aggregate_runs(runs: Sequence[dict[str, Any]]) -> dict[str, Any]:
    ok = [r for r in runs if "error" not in r]
    behaviour = [_judge(r, "behaviour", "passed") for r in ok]
    behaviour_vals = [b for b in behaviour if b is not None]
    latency = [r.get("client_latency_ms") for r in ok]
    return {
        "n": len(runs),
        "errors": len(runs) - len(ok),
        "faithfulness": summary(_judge(r, "faithfulness", "score") for r in ok),
        "answer_relevancy": summary(_judge(r, "relevancy", "score") for r in ok),
        "correctness_f1": summary(_judge(r, "correctness", "f1") for r in ok),
        "correctness_precision": rnd(mean(_judge(r, "correctness", "precision") for r in ok)),
        "correctness_recall": rnd(mean(_judge(r, "correctness", "recall") for r in ok)),
        "behaviour_pass_rate": rnd(sum(behaviour_vals) / len(behaviour_vals))
        if behaviour_vals
        else None,
        "behaviour_n": len(behaviour_vals),
        "context_precision": rnd(mean(r["context"]["context_precision"] for r in ok)),
        "context_recall": rnd(mean(r["context"]["context_recall"] for r in ok)),
        "context_chunks": rnd(mean(r["context"]["n_chunks"] for r in ok), 2),
        "citation_correctness": rnd(mean(r.get("citation_correctness") for r in ok)),
        "latency_ms": {k: rnd(v, 0) for k, v in summary(latency).items()},
        "input_tokens": rnd(mean(r["usage"].get("input_tokens") for r in ok), 0),
        "output_tokens": rnd(mean(r["usage"].get("output_tokens") for r in ok), 0),
        "generator_input_tokens": rnd(
            mean((r.get("generator_usage") or {}).get("input_tokens") for r in ok), 0
        ),
        "cost_usd_mean": rnd(mean(r["usage"].get("cost_usd") for r in ok), 5),
        "cost_usd_total": rnd(sum(r["usage"].get("cost_usd", 0.0) for r in ok), 4),
    }


def _rounded_summary(values: Any) -> dict[str, Any]:
    return {k: rnd(v) if isinstance(v, float) else v for k, v in summary(values).items()}


def aggregates(per_question: Sequence[dict[str, Any]], mode: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for scope, cats in SCOPES.items():
        runs = [
            q["runs"][mode] for q in per_question if q["category"] in cats and mode in q["runs"]
        ]
        if runs:
            agg = aggregate_runs(runs)
            for key in ("faithfulness", "answer_relevancy", "correctness_f1"):
                agg[key] = {k: rnd(v) if isinstance(v, float) else v for k, v in agg[key].items()}
            out[scope] = agg
    return out


def routing(per_question: Sequence[dict[str, Any]], mode: str) -> dict[str, Any] | None:
    rows = [q for q in per_question if mode in q["runs"]]
    if not rows:
        return None
    expected = [q["expected_agent"] for q in rows]
    final = routing_report(expected, [q["runs"][mode].get("answered_by") for q in rows])
    router = routing_report(expected, [q["runs"][mode].get("route") for q in rows])
    errors = [
        {
            "id": q["id"],
            "expected": q["expected_agent"],
            "answered_by": q["runs"][mode].get("answered_by"),
            "route": q["runs"][mode].get("route"),
            "delegated": q["runs"][mode].get("delegated"),
        }
        for q in rows
        if q["runs"][mode].get("answered_by") != q["expected_agent"]
    ]
    return {"final_agent": final, "router_decision": router, "errors": errors}


def per_node(per_question: Sequence[dict[str, Any]], mode: str) -> dict[str, Any]:
    nodes: dict[str, list[dict[str, Any]]] = {}
    total_cost = 0.0
    for q in per_question:
        run = q["runs"].get(mode)
        if not run or "error" in run:
            continue
        for s in run.get("steps", []):
            nodes.setdefault(s["node"], []).append(s)
            total_cost += s.get("cost_usd") or 0.0
    out: dict[str, Any] = {}
    for node, steps in nodes.items():
        cost = sum(s.get("cost_usd") or 0.0 for s in steps)
        out[node] = {
            "calls": len(steps),
            "duration_ms_mean": rnd(mean(s["duration_ms"] for s in steps), 0),
            "duration_ms_p95": rnd(percentile([s["duration_ms"] for s in steps], 95), 0),
            "input_tokens_mean": rnd(mean(s["input_tokens"] for s in steps), 0),
            "output_tokens_mean": rnd(mean(s["output_tokens"] for s in steps), 0),
            "cost_usd_total": rnd(cost, 4),
            "cost_share": rnd(cost / total_cost, 3) if total_cost else None,
        }
    return dict(sorted(out.items(), key=lambda kv: -(kv[1]["cost_usd_total"] or 0)))


def rewriter_stats(per_question: Sequence[dict[str, Any]]) -> dict[str, Any]:
    rows = [
        q for q in per_question if "agentic" in q["runs"] and "error" not in q["runs"]["agentic"]
    ]
    expected = [q for q in rows if q["expects_rewrite"]]
    return {
        "expects_rewrite_n": len(expected),
        "expects_rewrite_triggered": sorted(
            q["id"] for q in expected if q["runs"]["agentic"]["n_rewrites"] > 0
        ),
        "triggered_without_expectation": sorted(
            q["id"] for q in rows if not q["expects_rewrite"] and q["runs"]["agentic"]["n_rewrites"]
        ),
    }


def retrieval_summary(per_question: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    per_item = {q["id"]: q["retrieval"] for q in per_question if q.get("retrieval")}
    if not per_item:
        return None
    return summarize_crosslingual(per_item)


def comparison(aggs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Agentic minus linear on the headline numbers (E-05)."""
    a, b = aggs.get("agentic", {}), aggs.get("linear", {})
    out: dict[str, Any] = {}
    for scope in ("all", "docs_questions", "not_covered", "out_of_scope"):
        if scope not in a or scope not in b:
            continue
        x, y = a[scope], b[scope]
        out[scope] = {
            "faithfulness": _delta(x["faithfulness"]["mean"], y["faithfulness"]["mean"]),
            "answer_relevancy": _delta(
                x["answer_relevancy"]["mean"], y["answer_relevancy"]["mean"]
            ),
            "correctness_f1": _delta(x["correctness_f1"]["mean"], y["correctness_f1"]["mean"]),
            "behaviour_pass_rate": _delta(x["behaviour_pass_rate"], y["behaviour_pass_rate"]),
            "context_precision": _delta(x["context_precision"], y["context_precision"]),
            "latency_ms_p50": _delta(x["latency_ms"]["p50"], y["latency_ms"]["p50"]),
            "cost_usd_mean": _delta(x["cost_usd_mean"], y["cost_usd_mean"]),
            "input_tokens": _delta(x["input_tokens"], y["input_tokens"]),
        }
    return out


PAIRED_METRICS: tuple[tuple[str, str, str], ...] = (
    ("faithfulness", "faithfulness", "score"),
    ("answer_relevancy", "relevancy", "score"),
    ("correctness_f1", "correctness", "f1"),
)


def paired(per_question: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Judge metrics over the items scored in BOTH modes (fair agentic - linear delta)."""
    out: dict[str, Any] = {}
    for name, metric, field in PAIRED_METRICS:
        pairs = []
        for q in per_question:
            if q["category"] not in SCOPES["docs_questions"]:
                continue
            a = q["runs"].get("agentic", {})
            b = q["runs"].get("linear", {})
            x, y = _judge(a, metric, field), _judge(b, metric, field)
            if x is not None and y is not None:
                pairs.append((q["id"], x, y))
        ma = mean(x for _, x, _ in pairs)
        mb = mean(y for _, _, y in pairs)
        out[name] = {
            "n": len(pairs),
            **_delta(rnd(ma), rnd(mb)),
            "agentic_wins": sum(x > y for _, x, y in pairs),
            "linear_wins": sum(y > x for _, x, y in pairs),
        }
    return out


def _delta(x: float | None, y: float | None) -> dict[str, float | None]:
    return {
        "agentic": x,
        "linear": y,
        "delta": rnd(x - y) if x is not None and y is not None else None,
    }


def merge_usage(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    """Judge usage of a `--from-report` run = the reused verdicts + the new calls."""
    if not previous:
        return current
    out: dict[str, Any] = {}
    for key in ("calls", "failures", "input_tokens", "output_tokens"):
        out[key] = int(previous.get(key, 0)) + int(current.get(key, 0))
    out["cost_usd"] = rnd(
        float(previous.get("cost_usd", 0.0)) + float(current.get("cost_usd", 0.0))
    )
    by_metric: dict[str, float] = {}
    for src in (previous.get("cost_by_metric", {}), current.get("cost_by_metric", {})):
        for k, v in src.items():
            by_metric[k] = round(by_metric.get(k, 0.0) + float(v), 4)
    out["cost_by_metric"] = by_metric
    return out


def build_report(
    *,
    meta: dict[str, Any],
    items: Sequence[GoldenItem],
    per_question: list[dict[str, Any]],
    hnsw: dict[str, Any] | None,
    evidence: dict[str, Any],
    judge_usage: dict[str, Any],
    previous_judge_usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    modes = sorted({m for q in per_question for m in q["runs"]})
    aggs = {m: aggregates(per_question, m) for m in modes}
    agent_cost = {
        m: rnd(
            sum(
                q["runs"][m]["usage"].get("cost_usd", 0.0)
                for q in per_question
                if m in q["runs"] and "error" not in q["runs"][m]
            ),
            4,
        )
        for m in modes
    }
    judge_usage = merge_usage(previous_judge_usage, judge_usage)
    judge_cost = float(judge_usage.get("cost_usd", 0.0))
    meta = {**meta, "n_items": len(items), "modes": modes, "judge_usage": judge_usage}
    return {
        "run_meta": meta,
        "aggregates": aggs,
        "comparison": {**comparison(aggs), "paired_docs_questions": paired(per_question)},
        "routing": {m: routing(per_question, m) for m in modes},
        "rewriter": rewriter_stats(per_question),
        "retrieval": retrieval_summary(per_question),
        "hnsw_vs_exact": hnsw,
        "node_evidence": evidence,
        "per_node": {m: per_node(per_question, m) for m in modes},
        "costs": {
            "agent_usd": agent_cost,
            "judge_usd": rnd(judge_cost, 4),
            "total_usd": rnd(sum(v or 0.0 for v in agent_cost.values()) + judge_cost, 4),
        },
        "per_question": per_question,
    }


# ------------------------------------------------------------------------------ dashboard
def _judge_scores(judges: dict[str, Any] | None) -> dict[str, Any]:
    j = judges or {}

    def get(metric: str, field: str) -> Any:
        value = j.get(metric)
        return value.get(field) if isinstance(value, dict) else None

    return {
        "faithfulness": get("faithfulness", "score"),
        "answer_relevancy": get("relevancy", "score"),
        "correctness_f1": get("correctness", "f1"),
        "behaviour_passed": get("behaviour", "passed"),
    }


def dashboard_view(report: dict[str, Any]) -> dict[str, Any]:
    """Slim copy for the `/analytics` dashboard (U-12): no answers, steps or claim lists."""
    per_question = []
    for q in report["per_question"]:
        runs = {}
        for mode, r in q["runs"].items():
            if "error" in r:
                runs[mode] = {"error": True}
                continue
            runs[mode] = {
                "answered_by": r.get("answered_by"),
                "route": r.get("route"),
                "delegated": r.get("delegated"),
                "n_rewrites": r.get("n_rewrites"),
                "latency_ms": r.get("client_latency_ms"),
                "usage": r.get("usage"),
                "context_precision": r["context"]["context_precision"],
                "context_chunks": r["context"]["n_chunks"],
                "citation_correctness": r.get("citation_correctness"),
                **_judge_scores(r.get("judges")),
            }
        retrieval = q.get("retrieval") or {}
        per_question.append(
            {
                "id": q["id"],
                "category": q["category"],
                "question": q["question"],
                "expected_agent": q["expected_agent"],
                "retrieval": {
                    lang: {k: v.get(k) for k in ("recall@10", "rr")}
                    for lang, v in retrieval.items()
                }
                or None,
                "runs": runs,
            }
        )
    keep = ("run_meta", "aggregates", "comparison", "rewriter", "retrieval", "hnsw_vs_exact")
    out = {k: report.get(k) for k in keep}
    out["routing"] = {
        m: {k: v for k, v in (r or {}).items() if k != "errors"} if r else None
        for m, r in (report.get("routing") or {}).items()
    }
    out["node_evidence"] = report.get("node_evidence")
    out["per_node"] = report.get("per_node")
    out["costs"] = report.get("costs")
    out["per_question"] = per_question
    return out


# ------------------------------------------------------------------------------ markdown
def _f(v: Any, digits: int = 2) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "sí" if v else "no"
    if isinstance(v, float):
        return f"{v:.{digits}f}"
    return str(v)


def render_markdown(report: dict[str, Any]) -> str:
    """Tables for the README (E-12). Spanish, like the rest of the documentation."""
    meta = report["run_meta"]
    lines = [
        f"<!-- generado por runners.run_eval ({meta['started_at']}, git {meta['git_sha']}) -->",
        "",
        "**Lineal vs agéntico (E-05)**: mismas preguntas vía `POST /query`; medias por "
        "pregunta (`n` entre paréntesis).",
        "",
        "| Ámbito | Métrica | Agéntico | Lineal |",
        "|---|---|---|---|",
    ]
    aggs = report["aggregates"]
    a, b = aggs.get("agentic", {}), aggs.get("linear", {})

    def row(scope: str, label: str, getter: Any, digits: int = 2) -> None:
        if scope not in a and scope not in b:
            return
        cells = []
        for agg in (a.get(scope), b.get(scope)):
            if agg is None:
                cells.append("—")
                continue
            value, n = getter(agg)
            cells.append(f"{_f(value, digits)}" + (f" ({n})" if n is not None else ""))
        lines.append(f"| {scope} | {label} | {cells[0]} | {cells[1]} |")

    row(
        "docs_questions",
        "Faithfulness",
        lambda g: (g["faithfulness"]["mean"], g["faithfulness"]["n"]),
    )
    row(
        "docs_questions",
        "Answer relevancy",
        lambda g: (g["answer_relevancy"]["mean"], g["answer_relevancy"]["n"]),
    )
    row(
        "docs_questions",
        "Answer correctness (F1)",
        lambda g: (g["correctness_f1"]["mean"], g["correctness_f1"]["n"]),
    )
    row("docs_questions", "Context precision", lambda g: (g["context_precision"], None))
    row("docs_questions", "Context recall (secciones)", lambda g: (g["context_recall"], None))
    row("docs_questions", "Chunks al generator", lambda g: (g["context_chunks"], None), 1)
    row("docs_questions", "Corrección de citas", lambda g: (g["citation_correctness"], None))
    row(
        "not_covered",
        "Comportamiento esperado (juez)",
        lambda g: (g["behaviour_pass_rate"], g["behaviour_n"]),
    )
    row(
        "out_of_scope",
        "Comportamiento esperado (juez)",
        lambda g: (g["behaviour_pass_rate"], g["behaviour_n"]),
    )
    row("all", "Latencia p50 (s)", lambda g: (_s(g["latency_ms"]["p50"]), None), 1)
    row("all", "Latencia p95 (s)", lambda g: (_s(g["latency_ms"]["p95"]), None), 1)
    row("all", "Tokens de entrada (media)", lambda g: (g["input_tokens"], None), 0)
    row("all", "Tokens de salida (media)", lambda g: (g["output_tokens"], None), 0)
    row("all", "Costo por pregunta (USD)", lambda g: (g["cost_usd_mean"], None), 4)
    row("all", "Costo total (USD)", lambda g: (g["cost_usd_total"], None), 3)

    pq = (report.get("comparison") or {}).get("paired_docs_questions")
    if pq:
        parts = [
            f"{label} {_f(pq[k]['agentic'])} vs {_f(pq[k]['linear'])} "
            f"(n={pq[k]['n']}, gana agéntico {pq[k]['agentic_wins']}, "
            f"lineal {pq[k]['linear_wins']})"
            for k, label in (
                ("faithfulness", "faithfulness"),
                ("answer_relevancy", "relevancy"),
                ("correctness_f1", "correctness F1"),
            )
        ]
        lines += ["", "Pareado (solo preguntas juzgadas en ambos modos): " + "; ".join(parts) + "."]

    rt = (report.get("routing") or {}).get("agentic")
    if rt:
        fa = rt["final_agent"]
        lines += [
            "",
            f"**Supervisor (E-04)**: agente final correcto en {fa['correct']}/{fa['n']} "
            f"(accuracy {_f(fa['accuracy'])}); decisión del router "
            f"{_f(rt['router_decision']['accuracy'])}.",
            "",
            "| Esperado \\ Obtenido | docs | research | direct | ninguno | Recall |",
            "|---|---|---|---|---|---|",
        ]
        for label in fa["labels"]:
            c = fa["confusion"][label]
            lines.append(
                f"| {label} | {c['docs']} | {c['research']} | {c['direct']} | {c['none']} | "
                f"{_f(fa['per_class'][label]['recall'])} |"
            )
    ret = report.get("retrieval")
    if ret:
        es, en = ret["es"], ret["en"]
        lines += [
            "",
            f"**Recuperación (`/search`, top 10, n={es['n']}) y cross-lingual (E-09)**",
            "",
            "| Consulta | Recall@1 | Recall@5 | Recall@10 | Precision@5 | MRR | Context prec.@10 |",
            "|---|---|---|---|---|---|---|",
        ]
        for name, g in (("Español (original)", es), ("Inglés (`question_en`)", en)):
            lines.append(
                f"| {name} | {_f(g['recall@1'])} | {_f(g['recall@5'])} | {_f(g['recall@10'])} | "
                f"{_f(g['precision@5'])} | {_f(g['mrr'])} | {_f(g['context_precision@10'])} |"
            )
    hn = report.get("hnsw_vs_exact")
    if hn:
        col = hn["collection"]
        lines += [
            "",
            f"**HNSW vs exacto (V-04)**: {hn['n_queries']} consultas, top {hn['top_k']}, "
            f"{col['points_count']} puntos ({col['indexed_vectors_count']} indexados en HNSW, "
            f"{col['segments_count']} segmentos, m={col['m']}, "
            f"ef_construct={col['ef_construct']}). "
            f"Exacto: p50 {_f(hn['exact']['latency_ms_p50'])} ms, p95 "
            f"{_f(hn['exact']['latency_ms_p95'])} ms.",
            "",
            "| hnsw_ef | Recall@1 | Recall@5 | Recall@10 | Recall@10 mín. | p50 (ms) | p95 (ms) |",
            "|---|---|---|---|---|---|---|",
        ]
        for s in hn["hnsw"]:
            lines.append(
                f"| {s['hnsw_ef']} | {_f(s['recall@1'], 3)} | {_f(s['recall@5'], 3)} | "
                f"{_f(s['recall@10'], 3)} | {_f(s['min_recall@10'], 2)} | "
                f"{_f(s['latency_ms_p50'])} | {_f(s['latency_ms_p95'])} |"
            )
    nodes = (report.get("per_node") or {}).get("agentic")
    if nodes:
        lines += [
            "",
            "**Costo por nodo (agéntico)**",
            "",
            "| Nodo | Llamadas | Duración media (ms) | Tokens entrada | Costo (USD) | % costo |",
            "|---|---|---|---|---|---|",
        ]
        for node, s in nodes.items():
            share = s["cost_share"]
            lines.append(
                f"| {node} | {s['calls']} | {_f(s['duration_ms_mean'], 0)} | "
                f"{_f(s['input_tokens_mean'], 0)} | {_f(s['cost_usd_total'], 4)} | "
                f"{_f(share * 100 if share is not None else None, 1)} |"
            )
    costs = report["costs"]
    agent = ", ".join(f"{m} ${_f(v, 3)}" for m, v in costs["agent_usd"].items())
    lines += [
        "",
        f"Costo de la corrida: agente {agent}; "
        f"juez ${_f(costs['judge_usd'], 3)}; total ${_f(costs['total_usd'], 3)}.",
        "",
    ]
    return "\n".join(lines)


def _s(ms: float | None) -> float | None:
    return None if ms is None else ms / 1000
