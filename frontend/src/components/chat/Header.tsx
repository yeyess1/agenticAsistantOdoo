import Link from "next/link";
import { shortId } from "@/lib/format";

export function AppMark() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-primary" aria-hidden="true">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M8 6l-6 6 6 6" />
          <path d="M16 6l6 6-6 6" />
          <path d="M13 4l-2 16" />
        </svg>
      </div>
      <div className="flex flex-col">
        <span className="text-base font-semibold">Asistente Dev</span>
        <span className="text-xs text-ink-muted">Documentación Odoo 19 · RAG agéntico</span>
      </div>
    </div>
  );
}

export function MainNav({ current }: { current: "chat" | "analytics" }) {
  const item = (href: string, label: string, active: boolean) => (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`rounded-lg px-3.5 py-2 font-medium no-underline ${active ? "bg-primary-soft text-primary-hover" : "text-ink-muted hover:text-primary-hover"}`}
    >
      {label}
    </Link>
  );
  return (
    <nav aria-label="Principal" className="flex items-center gap-1">
      {item("/", "Chat", current === "chat")}
      {item("/analytics", "Analytics", current === "analytics")}
    </nav>
  );
}

export default function Header({ threadId, onNewThread }: { threadId: string; onNewThread: () => void }) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-background px-4 py-3.5 sm:px-6">
      <AppMark />
      <MainNav current="chat" />
      <div className="flex items-center gap-2">
        <span title={threadId} className="rounded-lg border border-line px-2.5 py-1.5 font-mono text-xs text-ink-muted">
          <span className="sr-only">Conversación </span>thread {threadId ? shortId(threadId) : "…"}
        </span>
        <button
          type="button"
          onClick={onNewThread}
          className="flex h-10 items-center gap-1.5 rounded-lg border border-primary-muted bg-background px-3.5 text-sm font-medium text-primary-hover hover:bg-primary-soft"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <path d="M12 5v14" />
            <path d="M5 12h14" />
          </svg>
          Nueva conversación
        </button>
      </div>
    </header>
  );
}
