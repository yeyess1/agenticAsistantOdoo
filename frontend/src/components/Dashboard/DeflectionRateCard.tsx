"use client";

interface Props {
  deflectionRate: number; // 0-1 (e.g., 0.92 = 92%)
  deflectedCases: number;
  totalCases: number;
}

export default function DeflectionRateCard({
  deflectionRate,
  deflectedCases,
  totalCases,
}: Props) {
  const percentage = Math.round(deflectionRate * 100);
  const statusColor =
    deflectionRate >= 0.9
      ? "text-green-600"
      : deflectionRate >= 0.7
      ? "text-primary"
      : "text-amber-600";

  const statusLabel =
    deflectionRate >= 0.9
      ? "Excelente"
      : deflectionRate >= 0.7
      ? "Muy Buena"
      : "Buena";

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-line dark:border-zinc-800 p-6 shadow-sm">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h3 className="text-sm font-semibold text-ink dark:text-white">
            Tasa de Deflexión
          </h3>
          <p className="text-xs text-ink-muted dark:text-gray-500 mt-0.5">
            Consultas resueltas sin asesor humano
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {/* Main metric */}
        <div className="flex items-baseline gap-2">
          <div className="text-4xl font-bold text-ink dark:text-white">
            {percentage}%
          </div>
          <div className={`text-sm font-semibold ${statusColor}`}>
            {statusLabel}
          </div>
        </div>

        {/* Progress bar */}
        <div className="h-3 bg-gray-200 dark:bg-zinc-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-primary to-primary-muted transition-all duration-300"
            style={{ width: `${percentage}%` }}
          />
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 pt-2 border-t border-line dark:border-zinc-800">
          <div>
            <p className="text-lg font-bold text-ink dark:text-white">
              {deflectedCases}
            </p>
            <p className="text-xs text-ink-muted dark:text-gray-500">
              Casos resueltos
            </p>
          </div>
          <div>
            <p className="text-lg font-bold text-ink dark:text-white">
              {totalCases}
            </p>
            <p className="text-xs text-ink-muted dark:text-gray-500">
              Total consultas
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
