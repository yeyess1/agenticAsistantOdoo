import type { QueryResponse } from "@/lib/api/client";

type Agent = NonNullable<QueryResponse["answered_by"]>;

const STYLES: Record<Agent, { label: string; cls: string; icon: React.ReactNode }> = {
  docs: {
    label: "Agente de documentación",
    cls: "bg-primary-soft text-primary-hover",
    icon: (
      <>
        <path d="M4 19V5a2 2 0 0 1 2-2h12v16H6a2 2 0 0 0-2 2" />
        <path d="M8 7h6" />
      </>
    ),
  },
  research: {
    label: "Agente de investigación",
    cls: "bg-research-soft text-research",
    icon: (
      <>
        <circle cx="11" cy="11" r="7" />
        <path d="M20 20l-4-4" />
      </>
    ),
  },
  direct: {
    label: "Respuesta directa",
    cls: "bg-neutral-soft text-ink",
    icon: <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.4A8 8 0 1 1 21 12z" />,
  },
};

/** Which agent answered (U-08): docs plum, research teal, direct neutral. */
export default function AgentBadge({ agent }: { agent: Agent }) {
  const s = STYLES[agent];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${s.cls}`}>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        {s.icon}
      </svg>
      {s.label}
    </span>
  );
}
