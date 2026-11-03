import type { QueryResponse } from "@/lib/api/client";
import { fmtSeconds, fmtUsd } from "@/lib/format";
import AgentBadge from "./AgentBadge";
import Citations from "./Citations";
import Markdown from "./Markdown";
import StepsTimeline from "./StepsTimeline";
import type { LiveState } from "./types";

/** In-flight turn (U-10): live graph steps and the answer as it streams. */
export function PendingMessage({ id, linear, live }: { id: string; linear: boolean; live: LiveState }) {
  const current = live.steps.at(-1);
  const research = live.steps.some((s) => s.agent === "research");
  return (
    <article className="flex flex-col gap-2.5" aria-busy="true" aria-label="Respuesta en curso">
      <ol className="m-0 flex list-none flex-wrap items-center gap-1.5 p-0 text-xs text-ink-muted" aria-label="Pasos del grafo en curso">
        {live.steps.length === 0 && <li>{linear ? "RAG lineal: recuperando…" : "El supervisor está trabajando…"}</li>}
        {live.steps.map((s, i) => (
          <li key={`${s.node}-${i}`} className={`rounded-full border px-2 py-0.5 font-mono ${s.durationMs == null ? "border-primary text-primary-hover" : "border-line"}`}>
            {s.node}
            {s.durationMs != null && ` · ${fmtSeconds(s.durationMs)}`}
          </li>
        ))}
      </ol>
      {live.text ? (
        <Markdown text={live.text} citePrefix={`cite-${id}`} sourceNumbers={research ? [] : live.sources.map((s) => s.n)} />
      ) : (
        <div role="status" aria-label={current ? `Ejecutando ${current.node}` : "Escribiendo"} className="flex w-fit items-center gap-1.5 rounded-2xl bg-surface px-4 py-3">
          <span className="typing-dot h-[7px] w-[7px] rounded-full bg-primary" />
          <span className="typing-dot h-[7px] w-[7px] rounded-full bg-primary [animation-delay:0.15s]" />
          <span className="typing-dot h-[7px] w-[7px] rounded-full bg-primary [animation-delay:0.3s]" />
        </div>
      )}
    </article>
  );
}

export function ErrorMessage({ error, onRetry }: { error: string; onRetry?: () => void }) {
  return (
    <article role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-danger bg-danger-soft px-4 py-3 text-sm text-danger">
      <span>{error}</span>
      {onRetry && (
        <button type="button" onClick={onRetry} className="h-9 rounded-lg border border-danger bg-background px-3 font-medium">
          Reintentar
        </button>
      )}
    </article>
  );
}

/** Assistant turn (U-03): agent badge, Markdown answer with `[n]`, citation cards, timeline. */
export default function AssistantMessage({ id, response }: { id: string; response: QueryResponse }) {
  const prefix = `cite-${id}`;
  const linear = response.mode === "linear";
  const research = response.answered_by === "research";
  const nSources = response.sources.filter((s) => s.cited).length || response.sources.length;
  return (
    <article className="flex flex-col gap-3.5" aria-label="Respuesta del asistente">
      <div className="flex flex-wrap items-center gap-2">
        {response.answered_by && <AgentBadge agent={response.answered_by} />}
        {linear && <span className="rounded-full border border-line px-2.5 py-0.5 text-xs font-medium text-ink-muted">RAG lineal</span>}
        {response.delegated && <span className="rounded-full bg-research-soft px-2.5 py-0.5 text-xs font-medium text-research">Delegada por falta de contexto</span>}
        <span className="text-xs text-ink-muted">
          {fmtSeconds(response.latency_ms)}
          {nSources > 0 && ` · ${nSources} ${nSources === 1 ? "fuente" : "fuentes"}`}
          {response.usage.cost_usd > 0 && ` · ${fmtUsd(response.usage.cost_usd)}`}
        </span>
      </div>
      <Markdown text={response.answer} citePrefix={prefix} sourceNumbers={response.sources.map((s) => s.n)} />
      <Citations sources={response.sources} citePrefix={prefix} research={research} />
      <StepsTimeline steps={response.steps} linear={linear} />
    </article>
  );
}
