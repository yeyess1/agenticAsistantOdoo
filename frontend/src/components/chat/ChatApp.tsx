"use client";

import { useEffect, useRef, useState } from "react";
import { errorMessage, type Mode } from "@/lib/api/client";
import { queryStream, type AgentEvent } from "@/lib/api/sse";
import DocumentsPanel from "@/components/documents/DocumentsPanel";
import AssistantMessage, { ErrorMessage, PendingMessage } from "./AssistantMessage";
import Composer from "./Composer";
import Header from "./Header";
import type { ChatMessage, LiveState } from "./types";

/** Nodes whose `token` events are the user-facing answer (the rest is internal). */
const STREAMED = new Set(["generator", "direct_answer", "research_llm"]);

/** Event reducer for the in-flight turn (U-10 state machine). */
function applyEvent(live: LiveState, e: AgentEvent): LiveState {
  switch (e.type) {
    case "node_started":
      return {
        ...live,
        steps: [...live.steps, { node: e.node, agent: e.agent, durationMs: null }],
        text: e.node === "research_llm" ? "" : live.text, // each research iteration restarts the draft
      };
    case "node_finished": {
      const steps = [...live.steps];
      const i = steps.findLastIndex((s) => s.node === e.node && s.durationMs == null);
      if (i >= 0) steps[i] = { ...steps[i], durationMs: e.duration_ms };
      return { ...live, steps };
    }
    case "token":
      return STREAMED.has(e.node) ? { ...live, text: live.text + e.text } : live;
    case "sources":
      return { ...live, sources: e.sources };
    default:
      return live;
  }
}

const SUGGESTIONS = [
  "¿Cómo defino un campo computado que sume dos campos?",
  "¿Cómo creo una vista de lista y una de formulario para un modelo?",
  "¿Qué son las reglas de registro (record rules) y cómo se definen?",
  "¿Cómo se estructura un componente OWL?",
];

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`;
}

/** Chat page (U-01): thread id in client state, agentic/linear toggle, documents panel. */
export default function ChatApp() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("agentic");
  const [busy, setBusy] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  const abort = useRef<AbortController | null>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const ask = async (question: string, reuseId?: string) => {
    const thread = threadId ?? newId();
    setThreadId(thread);
    const pendingId = reuseId ?? newId();
    setMessages((m) => [
      ...m.filter((x) => x.id !== pendingId),
      ...(reuseId ? [] : [{ id: newId(), role: "user" as const, text: question }]),
      { id: pendingId, role: "assistant", status: "pending", mode, live: { steps: [], text: "", sources: [] } },
    ]);
    setBusy(true);
    abort.current = new AbortController();
    try {
      const onEvent = (e: AgentEvent) =>
        setMessages((m) => m.map((x) => (x.id === pendingId && x.role === "assistant" && x.status === "pending" ? { ...x, live: applyEvent(x.live, e) } : x)));
      const response = await queryStream({ question, thread_id: thread, mode }, onEvent, abort.current.signal);
      setMessages((m) => m.map((x) => (x.id === pendingId ? { id: pendingId, role: "assistant", status: "done", response } : x)));
    } catch (err) {
      if (abort.current.signal.aborted) return;
      setMessages((m) => m.map((x) => (x.id === pendingId ? { id: pendingId, role: "assistant", status: "error", error: errorMessage(err), mode } : x)));
    } finally {
      setBusy(false);
    }
  };

  const newThread = () => {
    abort.current?.abort();
    setBusy(false);
    setMessages([]);
    setThreadId(null);
  };

  const lastQuestion = (beforeId: string): string | undefined => {
    const idx = messages.findIndex((m) => m.id === beforeId);
    const prev = messages.slice(0, idx).reverse().find((m) => m.role === "user");
    return prev?.role === "user" ? prev.text : undefined;
  };

  return (
    <div className="flex min-h-dvh flex-col md:h-dvh">
      <Header threadId={threadId ?? "nuevo"} onNewThread={newThread} />
      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <DocumentsPanel />
        <main className="flex min-h-0 min-w-0 flex-1 flex-col">
          <div className="flex-1 md:overflow-y-auto">
            <div className="mx-auto flex w-full max-w-[880px] flex-col gap-7 px-4 py-7 sm:px-6" aria-live="polite">
              {messages.length === 0 && (
                <section className="flex flex-col gap-4 py-8">
                  <h1 className="m-0 text-2xl font-semibold">¿En qué te ayudo con Odoo 19?</h1>
                  <p className="m-0 text-ink-muted">
                    Pregunta en español sobre la documentación de desarrollo. El supervisor decide si responde el agente de documentación, el de investigación (foro) o una respuesta directa.
                  </p>
                  <ul className="m-0 grid list-none gap-2 p-0 sm:grid-cols-2">
                    {SUGGESTIONS.map((s) => (
                      <li key={s}>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => void ask(s)}
                          className="h-full w-full rounded-xl border border-line bg-background px-4 py-3 text-left text-sm hover:border-primary-muted hover:bg-primary-soft"
                        >
                          {s}
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
              {messages.map((m) => {
                if (m.role === "user")
                  return (
                    <div key={m.id} className="flex justify-end">
                      <p className="m-0 max-w-[78%] whitespace-pre-wrap rounded-2xl rounded-br-[4px] bg-primary px-4 py-3 text-white">{m.text}</p>
                    </div>
                  );
                if (m.status === "pending") return <PendingMessage key={m.id} id={m.id} linear={m.mode === "linear"} live={m.live} />;
                if (m.status === "error") {
                  const q = lastQuestion(m.id);
                  return <ErrorMessage key={m.id} error={m.error} onRetry={q && !busy ? () => void ask(q, m.id) : undefined} />;
                }
                return <AssistantMessage key={m.id} id={m.id} response={m.response} />;
              })}
              <div ref={bottom} />
            </div>
          </div>
          <Composer busy={busy} mode={mode} onModeChange={setMode} onSend={(q) => void ask(q)} />
        </main>
      </div>
    </div>
  );
}
