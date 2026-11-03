import type { StepRecord } from "@/lib/api/client";
import { fmtInt, fmtSeconds } from "@/lib/format";

type Detail = Record<string, unknown>;

/** One-line, human description of what a node did (from `StepRecord.detail`). */
function describe(step: StepRecord): string {
  const d = (step.detail ?? {}) as Detail;
  switch (step.node) {
    case "contextualize":
      if (d.passthrough) return "Pass-through: thread sin historial";
      return d.rewritten ? `Reescrita: «${String(d.standalone_question ?? "")}»` : "Pregunta ya independiente";
    case "router":
      return `Ruta → ${String(d.route ?? "?")}${d.llm_error ? " (fallo del LLM: docs por defecto)" : ""}`;
    case "retriever":
      return `${fmtInt(Number(d.n_retrieved ?? 0))} chunks · dense${d.top_score != null ? ` · top ${Number(d.top_score).toFixed(2)}` : ""}`;
    case "grader":
      if (d.fail_open) return "Fallo del LLM: se usan todos los chunks";
      return `${fmtInt(Number(d.n_relevant ?? 0))} de ${fmtInt(Number(d.n_graded ?? 0))} chunks relevantes`;
    case "rewriter":
      return `Intento ${String(d.attempt ?? "?")}: «${String(d.rewritten ?? "")}» (${String(d.language ?? "")})`;
    case "generator": {
      const invalid = Array.isArray(d.invalid_citations) ? d.invalid_citations.length : 0;
      return `Respuesta con ${fmtInt(Number(d.n_cited ?? 0))} citas [n]${invalid ? ` · ${invalid} inválidas` : ""}`;
    }
    case "no_context":
      return "Sin contexto suficiente: delega en investigación";
    case "confirm_external_search":
      return d.hitl ? (d.approved ? "Búsqueda externa aprobada" : "Búsqueda externa rechazada") : "Pass-through (HITL apagado)";
    case "research_llm": {
      const calls = Array.isArray(d.tool_calls) ? d.tool_calls : [];
      return calls.length ? `Iteración ${String(d.iteration)}: ${calls.join(", ")}` : `Iteración ${String(d.iteration)}: redacta la respuesta`;
    }
    case "tools": {
      const calls = Array.isArray(d.calls) ? (d.calls as { tool: string; status: string }[]) : [];
      return calls.map((c) => `${c.tool} (${c.status})`).join(", ");
    }
    case "finalize_external":
      return d.found ? `${fmtInt(Number(d.n_sources ?? 0))} posts del foro` : "Sin fuentes externas";
    case "direct_answer":
      return "Respuesta directa (sin recuperación)";
    default:
      return "";
  }
}

const DOT: Record<StepRecord["agent"], string> = { supervisor: "bg-primary", docs: "bg-primary", research: "bg-research" };

/** Collapsible timeline of graph steps (U-08): node, detail, duration. */
export default function StepsTimeline({ steps, linear }: { steps: StepRecord[]; linear: boolean }) {
  if (steps.length === 0) return null;
  const label = (s: StepRecord) => (!linear && s.agent === "docs" ? `docs_agent › ${s.node}` : s.node);
  return (
    <details className="rounded-xl border border-line bg-surface">
      <summary className="cursor-pointer rounded-xl px-3.5 py-2.5 text-[13px] font-semibold text-ink">
        Pasos del grafo · {steps.length} nodos
      </summary>
      <ol className="m-0 flex list-none flex-col px-3.5 pb-3.5 pt-1">
        {steps.map((s, i) => (
          <li key={s.id} className="flex items-start gap-3">
            <div className="flex flex-col items-center self-stretch" aria-hidden="true">
              <span className={`mt-1.5 h-2.5 w-2.5 rounded-full ring-[3px] ring-primary-tint ${DOT[s.agent]}`} />
              {i < steps.length - 1 && <span className="min-h-3.5 w-0.5 flex-1 bg-line" />}
            </div>
            <div className="flex min-w-0 flex-1 flex-wrap justify-between gap-2 pb-2">
              <span className="flex min-w-0 flex-col">
                <span className="font-mono text-[13px] font-medium">{label(s)}</span>
                <span className="break-words text-xs text-ink-muted">{describe(s)}</span>
              </span>
              <span className="font-mono text-xs text-ink-muted">
                {fmtSeconds(s.duration_ms)}
                {s.model ? ` · ${s.model}` : ""}
              </span>
            </div>
          </li>
        ))}
      </ol>
    </details>
  );
}
