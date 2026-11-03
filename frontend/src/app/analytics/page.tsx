"use client";

import { useEffect, useState } from "react";
import { AppMark, MainNav } from "@/components/chat/Header";
import { Section, StatTile } from "@/components/analytics/Card";
import ModeComparison from "@/components/analytics/ModeComparison";
import NodeCost from "@/components/analytics/NodeCost";
import QuestionsTable from "@/components/analytics/QuestionsTable";
import RetrievalPanel from "@/components/analytics/RetrievalPanel";
import RoutingMatrix from "@/components/analytics/RoutingMatrix";
import { money, pct, score, secs } from "@/components/analytics/format";
import type { EvalReport } from "@/components/analytics/types";

// Written by `make eval` (eval/runners/report.py -> dashboard.json), shipped in public/ (E-12).
const REPORT_URL = "/eval/latest.json";

type State = { status: "loading" } | { status: "error"; message: string } | { status: "ready"; report: EvalReport };

export default function AnalyticsPage() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetch(REPORT_URL, { cache: "no-store" })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<EvalReport>;
      })
      .then((report) => !cancelled && setState({ status: "ready", report }))
      .catch((e: unknown) => !cancelled && setState({ status: "error", message: e instanceof Error ? e.message : String(e) }));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex min-h-screen flex-col bg-surface">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-background px-4 py-3.5 sm:px-6">
        <AppMark />
        <MainNav current="analytics" />
        <span className="hidden w-40 sm:block" aria-hidden="true" />
      </header>
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-10 px-4 py-8 sm:px-6">
        {state.status === "loading" && <p className="text-sm text-ink-muted" role="status">Cargando resultados de la evaluación…</p>}
        {state.status === "error" && (
          <div role="alert" className="rounded-xl border border-danger bg-danger-soft p-5 text-sm text-danger">
            No se encontró el reporte de evaluación ({state.message}). Ejecuta <code className="font-mono">make eval</code> y reconstruye el frontend.
          </div>
        )}
        {state.status === "ready" && <Report report={state.report} />}
      </main>
    </div>
  );
}

function Report({ report }: { report: EvalReport }) {
  const meta = report.run_meta;
  const routing = report.routing.agentic;
  const agentic = report.aggregates.agentic;
  const f1 = report.comparison.paired_docs_questions?.correctness_f1;
  const started = new Date(meta.started_at).toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });

  return (
    <>
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold text-ink">Evaluación del asistente</h1>
        <p className="max-w-3xl text-sm text-ink-muted">
          Golden set de {meta.n_items} preguntas en español ({Object.entries(meta.golden_counts).map(([k, v]) => `${v} ${k}`).join(", ")}), cada una
          por <code className="font-mono">POST /query</code> en modo agéntico y lineal. Juez: {meta.models.judge}. Corrida del {started} (git{" "}
          <code className="font-mono">{meta.git_sha}</code>). Muestra pequeña: leer los promedios junto con su <em>n</em>.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile
          label="Supervisor (E-04)"
          value={pct(routing?.final_agent.accuracy)}
          detail={routing ? `${routing.final_agent.correct}/${routing.final_agent.n} con el agente esperado` : undefined}
        />
        <StatTile
          label="Recall@10 · MRR"
          value={`${score(report.retrieval?.es["recall@10"])} · ${score(report.retrieval?.es.mrr)}`}
          detail="/search, pregunta en español"
        />
        <StatTile
          label="Corrección F1"
          value={`${score(f1?.agentic)} vs ${score(f1?.linear)}`}
          detail={`agéntico vs lineal, pareado sobre ${f1?.n ?? 0} preguntas juzgadas en ambos modos`}
        />
        <StatTile
          label="Costo de la corrida"
          value={money(report.costs.total_usd)}
          detail={`agente ${money((report.costs.agent_usd.agentic ?? 0) + (report.costs.agent_usd.linear ?? 0))} · juez ${money(report.costs.judge_usd)} · p50 agéntico ${secs(agentic?.all?.latency_ms.p50)}`}
        />
      </div>

      <Section id="modes" title="Lineal vs agéntico (E-05)" subtitle="Mismas preguntas, mismo retriever y generator: solo cambia la orquestación. En modo agéntico el contexto medido es el que deja el grader.">
        <ModeComparison report={report} />
      </Section>

      {routing && (
        <Section id="routing" title="Precisión del supervisor (E-04)">
          <RoutingMatrix routing={routing.final_agent} routerAccuracy={routing.router_decision.accuracy} />
        </Section>
      )}

      <Section id="retrieval" title="Recuperación">
        <RetrievalPanel report={report} />
      </Section>

      {report.per_node.agentic && (
        <Section id="nodes" title="Costo por nodo">
          <NodeCost nodes={report.per_node.agentic} />
        </Section>
      )}

      <Section id="questions" title="Preguntas">
        <QuestionsTable rows={report.per_question} />
      </Section>
    </>
  );
}
