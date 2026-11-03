"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LabelList,
} from "recharts";

interface Props {
  avgTotal: number;
  avgRetrieval: number;
  avgGeneration: number;
  maxTotal: number;
}

export default function LatencyChart({
  avgTotal,
  avgRetrieval,
  avgGeneration,
  maxTotal,
}: Props) {
  const overhead = Math.max(0, avgTotal - avgRetrieval - avgGeneration);

  const data = [
    { name: "Retrieval",   value: Math.round(avgRetrieval),  color: "#714B67" },
    { name: "Generación",  value: Math.round(avgGeneration), color: "#5E3E56" },
    { name: "Overhead",    value: Math.round(overhead),      color: "#E4D6E0" },
  ].filter((d) => d.value > 0);

  const latencyRating =
    avgTotal < 500 ? "Rápida" : avgTotal < 1500 ? "Normal" : "Lenta";
  const ratingColor =
    avgTotal < 500 ? "text-green-600" : avgTotal < 1500 ? "text-amber-600" : "text-red-500";

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-line dark:border-zinc-800 p-6 shadow-sm flex flex-col gap-5">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-semibold text-ink dark:text-white">
            Latencia por Fase
          </h3>
          <p className="text-xs text-ink-muted dark:text-gray-500 mt-0.5">
            Desglose promedio del tiempo de respuesta
          </p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-ink dark:text-white">
            {avgTotal > 0 ? `${Math.round(avgTotal)}ms` : "—"}
          </p>
          <p className={`text-xs font-semibold ${ratingColor}`}>{avgTotal > 0 ? latencyRating : "Sin datos"}</p>
        </div>
      </div>

      {/* Horizontal bars via vertical BarChart */}
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ left: 8, right: 40, top: 0, bottom: 0 }}
          >
            <XAxis type="number" hide />
            <YAxis
              type="category"
              dataKey="name"
              width={80}
              tick={{ fontSize: 12, fill: "#6b7280" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              formatter={(v) => [`${v}ms`, "Latencia"]}
              contentStyle={{
                borderRadius: "12px",
                border: "1px solid #e5e7eb",
                fontSize: "12px",
              }}
            />
            <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={22}>
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
              <LabelList
                dataKey="value"
                position="right"
                formatter={(v: string | number | boolean | null | undefined) => v != null && v !== false ? `${v}ms` : ""}
                style={{ fontSize: "11px", fill: "#6b7280", fontWeight: 600 }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Max latency footer */}
      {maxTotal > 0 && (
        <p className="text-xs text-ink-muted pt-2 border-t border-line dark:border-zinc-800">
          Pico máximo:{" "}
          <span className="font-semibold text-ink-muted dark:text-gray-300">
            {Math.round(maxTotal)}ms
          </span>
        </p>
      )}
    </div>
  );
}
