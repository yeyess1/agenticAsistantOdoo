"use client";

import { Bar, BarChart, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card } from "./Card";
import { money, pct, secs, tokens } from "./format";
import type { NodeStats } from "./types";

const tooltipStyle = { borderRadius: 8, border: "1px solid var(--line)", fontSize: 12, color: "var(--ink)" };

export default function NodeCost({ nodes }: { nodes: Record<string, NodeStats> }) {
  const data = Object.entries(nodes)
    .filter(([, s]) => (s.cost_usd_total ?? 0) > 0 || (s.duration_ms_mean ?? 0) > 0)
    .map(([node, s]) => ({ node, ...s, cost: s.cost_usd_total ?? 0 }));
  return (
    <Card title="Costo por nodo (agéntico)" subtitle="Costo total de la corrida por nodo del grafo; el tooltip muestra llamadas, duración media y tokens.">
      <div className="overflow-x-auto">
      <div className="min-w-[24rem]" style={{ height: `${Math.max(160, data.length * 34)}px` }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 56, left: 8, bottom: 0 }}>
            <XAxis type="number" hide />
            <YAxis type="category" dataKey="node" width={150} tick={{ fontSize: 11, fill: "var(--ink-muted)" }} axisLine={false} tickLine={false} />
            <Tooltip
              cursor={{ fill: "var(--primary-soft)" }}
              contentStyle={tooltipStyle}
              formatter={(_v, _n, item) => {
                const s = item.payload as NodeStats;
                return [`${money(s.cost_usd_total)} (${pct(s.cost_share)}) · ${s.calls} llamadas · ${secs(s.duration_ms_mean)} · ${tokens(s.input_tokens_mean)} tokens de entrada`, "Costo"];
              }}
            />
            <Bar dataKey="cost" fill="var(--chart-agentic)" radius={[0, 4, 4, 0]} maxBarSize={18} isAnimationActive={false}>
              <LabelList dataKey="cost" position="right" formatter={(v) => money(Number(v))} style={{ fontSize: 10, fill: "var(--ink-muted)" }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      </div>
    </Card>
  );
}
