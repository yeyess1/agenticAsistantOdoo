"use client";

import type { ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { pct, tokens } from "@/components/analytics/format";

const tooltipStyle = { borderRadius: 8, border: "1px solid var(--line)", fontSize: 12, color: "var(--ink)", background: "var(--background)" };
const BAR = "var(--chart-agentic)";

export type BarDatum = { label: string; value: number; detail?: string };

/** Horizontal ranked bars, one hue (magnitude only); value as a direct label at the bar end. */
export function BarList({ data, labelWidth = 150, unit = "", format = (v: number) => String(v) }: { data: BarDatum[]; labelWidth?: number; unit?: string; format?: (v: number) => string }) {
  if (data.length === 0) return <Empty>Sin datos para este filtro.</Empty>;
  return (
    <div className="min-w-0">
      <div style={{ height: `${Math.max(120, data.length * 30)}px` }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 48, left: 4, bottom: 0 }} barCategoryGap={2}>
            <XAxis type="number" hide />
            <YAxis type="category" dataKey="label" width={labelWidth} tick={{ fontSize: 11, fill: "var(--ink-muted)" }} axisLine={false} tickLine={false} interval={0} />
            <Tooltip
              cursor={{ fill: "var(--primary-soft)" }}
              contentStyle={tooltipStyle}
              formatter={(v, _n, item) => [`${format(Number(v))}${unit}${(item.payload as BarDatum).detail ? ` · ${(item.payload as BarDatum).detail}` : ""}`, (item.payload as BarDatum).label]}
              labelFormatter={() => ""}
            />
            <Bar dataKey="value" fill={BAR} radius={[0, 4, 4, 0]} maxBarSize={16} isAnimationActive={false}>
              <LabelList dataKey="value" position="right" formatter={(v) => format(Number(v))} style={{ fontSize: 10, fill: "var(--ink-muted)" }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/** Answer length distribution (output tokens of the answering node), 100-token bins. */
export function TokenHistogram({ bins }: { bins: { lo: number; hi: number; count: number }[] }) {
  if (bins.length === 0) return <Empty>Sin respuestas con tokens registrados.</Empty>;
  const total = bins.reduce((a, b) => a + b.count, 0);
  const data = bins.map((b) => ({ ...b, label: tokens(b.lo) }));
  return (
    <div className="h-56 min-w-0 overflow-hidden">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }} barCategoryGap={2}>
          <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
          <XAxis dataKey="label" tick={{ fontSize: 10, fill: "var(--ink-muted)" }} axisLine={false} tickLine={false} />
          <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: "var(--ink-muted)" }} axisLine={false} tickLine={false} />
          <Tooltip
            cursor={{ fill: "var(--primary-soft)" }}
            contentStyle={tooltipStyle}
            labelFormatter={() => ""}
            formatter={(v, _n, item) => {
              const b = item.payload as { lo: number; hi: number };
              return [`${v} respuestas (${pct(Number(v) / total)})`, `${tokens(b.lo)}–${tokens(b.hi)} tokens`];
            }}
          />
          <Bar dataKey="count" fill={BAR} radius={[4, 4, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="py-6 text-center text-sm text-ink-muted">{children}</p>;
}

/** Segmented single-choice control (filters, tabs). */
export function Segmented<T extends string>({ label, value, options, onChange }: { label: string; value: T; options: { value: T; label: string }[]; onChange: (v: T) => void }) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex flex-wrap items-center gap-1 self-start rounded-lg border border-line bg-background p-1 text-xs">
      <span className="px-2 font-medium text-ink-muted">{label}</span>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          onClick={() => onChange(o.value)}
          className={`rounded-md px-2.5 py-1.5 font-medium ${value === o.value ? "bg-primary-soft text-primary-hover" : "text-ink-muted hover:text-primary-hover"}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
