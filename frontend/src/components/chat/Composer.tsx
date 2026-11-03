"use client";

import { useRef, useState, type KeyboardEvent } from "react";
import type { Mode } from "@/lib/api/client";

const MODES: { value: Mode; label: string; hint: string }[] = [
  { value: "agentic", label: "Agéntico", hint: "Supervisor, grader, rewriter y memoria" },
  { value: "linear", label: "Lineal", hint: "Baseline: recuperar → generar, sin memoria" },
];

function ModeToggle({ mode, onChange }: { mode: Mode; onChange: (m: Mode) => void }) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const onKey = (e: KeyboardEvent<HTMLButtonElement>, i: number) => {
    if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) return;
    e.preventDefault();
    const next = (i + (e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 1) + MODES.length) % MODES.length;
    onChange(MODES[next].value);
    refs.current[next]?.focus();
  };
  return (
    <div role="radiogroup" aria-label="Modo de respuesta" className="flex gap-0.5 rounded-lg bg-primary-soft p-0.5">
      {MODES.map((m, i) => {
        const checked = m.value === mode;
        return (
          <button
            key={m.value}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={checked}
            tabIndex={checked ? 0 : -1}
            title={m.hint}
            onClick={() => onChange(m.value)}
            onKeyDown={(e) => onKey(e, i)}
            className={`h-[30px] rounded-md px-3 text-xs ${checked ? "bg-background font-semibold text-primary-hover shadow-sm" : "font-medium text-ink-muted"}`}
          >
            {m.label}
          </button>
        );
      })}
    </div>
  );
}

export default function Composer({ busy, mode, onModeChange, onSend }: { busy: boolean; mode: Mode; onModeChange: (m: Mode) => void; onSend: (q: string) => void }) {
  const [text, setText] = useState("");
  const area = useRef<HTMLTextAreaElement>(null);
  const submit = () => {
    const q = text.trim();
    if (!q || busy) return;
    onSend(q);
    setText("");
    if (area.current) area.current.style.height = "auto";
  };
  return (
    <div className="sticky bottom-0 border-t border-line bg-background">
      <form
        className="mx-auto flex max-w-[880px] flex-col gap-2 px-4 pb-4 pt-3.5 sm:px-6"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <label htmlFor="question" className="sr-only">
          Pregunta
        </label>
        <div className="flex items-end gap-2.5 rounded-[14px] border border-primary-muted bg-background py-2 pl-3.5 pr-2 shadow-sm focus-within:border-primary">
          <textarea
            id="question"
            ref={area}
            rows={1}
            maxLength={4000}
            value={text}
            placeholder="Pregunta sobre el ORM, vistas, OWL, seguridad…"
            onChange={(e) => {
              setText(e.target.value);
              e.target.style.height = "auto";
              e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                submit();
              }
            }}
            className="max-h-[200px] flex-1 resize-none border-0 bg-transparent py-2 text-[15px] text-ink outline-none placeholder:text-ink-muted focus-visible:outline-none"
          />
          <button
            type="submit"
            aria-label="Enviar pregunta"
            disabled={busy || !text.trim()}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[10px] bg-primary text-white hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M5 12h14" />
              <path d="M13 6l6 6-6 6" />
            </svg>
          </button>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-ink-muted">
          <ModeToggle mode={mode} onChange={onModeChange} />
          <span>Respuestas basadas en la documentación oficial de Odoo 19 (CC BY-SA 4.0)</span>
        </div>
      </form>
    </div>
  );
}
