"use client";

interface Keyword {
  keyword: string;
  count: number;
  frequency: number;
}

interface Props {
  keywords: Keyword[];
}

export default function TopKeywordsSection({ keywords }: Props) {
  if (!keywords || keywords.length === 0) {
    return (
      <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-line dark:border-zinc-800 p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-ink dark:text-white mb-2">
          Términos Más Consultados
        </h3>
        <p className="text-xs text-ink-muted dark:text-gray-500">
          Sin datos disponibles
        </p>
      </div>
    );
  }

  // Find max and min frequency for scaling
  const maxFreq = Math.max(...keywords.map((k) => k.frequency));
  const minFreq = Math.min(...keywords.map((k) => k.frequency));
  const freqRange = maxFreq - minFreq || 1;

  // Function to calculate tag size
  const getTagSize = (frequency: number): string => {
    const normalized = (frequency - minFreq) / freqRange;
    if (normalized > 0.7) return "text-lg";
    if (normalized > 0.4) return "text-base";
    return "text-sm";
  };

  // Function to get opacity
  const getOpacity = (frequency: number): string => {
    const normalized = (frequency - minFreq) / freqRange;
    if (normalized > 0.7) return "opacity-100";
    if (normalized > 0.4) return "opacity-75";
    return "opacity-60";
  };

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-line dark:border-zinc-800 p-6 shadow-sm">
      <div className="mb-6">
        <h3 className="text-sm font-semibold text-ink dark:text-white">
          Términos Más Consultados
        </h3>
        <p className="text-xs text-ink-muted dark:text-gray-500 mt-0.5">
          Palabras clave de las consultas de usuarios
        </p>
      </div>

      {/* Tag Cloud */}
      <div className="flex flex-wrap gap-3">
        {keywords.map((keyword) => (
          <div
            key={keyword.keyword}
            className="flex flex-col items-center"
            title={`${keyword.count} consultas (${(keyword.frequency * 100).toFixed(1)}%)`}
          >
            <span
              className={`
                px-3 py-2 rounded-full font-semibold
                bg-primary-soft dark:bg-primary/30
                text-primary dark:text-primary-muted
                border border-primary-tint dark:border-primary-hover
                cursor-default transition-transform hover:scale-105
                ${getTagSize(keyword.frequency)}
                ${getOpacity(keyword.frequency)}
              `}
            >
              {keyword.keyword}
            </span>
            <span className="text-xs text-ink-muted dark:text-gray-600 mt-1">
              {keyword.count}
            </span>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="mt-6 pt-4 border-t border-line dark:border-zinc-800">
        <p className="text-xs text-ink-muted dark:text-gray-400">
          El tamaño indica frecuencia relativa de consultas
        </p>
      </div>
    </div>
  );
}
