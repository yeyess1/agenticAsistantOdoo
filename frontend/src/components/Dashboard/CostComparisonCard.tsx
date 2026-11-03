"use client";

interface Props {
  ragTotalUsd: number;
  humanTotalUsd: number;
  savingsTotalUsd: number;
  ragPerQueryUsd: number;
  humanPerQueryUsd: number;
}

export default function CostComparisonCard({
  ragTotalUsd,
  humanTotalUsd,
  savingsTotalUsd,
  ragPerQueryUsd,
  humanPerQueryUsd,
}: Props) {
  const savingsPercentage =
    humanTotalUsd > 0
      ? Math.round((savingsTotalUsd / humanTotalUsd) * 100)
      : 0;

  const costRatio = humanPerQueryUsd > 0 ? ragPerQueryUsd / humanPerQueryUsd : 0;
  const costReductionPercentage = Math.round((1 - costRatio) * 100);

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-line dark:border-zinc-800 p-6 shadow-sm">
      <div className="mb-6">
        <h3 className="text-sm font-semibold text-ink dark:text-white">
          Análisis de Costo
        </h3>
        <p className="text-xs text-ink-muted dark:text-gray-500 mt-0.5">
          RAG vs Asesor Humano
        </p>
      </div>

      {/* Main savings metric */}
      <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
        <p className="text-xs text-green-700 dark:text-green-400 font-semibold mb-1">
          Ahorro Total
        </p>
        <p className="text-3xl font-bold text-green-600 dark:text-green-400">
          ${savingsTotalUsd.toFixed(2)}
        </p>
        <p className="text-xs text-green-600 dark:text-green-400 mt-1">
          {savingsPercentage}% de reducción
        </p>
      </div>

      {/* Cost comparison table */}
      <div className="space-y-3 border-t border-line dark:border-zinc-800 pt-4">
        {/* Per query */}
        <div>
          <p className="text-xs font-semibold text-ink-muted dark:text-gray-400 mb-2">
            Costo por Consulta
          </p>
          <div className="flex items-center justify-between gap-2">
            <div className="flex-1">
              <div className="flex items-baseline gap-1 mb-1">
                <span className="text-sm font-semibold text-primary">RAG</span>
                <span className="text-lg font-bold text-ink dark:text-white">
                  ${ragPerQueryUsd.toFixed(6)}
                </span>
              </div>
              <div className="h-2 bg-primary rounded-full w-1/4" />
            </div>
            <div className="flex-1">
              <div className="flex items-baseline gap-1 mb-1">
                <span className="text-sm font-semibold text-amber-600">
                  Humano
                </span>
                <span className="text-lg font-bold text-ink dark:text-white">
                  ${humanPerQueryUsd.toFixed(2)}
                </span>
              </div>
              <div className="h-2 bg-amber-600 rounded-full" />
            </div>
          </div>
          <p className="text-xs text-green-600 dark:text-green-400 mt-2 font-semibold">
            {costReductionPercentage}% más barato
          </p>
        </div>

        {/* Total costs */}
        <div className="border-t border-line dark:border-zinc-800 pt-3">
          <p className="text-xs font-semibold text-ink-muted dark:text-gray-400 mb-2">
            Costo Total Período
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-primary-soft dark:bg-primary/20 p-3 rounded-lg">
              <p className="text-xs text-primary-hover dark:text-primary-muted font-semibold">
                RAG
              </p>
              <p className="text-xl font-bold text-primary dark:text-primary-muted">
                ${ragTotalUsd.toFixed(2)}
              </p>
            </div>
            <div className="bg-amber-50 dark:bg-amber-900/20 p-3 rounded-lg">
              <p className="text-xs text-amber-700 dark:text-amber-400 font-semibold">
                Humano
              </p>
              <p className="text-xl font-bold text-amber-600 dark:text-amber-400">
                ${humanTotalUsd.toFixed(2)}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
