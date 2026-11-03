"use client";

import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, LegendItem, TableWrap, td, th } from "./Card";
import { MODE_LABEL, SERIES_COLOR, money, pct, score, secs, tokens } from "./format";
import type { EvalReport, ScopeAggregate } from "./types";

type Row = { metric: string; agentic: number | null; linear: number | null };

function qualityRows(a?: ScopeAggregate, l?: ScopeAggregate): Row[] {
  const pick = (f: (g: ScopeAggregate) => number | null) => ({ agentic: a ? f(a) : null, linear: l ? f(l) : null });
  return [
    { metric: "Faithfulness", ...pick((g) => g.faithfulness.mean) },
    { metric: "Relevancy", ...pick((g) => g.answer_relevancy.mean) },
    { metric: "Correctness F1", ...pick((g) => g.correctness_f1.mean) },
    { metric: "Context precision", ...pick((g) => g.context_precision) },
    { metric: "Citas correctas", ...pick((g) => g.citation_correctness) },
  ];
}

const tooltipStyle = { borderRadius: 8, border: "1px solid var(--line)", fontSize: 12, color: "var(--ink)" };

export default function ModeComparison({ report }: { report: EvalReport }) {
  const a = report.aggregates.agentic;
  const l = report.aggregates.linear;
  const rows = qualityRows(a?.docs_questions, l?.docs_questions);
  const n = a?.docs_questions?.n ?? l?.docs_questions?.n ?? 0;

  const costRows: { label: string; get: (g?: ScopeAggregate) => string }[] = [
    { label: "Latencia p50", get: (g) => secs(g?.latency_ms.p50) },
    { label: "Latencia p95", get: (g) => secs(g?.latency_ms.p95) },
    { label: "Tokens de entrada (media)", get: (g) => tokens(g?.input_tokens) },
    { label: "Tokens de salida (media)", get: (g) => tokens(g?.output_tokens) },
    { label: "Tokens de entrada al generator", get: (g) => tokens(g?.generator_input_tokens) },
    { label: "Costo por pregunta", get: (g) => money(g?.cost_usd_mean) },
    { label: "Costo total", get: (g) => money(g?.cost_usd_total) },
  ];
  const behaviourRows: { label: string; get: (m: "agentic" | "linear") => string }[] = [
    { label: "No cubiertas: comportamiento esperado", get: (m) => pct(report.aggregates[m]?.not_covered?.behaviour_pass_rate) },
    { label: "Fuera de alcance: comportamiento esperado", get: (m) => pct(report.aggregates[m]?.out_of_scope?.behaviour_pass_rate) },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Card title="Calidad de la respuesta" subtitle={`Preguntas con documentación (cubiertas + seguimiento, n=${n}); escala 0–1, más es mejor.`}>
        <div className="flex gap-4">
          <LegendItem color={SERIES_COLOR.agentic} label={MODE_LABEL.agentic} />
          <LegendItem color={SERIES_COLOR.linear} label={MODE_LABEL.linear} />
        </div>
        <div className="overflow-x-auto">
        <div className="h-72 min-w-[28rem]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rows} margin={{ top: 16, right: 8, left: -16, bottom: 0 }} barGap={2}>
              <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
              <XAxis dataKey="metric" tick={{ fontSize: 11, fill: "var(--ink-muted)" }} axisLine={false} tickLine={false} interval={0} />
              <YAxis domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} tick={{ fontSize: 11, fill: "var(--ink-muted)" }} axisLine={false} tickLine={false} />
              <Tooltip cursor={{ fill: "var(--primary-soft)" }} contentStyle={tooltipStyle} formatter={(v) => score(Number(v))} />
              {(["agentic", "linear"] as const).map((m) => (
                <Bar key={m} dataKey={m} name={MODE_LABEL[m]} fill={SERIES_COLOR[m]} radius={[4, 4, 0, 0]} maxBarSize={28} isAnimationActive={false}>
                  <LabelList dataKey={m} position="top" formatter={(v) => score(Number(v))} style={{ fontSize: 10, fill: "var(--ink-muted)" }} />
                </Bar>
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
        </div>
      </Card>
      <Card title="Costo y comportamiento" subtitle="Todas las preguntas (latencia medida en el cliente, incluye research).">
        <TableWrap label="Costo y comportamiento por modo">
          <thead>
            <tr>
              <th className={th} scope="col">Métrica</th>
              <th className={th} scope="col">{MODE_LABEL.agentic}</th>
              <th className={th} scope="col">{MODE_LABEL.linear}</th>
            </tr>
          </thead>
          <tbody>
            {costRows.map((r) => (
              <tr key={r.label}>
                <th scope="row" className={`${td} font-normal text-ink-muted`}>{r.label}</th>
                <td className={td}>{r.get(a?.all)}</td>
                <td className={td}>{r.get(l?.all)}</td>
              </tr>
            ))}
            {behaviourRows.map((r) => (
              <tr key={r.label}>
                <th scope="row" className={`${td} font-normal text-ink-muted`}>{r.label}</th>
                <td className={td}>{r.get("agentic")}</td>
                <td className={td}>{r.get("linear")}</td>
              </tr>
            ))}
          </tbody>
        </TableWrap>
      </Card>
    </div>
  );
}
