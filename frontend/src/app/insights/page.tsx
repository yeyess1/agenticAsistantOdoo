"use client";

import { useEffect, useState } from "react";
import { AppMark, MainNav } from "@/components/chat/Header";
import { Card, Section, StatTile, TableWrap, td, th } from "@/components/analytics/Card";
import { AGENT_LABEL, money, pct, secs, tokens } from "@/components/analytics/format";
import { BarList, Empty, Segmented, TokenHistogram } from "@/components/insights/charts";
import { errorMessage, getInsights, type InsightsFilters, type InsightsResponse } from "@/lib/api/client";

// Live: GET /insights aggregates query_log (one row per answered turn; `make insights-backfill`
// loads the turns already in the LangGraph checkpoints).
type Origin = "all" | "ui" | "eval";
type ModeFilter = "all" | "agentic" | "linear";
type Gram = "terms" | "bigrams" | "trigrams";
type DocMetric = "retrieved" | "cited";
type Result = { key: string } & ({ status: "error"; message: string } | { status: "ready"; data: InsightsResponse });

const TOPIC_LABEL: Record<string, string> = {
  orm: "ORM y modelos",
  views: "Vistas",
  frontend: "Frontend / OWL",
  security: "Seguridad",
  api: "API y controladores",
  reports: "Reportes",
  modules: "Módulos y datos",
  actions: "Acciones y menús",
  testing: "Testing",
  upgrades: "Migraciones",
  performance: "Rendimiento",
  general: "General",
};
const topicLabel = (t?: string | null) => (t ? (TOPIC_LABEL[t] ?? t) : "—");
const int = new Intl.NumberFormat("es-CO");

export default function InsightsPage() {
  const [origin, setOrigin] = useState<Origin>("all");
  const [mode, setMode] = useState<ModeFilter>("all");
  const [result, setResult] = useState<Result | null>(null);
  const key = `${origin}|${mode}`;
  // Loading = no result yet for the current filters (no setState inside the effect body).
  const state = result?.key === key ? result : ({ status: "loading" } as const);

  useEffect(() => {
    const ctrl = new AbortController();
    const filters: InsightsFilters = {
      origin: origin === "all" ? undefined : origin,
      mode: mode === "all" ? undefined : mode,
    };
    getInsights(filters, ctrl.signal)
      .then((data) => setResult({ key, status: "ready", data }))
      .catch((e: unknown) => !ctrl.signal.aborted && setResult({ key, status: "error", message: errorMessage(e) }));
    return () => ctrl.abort();
  }, [origin, mode, key]);

  return (
    <div className="flex min-h-screen flex-col bg-surface">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-background px-4 py-3.5 sm:px-6">
        <AppMark />
        <MainNav current="insights" />
        <span className="hidden w-40 sm:block" aria-hidden="true" />
      </header>
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-10 px-4 py-8 sm:px-6">
        <div className="flex flex-col gap-3">
          <h1 className="text-2xl font-semibold text-ink">Uso del asistente</h1>
          <p className="max-w-3xl text-sm text-ink-muted">
            NLP básico sobre cada turno respondido: n-gramas de palabras de contenido (sin stopwords, sin tildes), tópico por léxico de palabras clave más la sección
            de los documentos recuperados, y longitud de la respuesta en tokens de salida del nodo que responde.
          </p>
          <div className="flex flex-wrap gap-2">
            <Segmented<Origin>
              label="Origen"
              value={origin}
              onChange={setOrigin}
              options={[
                { value: "all", label: "Todo" },
                { value: "ui", label: "Chat" },
                { value: "eval", label: "Evaluación" },
              ]}
            />
            <Segmented<ModeFilter>
              label="Modo"
              value={mode}
              onChange={setMode}
              options={[
                { value: "all", label: "Ambos" },
                { value: "agentic", label: "Agéntico" },
                { value: "linear", label: "Lineal" },
              ]}
            />
          </div>
        </div>
        {state.status === "loading" && <p className="text-sm text-ink-muted" role="status">Cargando…</p>}
        {state.status === "error" && (
          <div role="alert" className="rounded-xl border border-danger bg-danger-soft p-5 text-sm text-danger">
            No se pudieron cargar los datos ({state.message}).
          </div>
        )}
        {state.status === "ready" && (state.data.totals.turns === 0 ? <Empty>Aún no hay turnos registrados para este filtro.</Empty> : <Insights data={state.data} />)}
      </main>
    </div>
  );
}

function Insights({ data }: { data: InsightsResponse }) {
  const t = data.totals;
  const [gram, setGram] = useState<Gram>("bigrams");
  const range = t.first_at && t.last_at ? `${fmtDate(t.first_at)} – ${fmtDate(t.last_at)}` : "";
  const agents = Object.entries(t.by_agent)
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `${AGENT_LABEL[k as keyof typeof AGENT_LABEL] ?? k} ${v}`)
    .join(" · ");
  const phrases = data[gram];
  const [docMetric, setDocMetric] = useState<DocMetric>("retrieved");
  const topDocs = [...data.documents].sort((a, b) => b[docMetric] - a[docMetric] || b.retrieved + b.cited - (a.retrieved + a.cited)).slice(0, 5);

  return (
    <>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Turnos" value={int.format(t.turns)} detail={`${range}${range ? " · " : ""}${agents}`} />
        <StatTile label="Respuesta media" value={`${tokens(t.answer_tokens_mean)} tokens`} detail={`mediana ${tokens(t.answer_tokens_p50)} · ~${tokens(t.answer_chars_mean)} caracteres`} />
        <StatTile label="Latencia p50" value={secs(t.latency_ms_p50)} detail={`sin contexto ${pct(t.no_context_rate)}`} />
        <StatTile label="Costo acumulado" value={money(t.cost_usd_total)} detail={Object.entries(t.by_origin).map(([k, v]) => `${k === "ui" ? "chat" : "evaluación"} ${v}`).join(" · ")} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Distribución por tópico" subtitle="Turnos por tópico; el tooltip muestra la longitud media de la respuesta.">
          <BarList
            labelWidth={140}
            data={data.topics.map((s) => ({
              label: topicLabel(s.topic),
              value: s.count,
              detail: `${pct(s.share)} · ${tokens(s.answer_tokens_mean)} tokens de respuesta`,
            }))}
            unit=" turnos"
          />
        </Card>
        <Card title="Frases más frecuentes" subtitle="Cada frase cuenta una vez por pregunta. Bigramas y trigramas con al menos 2 apariciones.">
          <Segmented<Gram>
            label="N-grama"
            value={gram}
            onChange={setGram}
            options={[
              { value: "terms", label: "Términos" },
              { value: "bigrams", label: "Bigramas" },
              { value: "trigrams", label: "Trigramas" },
            ]}
          />
          <BarList data={phrases.slice(0, 15).map((p) => ({ label: p.text, value: p.count }))} unit=" preguntas" />
        </Card>
      </div>

      <Section id="answers" title="Longitud de las respuestas" subtitle="Tokens de salida del nodo que redacta la respuesta (generator, direct_answer o research_llm), en tramos de 100.">
        <Card>
          <TokenHistogram bins={data.answer_tokens_hist} />
        </Card>
      </Section>

      <Section id="documents" title="Documentos más consultados" subtitle="Top 5. Recuperado: turnos en los que el documento llegó al contexto. Citado: turnos en los que la respuesta lo citó con [n]. Ambos cuentan una vez por turno.">
        <Card>
          <Segmented<DocMetric>
            label="Métrica"
            value={docMetric}
            onChange={setDocMetric}
            options={[
              { value: "retrieved", label: "Recuperado" },
              { value: "cited", label: "Citado" },
            ]}
          />
          <BarList
            labelWidth={230}
            unit=" turnos"
            data={topDocs.map((d) => ({
              label: shorten(d.title, 34),
              value: d[docMetric],
              detail: `${d.title} · ${topicLabel(d.topic)} · ${docMetric === "retrieved" ? `citado ${d.cited}` : `recuperado ${d.retrieved}`}`,
            }))}
          />
        </Card>
      </Section>

      <Section id="questions" title="Preguntas más repetidas" subtitle="Agrupadas por sus palabras de contenido (sin importar orden, tildes ni signos).">
        <Card>
          <TableWrap label="Preguntas más repetidas">
            <thead>
              <tr>
                <th className={th}>Pregunta</th>
                <th className={th}>Tópico</th>
                <th className={`${th} text-right`}>Veces</th>
              </tr>
            </thead>
            <tbody>
              {data.questions.map((q) => (
                <tr key={q.question}>
                  <td className={`${td} max-w-xl`}>{q.question}</td>
                  <td className={`${td} whitespace-nowrap text-ink-muted`}>{topicLabel(q.topic)}</td>
                  <td className={`${td} text-right`}>{q.count}</td>
                </tr>
              ))}
            </tbody>
          </TableWrap>
        </Card>
      </Section>
    </>
  );
}

function shorten(text: string, max: number): string {
  const clean = text.replace(/ — Odoo [\d.]+ documentation$/, "");
  return clean.length > max ? `${clean.slice(0, max - 1)}…` : clean;
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("es-CO", { day: "numeric", month: "short" });
}
