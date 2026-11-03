"use client";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { ContextQualityDistribution } from "@/lib/metricsApi";

interface Props {
  distribution: ContextQualityDistribution;
  avgScore: number;
  mmrCount: number;
  totalRequests: number;
}

const QUALITY_CONFIG = [
  { key: "high", label: "Alta", color: "#714B67" },
  { key: "medium", label: "Media", color: "#5E3E56" },
  { key: "low", label: "Baja", color: "#B497AB" },
  { key: "none", label: "Sin ctx", color: "#e5e7eb" },
] as const;

function pct(fraction: number) {
  return Math.round(fraction * 100);
}

export default function ContextQualityChart({
  distribution,
  avgScore,
  mmrCount,
  totalRequests,
}: Props) {
  const chartData = QUALITY_CONFIG.map(({ key, label, color }) => ({
    name: label,
    value: pct(distribution[key]),
    color,
  })).filter((d) => d.value > 0);

  const scoreLabel =
    avgScore >= 0.7 ? "Excelente" : avgScore >= 0.5 ? "Buena" : "Mejorable";
  const scoreColor =
    avgScore >= 0.7 ? "text-green-600" : avgScore >= 0.5 ? "text-amber-600" : "text-red-500";
  const mmrPct =
    totalRequests > 0 ? Math.round((mmrCount / totalRequests) * 100) : 0;

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-line dark:border-zinc-800 p-6 shadow-sm flex flex-col gap-5">
      <div>
        <h3 className="text-sm font-semibold text-ink dark:text-white">
          Calidad de Contexto
        </h3>
        <p className="text-xs text-ink-muted dark:text-gray-500 mt-0.5">
          Distribución por nivel de relevancia RAG
        </p>
      </div>

      {/* Donut chart */}
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={88}
              paddingAngle={3}
              dataKey="value"
              strokeWidth={0}
            >
              {chartData.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => [`${value}%`, "Porcentaje"]}
              contentStyle={{
                borderRadius: "12px",
                border: "1px solid #e5e7eb",
                fontSize: "12px",
              }}
            />
            <Legend
              iconType="circle"
              iconSize={8}
              formatter={(value) => (
                <span className="text-xs text-ink-muted dark:text-gray-400">
                  {value}
                </span>
              )}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Stats below chart */}
      <div className="grid grid-cols-2 gap-3 pt-2 border-t border-line dark:border-zinc-800">
        <div className="text-center">
          <p className={`text-xl font-bold ${scoreColor}`}>
            {avgScore > 0 ? avgScore.toFixed(2) : "—"}
          </p>
          <p className="text-xs text-ink-muted mt-0.5">
            Relevancia prom. · <span className={scoreColor}>{avgScore > 0 ? scoreLabel : "Sin datos"}</span>
          </p>
        </div>
        <div className="text-center">
          <p className="text-xl font-bold text-primary dark:text-primary-muted">
            {mmrPct}%
          </p>
          <p className="text-xs text-ink-muted mt-0.5">
            Consultas con MMR
          </p>
        </div>
      </div>
    </div>
  );
}
