"use client";

import { type TimeWindow, WINDOW_LABELS } from "@/lib/metricsApi";

interface FiltersProps {
  window: TimeWindow;
  onWindowChange: (w: TimeWindow) => void;
  onRefresh: () => void;
  loading: boolean;
  lastUpdated: Date | null;
}

const WINDOWS: TimeWindow[] = ["1h", "6h", "24h", "7d", "30d"];

function formatTime(date: Date): string {
  return date.toLocaleTimeString("es-CO", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function Filters({
  window,
  onWindowChange,
  onRefresh,
  loading,
  lastUpdated,
}: FiltersProps) {
  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
      {/* Time window selector */}
      <div className="flex items-center gap-1 bg-primary-soft dark:bg-zinc-800 rounded-xl p-1">
        {WINDOWS.map((w) => (
          <button
            key={w}
            onClick={() => onWindowChange(w)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${window === w
                ? "bg-primary text-white shadow-sm"
                : "text-ink-muted dark:text-gray-400 hover:text-ink dark:hover:text-white"
              }`}
          >
            {w}
          </button>
        ))}
      </div>

      {/* Right: last updated + refresh */}
      <div className="flex items-center gap-3">
        {lastUpdated && (
          <p className="text-xs text-ink-muted dark:text-gray-500">
            Actualizado a las {formatTime(lastUpdated)}
          </p>
        )}
        <button
          onClick={onRefresh}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-xs font-semibold text-white hover:bg-primary-hover disabled:opacity-50 transition-colors shadow-sm"
        >
          <svg
            className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          {loading ? "Cargando…" : "Actualizar"}
        </button>
      </div>
    </div>
  );
}
