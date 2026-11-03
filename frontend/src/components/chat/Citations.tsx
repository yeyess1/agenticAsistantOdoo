import type { SourceRef } from "@/lib/api/client";
import { shortUrl } from "@/lib/format";

/** Citation cards (U-07): document, section, url#anchor or PDF page; anchors `#<prefix>-<n>`. */
export default function Citations({ sources, citePrefix, research }: { sources: SourceRef[]; citePrefix: string; research: boolean }) {
  const shown = sources.some((s) => s.cited) ? sources.filter((s) => s.cited) : sources;
  if (shown.length === 0) return null;
  const isWeb = (url: string) => /^https?:\/\//.test(url);
  // Sections are breadcrumbs that start with the page title: drop it, the card shows it already.
  const section = (s: SourceRef) => {
    const sec = s.section ?? "";
    const rest = sec.startsWith(`${s.title} > `) ? sec.slice(s.title.length + 3) : sec;
    return rest.replaceAll(" > ", " › ") || s.title;
  };
  return (
    <section aria-label="Fuentes citadas">
      <ul className="m-0 grid list-none grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-2.5 p-0">
        {shown.map((s) => {
          const body = (
            <>
              <span className="flex items-center gap-2">
                <span className={`flex h-[22px] min-w-[22px] shrink-0 items-center justify-center rounded-md text-xs font-semibold text-white ${research ? "bg-research" : "bg-primary"}`}>
                  {s.n}
                </span>
                <span className="truncate text-[13px] font-semibold" title={s.title}>{s.kind === "external" ? "Odoo Forum" : s.title}</span>
              </span>
              <span className="text-xs text-ink-muted">{s.kind === "external" ? s.title : section(s)}</span>
              <span className="truncate font-mono text-[11px] text-primary-hover">
                {s.page != null ? `${shortUrl(s.url)} · p. ${s.page}` : shortUrl(s.url)}
              </span>
            </>
          );
          const cls = "flex h-full flex-col gap-1 rounded-xl border border-line bg-background px-3.5 py-3 text-ink no-underline";
          return (
            <li key={s.n} id={`${citePrefix}-${s.n}`} className="min-w-0 scroll-mt-24">
              {isWeb(s.url) ? (
                <a href={s.url} target="_blank" rel="noopener noreferrer" className={`${cls} hover:border-primary-muted`}>
                  {body}
                </a>
              ) : (
                <div className={cls}>{body}</div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
