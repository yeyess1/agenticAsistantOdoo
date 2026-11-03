interface StatCardProps {
  title: string;
  value: string;
  subtitle?: string;
  trend?: "up" | "down" | "neutral";
  trendLabel?: string;
  icon: React.ReactNode;
  accentColor?: "blue" | "green" | "amber" | "purple";
}

const ACCENT = {
  blue:   { bg: "bg-primary/10", text: "text-primary", value: "text-primary" },
  green:  { bg: "bg-green-50",     text: "text-green-600", value: "text-green-700" },
  amber:  { bg: "bg-amber-50",     text: "text-amber-600", value: "text-amber-700" },
  purple: { bg: "bg-purple-50",    text: "text-purple-600", value: "text-purple-700" },
};

export default function StatCard({
  title,
  value,
  subtitle,
  trend,
  trendLabel,
  icon,
  accentColor = "blue",
}: StatCardProps) {
  const accent = ACCENT[accentColor];

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-line dark:border-zinc-800 p-5 flex flex-col gap-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-ink-muted dark:text-gray-500 uppercase tracking-widest">
          {title}
        </p>
        <div className={`flex h-9 w-9 items-center justify-center rounded-xl ${accent.bg} ${accent.text}`}>
          {icon}
        </div>
      </div>

      <div>
        <p className={`text-3xl font-bold tracking-tight ${accent.value} dark:text-white`}>
          {value}
        </p>

        <div className="flex items-center gap-2 mt-1.5">
          {trend && trendLabel && (
            <span
              className={`inline-flex items-center gap-0.5 text-xs font-semibold px-1.5 py-0.5 rounded-full ${
                trend === "up"
                  ? "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                  : trend === "down"
                  ? "bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400"
                  : "bg-primary-soft text-ink-muted dark:bg-zinc-800 dark:text-gray-400"
              }`}
            >
              {trend === "up" ? "↑" : trend === "down" ? "↓" : "—"}
              {trendLabel}
            </span>
          )}
          {subtitle && (
            <p className="text-xs text-ink-muted dark:text-gray-500">{subtitle}</p>
          )}
        </div>
      </div>
    </div>
  );
}
