"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { askQuestion, clearHistory, type Message, type Source } from "@/lib/api";

const USER_ID = "demo-user";

// ── App mark (brand-agnostic code icon) ───────────────────────────────────────
function AppMark({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M8 6l-6 6 6 6" />
      <path d="M16 6l6 6-6 6" />
      <path d="M13 4l-2 16" />
    </svg>
  );
}

// ── Sources ───────────────────────────────────────────────────────────────────
function Sources({ sources }: { sources: Source[] }) {
  if (!sources.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {sources.map((s, i) => (
        <a
          key={i}
          href={s.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 rounded-full bg-primary-soft border border-primary-tint px-2.5 py-1 text-xs text-primary-hover hover:bg-primary-tint transition-colors dark:bg-primary/30 dark:text-primary-muted dark:border-primary-hover"
        >
          <svg className="h-3 w-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.172 13.828a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          {s.title || `Fuente ${i + 1}`}
        </a>
      ))}
    </div>
  );
}

// ── Message Bubble ─────────────────────────────────────────────────────────────
function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      {!isUser && (
        <div className="flex-shrink-0 h-8 w-8 rounded-full bg-primary flex items-center justify-center shadow-sm mt-1">
          <AppMark className="h-4 w-4 text-white" />
        </div>
      )}

      {/* Bubble */}
      <div
        className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${isUser
            ? "bg-primary text-white rounded-tr-sm"
            : "bg-white border border-line text-ink rounded-tl-sm dark:bg-zinc-800 dark:border-zinc-700 dark:text-gray-200"
          }`}
      >
        <p className="whitespace-pre-wrap">{msg.content}</p>
        {!isUser && msg.sources && <Sources sources={msg.sources} />}
        {msg.timestamp && (
          <p className={`text-[10px] mt-1.5 ${isUser ? "text-white/80 text-right" : "text-ink-muted"}`}>
            {new Date(msg.timestamp).toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit" })}
          </p>
        )}
      </div>
    </div>
  );
}

// ── Typing Indicator ───────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 h-8 w-8 rounded-full bg-primary flex items-center justify-center shadow-sm">
        <AppMark className="h-4 w-4 text-white" />
      </div>
      <div className="bg-white border border-line rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm dark:bg-zinc-800 dark:border-zinc-700">
        <div className="flex gap-1.5 items-center h-4">
          <span className="h-2 w-2 rounded-full bg-primary animate-bounce [animation-delay:0ms]" />
          <span className="h-2 w-2 rounded-full bg-primary animate-bounce [animation-delay:150ms]" />
          <span className="h-2 w-2 rounded-full bg-primary animate-bounce [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  );
}

// ── Empty State ────────────────────────────────────────────────────────────────
function EmptyState() {
  const suggestions = [
    "¿Cómo defino un campo computado en el ORM?",
    "¿Cómo hereda una vista para añadir un campo?",
    "¿Qué diferencia hay entre ir.rule y los grupos de acceso?",
    "¿Cómo creo un componente OWL con estado?",
  ];

  return (
    <div className="flex flex-col items-center justify-center h-full px-4 pb-8">
      {/* Logo central */}
      <div className="flex flex-col items-center mb-8">
        <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-primary shadow-lg mb-4">
          <AppMark className="h-9 w-9 text-white" />
        </div>
        <h2 className="text-lg font-bold text-ink dark:text-white">
          Asistente Dev
        </h2>
        <p className="text-sm text-ink-muted dark:text-gray-400 mt-1 text-center max-w-xs">
          Pregunta sobre la documentación de desarrollo de Odoo 19
        </p>
      </div>

      {/* Suggested questions */}
      <div className="w-full max-w-sm space-y-2">
        <p className="text-xs font-semibold text-ink-muted uppercase tracking-wide mb-3">
          Prueba con
        </p>
        {suggestions.map((s, i) => (
          <button
            key={i}
            className="w-full text-left text-sm text-ink dark:text-gray-300 bg-white dark:bg-zinc-800 border border-line dark:border-zinc-700 rounded-xl px-4 py-3 hover:border-primary hover:text-primary dark:hover:border-primary-muted dark:hover:text-primary-muted transition-all shadow-sm"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Main Chat ──────────────────────────────────────────────────────────────────
export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSubmit(e: React.SyntheticEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    const userMsg: Message = {
      role: "user",
      content: question,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await askQuestion(USER_ID, question);
      const assistantMsg: Message = {
        role: "assistant",
        content: res.answer,
        timestamp: res.timestamp,
        sources: res.sources,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errorMsg: Message = {
        role: "assistant",
        content: "Lo siento, hubo un error al procesar tu consulta. Por favor intenta de nuevo.",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  }

  async function handleClear() {
    try {
      await clearHistory(USER_ID);
    } catch {
      // best-effort
    }
    setMessages([]);
  }

  return (
    <div className="flex flex-col h-full bg-surface dark:bg-zinc-950">

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <header className="flex-shrink-0 bg-primary shadow-lg relative overflow-hidden">
        {/* Decorative background elements */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-6 -right-6 h-24 w-24 rounded-full bg-white/5" />
          <div className="absolute -bottom-8 -left-4 h-20 w-20 rounded-full bg-white/5" />
        </div>

        <div className="relative flex items-center justify-between px-4 py-3">
          {/* Logo + branding */}
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white shadow-sm">
              <AppMark className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-white leading-tight">Asistente Dev</h1>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse" />
                <p className="text-xs text-white/80">Documentación Odoo 19 · RAG agéntico</p>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <Link
              href="/analytics"
              className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-white bg-white/10 hover:bg-white/20 transition-colors"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
              </svg>
              Métricas
            </Link>
            {messages.length > 0 && (
              <button
                onClick={handleClear}
                className="rounded-lg px-3 py-1.5 text-xs font-medium text-white bg-white/10 hover:bg-white/20 transition-colors"
              >
                Nueva sesión
              </button>
            )}
          </div>
        </div>
      </header>

      {/* ── Messages ────────────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.length === 0 && <EmptyState />}
        {messages.map((msg, i) => (
          <MessageBubble key={i} msg={msg} />
        ))}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* ── Input ───────────────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 border-t border-line dark:border-zinc-800 bg-white dark:bg-zinc-900 px-4 py-3">
        <form onSubmit={handleSubmit} className="flex items-end gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Pregunta sobre el ORM, vistas, OWL, seguridad…"
            disabled={loading}
            className="flex-1 rounded-xl border border-line dark:border-zinc-700 bg-surface dark:bg-zinc-800 px-4 py-2.5 text-sm text-ink dark:text-white placeholder-ink-muted outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:opacity-50 transition-all resize-none"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="flex-shrink-0 h-10 w-10 flex items-center justify-center rounded-xl bg-primary text-white hover:bg-primary-hover disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </form>
        <p className="text-center text-[10px] text-ink-muted mt-2">
          Respuestas basadas en la documentación oficial de Odoo 19 (CC BY-SA 4.0)
        </p>
      </div>
    </div>
  );
}
