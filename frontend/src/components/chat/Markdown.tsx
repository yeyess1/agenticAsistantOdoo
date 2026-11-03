"use client";

import { useState, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

type HastNode = { type: string; value?: string; children?: HastNode[]; properties?: Record<string, unknown> };

function hastText(node: HastNode | undefined): string {
  if (!node) return "";
  if (node.type === "text") return node.value ?? "";
  return (node.children ?? []).map(hastText).join("");
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      aria-label={copied ? "Código copiado" : "Copiar código"}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        } catch {
          /* clipboard unavailable (insecure context): nothing to do */
        }
      }}
      className="flex h-7 items-center gap-1.5 rounded-md px-2 text-xs text-code-label hover:bg-code-header"
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <rect x="9" y="9" width="11" height="11" rx="2" />
        <path d="M5 15V5a2 2 0 0 1 2-2h8" />
      </svg>
      <span aria-live="polite">{copied ? "Copiado" : "Copiar"}</span>
    </button>
  );
}

const CITE = /\[(\d{1,3})\](?!\()/g;
const CODE = /(```[\s\S]*?(?:```|$)|`[^`\n]*`)/g;

/** Turn `[n]` markers (outside code) into `#cite-…` links, only for known source numbers. */
function linkCitations(text: string, prefix: string, valid: Set<number>): string {
  return text
    .split(CODE)
    .map((part, i) =>
      i % 2 === 1 ? part : part.replace(CITE, (m, n: string) => (valid.has(Number(n)) ? `[[${n}]](#${prefix}-${n})` : m)),
    )
    .join("");
}

export default function Markdown({ text, citePrefix, sourceNumbers }: { text: string; citePrefix: string; sourceNumbers: number[] }) {
  const valid = new Set(sourceNumbers);
  const components: Components = {
    a({ href, children }) {
      if (href?.startsWith(`#${citePrefix}-`)) {
        const n = href.split("-").at(-1);
        return (
          <a href={href} aria-label={`Fuente ${n}`} className="rounded bg-primary-tint px-1.5 text-xs font-semibold text-primary-hover no-underline hover:bg-primary-muted">
            {children}
          </a>
        );
      }
      return (
        <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary-hover underline underline-offset-2">
          {children}
        </a>
      );
    },
    pre({ node, children }) {
      const code = node?.children?.[0] as HastNode | undefined;
      const classes = (code?.properties?.className as string[] | undefined) ?? [];
      const lang = classes.find((c) => c.startsWith("language-"))?.slice("language-".length) ?? "código";
      return (
        <div className="overflow-hidden rounded-xl border border-code-bg">
          <div className="flex items-center justify-between bg-code-bg px-3 py-1.5 font-mono text-xs text-code-label">
            <span>{lang}</span>
            <CopyButton text={hastText(code)} />
          </div>
          <pre className="m-0 overflow-x-auto bg-code-header px-4 py-3.5 font-mono text-[13px] leading-relaxed text-code-ink">{children}</pre>
        </div>
      );
    },
    code({ className, children }) {
      if (className?.includes("language-") || className?.includes("hljs")) return <code className={className}>{children}</code>;
      return <code className="rounded-[5px] bg-primary-soft px-1.5 py-px font-mono text-[13px] text-primary-strong">{children as ReactNode}</code>;
    },
    table({ children }) {
      return (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">{children}</table>
        </div>
      );
    },
    th: ({ children }) => <th className="border border-line bg-surface px-2 py-1 text-left font-semibold">{children}</th>,
    td: ({ children }) => <td className="border border-line px-2 py-1 align-top">{children}</td>,
    ul: ({ children }) => <ul className="list-disc space-y-1 pl-6">{children}</ul>,
    ol: ({ children }) => <ol className="list-decimal space-y-1 pl-6">{children}</ol>,
    h1: ({ children }) => <h3 className="text-lg font-semibold">{children}</h3>,
    h2: ({ children }) => <h3 className="text-base font-semibold">{children}</h3>,
    h3: ({ children }) => <h4 className="text-base font-semibold">{children}</h4>,
    blockquote: ({ children }) => <blockquote className="border-l-4 border-primary-muted pl-3 text-ink-muted">{children}</blockquote>,
    hr: () => <hr className="border-line" />,
  };
  return (
    <div className="flex flex-col gap-3 break-words [&_p]:m-0">
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[[rehypeHighlight, { detect: false }]]} components={components}>
        {linkCitations(text, citePrefix, valid)}
      </ReactMarkdown>
    </div>
  );
}
