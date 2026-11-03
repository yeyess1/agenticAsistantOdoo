import type { ReactNode } from "react";

export function Section({ id, title, subtitle, children }: { id: string; title: string; subtitle?: ReactNode; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-4">
      <div>
        <h2 id={id} className="text-lg font-semibold text-ink">{title}</h2>
        {subtitle && <p className="mt-1 max-w-3xl text-sm text-ink-muted">{subtitle}</p>}
      </div>
      {children}
    </section>
  );
}

export function Card({ title, subtitle, children, className = "" }: { title?: string; subtitle?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <div className={`flex min-w-0 flex-col gap-4 rounded-xl border border-line bg-background p-5 ${className}`}>
      {title && (
        <div>
          <h3 className="text-sm font-semibold text-ink">{title}</h3>
          {subtitle && <p className="mt-0.5 text-xs text-ink-muted">{subtitle}</p>}
        </div>
      )}
      {children}
    </div>
  );
}

export function StatTile({ label, value, detail }: { label: string; value: string; detail?: ReactNode }) {
  return (
    <div className="flex min-w-0 flex-col gap-1 rounded-xl border border-line bg-background p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">{label}</p>
      <p className="text-2xl font-semibold tabular-nums text-ink">{value}</p>
      {detail && <p className="text-xs text-ink-muted">{detail}</p>}
    </div>
  );
}

/** Legend chip: a colored swatch next to text in ink (identity never by color alone). */
export function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-ink-muted">
      <span aria-hidden="true" className="h-2.5 w-2.5 rounded-sm" style={{ background: color }} />
      {label}
    </span>
  );
}

export function TableWrap({ children, label }: { children: ReactNode; label: string }) {
  return (
    <div role="region" aria-label={label} tabIndex={0} className="overflow-x-auto">
      <table className="w-full min-w-[32rem] border-collapse text-sm">{children}</table>
    </div>
  );
}

export const th = "border-b border-line px-3 py-2 text-left text-xs font-semibold text-ink-muted";
export const td = "border-b border-line px-3 py-2 text-left tabular-nums text-ink";
