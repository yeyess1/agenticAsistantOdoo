"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface Props {
  totalInput: number;
  totalOutput: number;
  avgInput: number;
  avgOutput: number;
  totalCost: number;
  avgCostPerRequest: number;
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

function formatCost(usd: number): string {
  if (usd < 0.001) return `$${(usd * 1000).toFixed(3)}m`;
  return `$${usd.toFixed(4)}`;
}

export default function TokenUsageChart({
  totalInput,
  totalOutput,
  avgInput,
  avgOutput,
  totalCost,
  avgCostPerRequest,
}: Props) {
  const barData = [
    {
      name: "Total",
      "Input tokens": totalInput,
      "Output tokens": totalOutput,
    },
    {
      name: "Promedio",
      "Input tokens": Math.round(avgInput),
      "Output tokens": Math.round(avgOutput),
    },
  ];

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-line dark:border-zinc-800 p-6 shadow-sm flex flex-col gap-5">
      <div>
        <h3 className="text-sm font-semibold text-ink dark:text-white">
          Uso de Tokens y Costo
        </h3>
        <p className="text-xs text-ink-muted dark:text-gray-500 mt-0.5">
          Tokens Gemini · Tarifa: $0.075/1M input · $0.30/1M output
        </p>
      </div>

      <div className="h-44">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={barData}
            margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
            barCategoryGap="30%"
          >
            <XAxis
              dataKey="name"
              tick={{ fontSize: 12, fill: "#6b7280" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tickFormatter={formatTokens}
              tick={{ fontSize: 11, fill: "#9ca3af" }}
              axisLine={false}
              tickLine={false}
              width={40}
            />
            <Tooltip
              formatter={(value, name) => [
                formatTokens(Number(value)),
                String(name),
              ]}
              contentStyle={{
                borderRadius: "12px",
                border: "1px solid #e5e7eb",
                fontSize: "12px",
              }}
            />
            <Legend
              iconType="circle"
              iconSize={8}
              formatter={(v) => (
                <span style={{ fontSize: "11px", color: "#6b7280" }}>{v}</span>
              )}
            />
            <Bar
              dataKey="Input tokens"
              fill="#714B67"
              radius={[4, 4, 0, 0]}
              barSize={28}
            />
            <Bar
              dataKey="Output tokens"
              fill="#B497AB"
              radius={[4, 4, 0, 0]}
              barSize={28}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Cost summary */}
      <div className="grid grid-cols-2 gap-3 pt-3 border-t border-line dark:border-zinc-800">
        <div>
          <p className="text-lg font-bold text-ink dark:text-white">
            {totalCost > 0 ? formatCost(totalCost) : "—"}
          </p>
          <p className="text-xs text-ink-muted mt-0.5">Costo total período</p>
        </div>
        <div>
          <p className="text-lg font-bold text-ink dark:text-white">
            {avgCostPerRequest > 0 ? formatCost(avgCostPerRequest) : "—"}
          </p>
          <p className="text-xs text-ink-muted mt-0.5">Costo promedio / req</p>
        </div>
      </div>
    </div>
  );
}
