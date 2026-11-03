"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, TableWrap, td, th } from "./Card";
import { ms, score } from "./format";
import type { EvalReport, RankingAggregate } from "./types";

const tooltipStyle = { borderRadius: 8, border: "1px solid var(--line)", fontSize: 12, color: "var(--ink)" };

function Ranking({ es, en }: { es: RankingAggregate; en: RankingAggregate }) {
  const rows: { label: string; key: keyof RankingAggregate }[] = [
    { label: "Recall@1", key: "recall@1" },
    { label: "Recall@5", key: "recall@5" },
    { label: "Recall@10", key: "recall@10" },
    { label: "Precision@5", key: "precision@5" },
    { label: "MRR", key: "mrr" },
    { label: "Context precision@10", key: "context_precision@10" },
  ];
  return (
    <Card title="Recuperación y cross-lingual (E-09)" subtitle={`/search top 10 sobre ${es.n} preguntas con secciones etiquetadas: pregunta original en español vs traducción manual al inglés.`}>
      <TableWrap label="Recuperación español vs inglés">
        <thead>
          <tr>
            <th className={th} scope="col">Métrica</th>
            <th className={th} scope="col">Español</th>
            <th className={th} scope="col">Inglés</th>
            <th className={th} scope="col">Δ (EN − ES)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const a = es[r.key] as number | null;
            const b = en[r.key] as number | null;
            const d = a !== null && b !== null ? b - a : null;
            return (
              <tr key={r.label}>
                <th scope="row" className={`${td} font-normal text-ink-muted`}>{r.label}</th>
                <td className={td}>{score(a)}</td>
                <td className={td}>{score(b)}</td>
                <td className={td}>{d === null ? "—" : `${d > 0 ? "+" : ""}${score(d)}`}</td>
              </tr>
            );
          })}
        </tbody>
      </TableWrap>
    </Card>
  );
}

function Hnsw({ data }: { data: NonNullable<EvalReport["hnsw_vs_exact"]> }) {
  const c = data.collection;
  return (
    <Card
      title="HNSW vs búsqueda exacta (V-04)"
      subtitle={`${data.n_queries} consultas, top ${data.top_k}; ${c.points_count} puntos, ${c.indexed_vectors_count} indexados en ${c.segments_count} segmentos (m=${c.m}, ef_construct=${c.ef_construct}). Exacta: p50 ${ms(data.exact.latency_ms_p50)}.`}
    >
      <div className="overflow-x-auto">
      <div className="h-48 min-w-[20rem]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data.hnsw} margin={{ top: 8, right: 16, left: -16, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
            <XAxis dataKey="hnsw_ef" tick={{ fontSize: 11, fill: "var(--ink-muted)" }} axisLine={false} tickLine={false} />
            <YAxis domain={[0.9, 1]} tick={{ fontSize: 11, fill: "var(--ink-muted)" }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle} formatter={(v) => score(Number(v))} labelFormatter={(l) => `hnsw_ef = ${l}`} />
            <Line type="monotone" dataKey="recall@10" name="Recall@10 vs exacta" stroke="var(--chart-agentic)" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 5 }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      </div>
      <TableWrap label="Recall y latencia por hnsw_ef">
        <thead>
          <tr>
            <th className={th} scope="col">hnsw_ef</th>
            <th className={th} scope="col">Recall@10</th>
            <th className={th} scope="col">Mín.</th>
            <th className={th} scope="col">p50</th>
            <th className={th} scope="col">p95</th>
          </tr>
        </thead>
        <tbody>
          {data.hnsw.map((s) => (
            <tr key={s.hnsw_ef}>
              <td className={td}>{s.hnsw_ef}</td>
              <td className={td}>{score(s["recall@10"])}</td>
              <td className={td}>{score(s["min_recall@10"])}</td>
              <td className={td}>{ms(s.latency_ms_p50)}</td>
              <td className={td}>{ms(s.latency_ms_p95)}</td>
            </tr>
          ))}
        </tbody>
      </TableWrap>
    </Card>
  );
}

export default function RetrievalPanel({ report }: { report: EvalReport }) {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {report.retrieval && <Ranking es={report.retrieval.es} en={report.retrieval.en} />}
      {report.hnsw_vs_exact && <Hnsw data={report.hnsw_vs_exact} />}
    </div>
  );
}
