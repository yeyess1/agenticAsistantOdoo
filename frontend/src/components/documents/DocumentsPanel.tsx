"use client";

import { useCallback, useEffect, useMemo, useState, type DragEvent } from "react";
import { deleteDocument, errorMessage, listDocuments, uploadDocument, type DocumentOut } from "@/lib/api/client";
import { fmtDate, fmtInt } from "@/lib/format";

const MAX_MB = 20;
const ACCEPT = [".pdf", ".md", ".txt"];

function kindOf(doc: DocumentOut): string {
  const name = doc.name.toLowerCase();
  if (doc.mime_type.includes("pdf") || name.endsWith(".pdf")) return "PDF";
  if (doc.mime_type.includes("markdown") || name.endsWith(".md")) return "MD";
  return "TXT";
}

type Upload = { name: string; progress: number; phase: "uploading" | "indexing" };

/** Documents panel (U-02, U-09): upload (drag & drop or picker), list with filter, delete. */
export default function DocumentsPanel() {
  const [docs, setDocs] = useState<DocumentOut[] | null>(null);
  const [filter, setFilter] = useState("");
  const [upload, setUpload] = useState<Upload | null>(null);
  const [notice, setNotice] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [dragging, setDragging] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const list = await listDocuments();
      setDocs(list.items);
    } catch (err) {
      setDocs((d) => d ?? []);
      setNotice({ kind: "error", text: `No se pudo cargar la lista: ${errorMessage(err)}` });
    }
  }, []);

  useEffect(() => {
    // Initial load of the remote list (external system sync).
    void refresh();
  }, [refresh]);

  const send = async (file: File) => {
    setNotice(null);
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!ACCEPT.includes(ext)) return setNotice({ kind: "error", text: "Formato no soportado: usa PDF, MD o TXT." });
    if (file.size > MAX_MB * 1024 * 1024) return setNotice({ kind: "error", text: `El archivo supera ${MAX_MB} MB.` });
    setUpload({ name: file.name, progress: 0, phase: "uploading" });
    try {
      const res = await uploadDocument(file, (p) => setUpload({ name: file.name, progress: p, phase: p >= 1 ? "indexing" : "uploading" }));
      const verb = res.action === "unchanged" ? "sin cambios" : res.action === "updated" ? "actualizado" : "indexado";
      setNotice({ kind: "ok", text: `${res.name}: ${verb} (${fmtInt(res.n_chunks)} chunks).` });
      await refresh();
    } catch (err) {
      setNotice({ kind: "error", text: `${file.name}: ${errorMessage(err)}` });
    } finally {
      setUpload(null);
    }
  };

  const remove = async (doc: DocumentOut) => {
    if (!window.confirm(`¿Eliminar «${doc.name}» y sus ${doc.n_chunks} chunks del índice?`)) return;
    setDeleting(doc.doc_id);
    try {
      await deleteDocument(doc.doc_id);
      setNotice({ kind: "ok", text: `${doc.name}: eliminado.` });
      await refresh();
    } catch (err) {
      setNotice({ kind: "error", text: `${doc.name}: ${errorMessage(err)}` });
    } finally {
      setDeleting(null);
    }
  };

  const onDrop = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && !upload) void send(file);
  };

  const shown = useMemo(() => {
    const q = filter.trim().toLowerCase();
    return (docs ?? []).filter((d) => !q || d.name.toLowerCase().includes(q));
  }, [docs, filter]);
  const totalChunks = (docs ?? []).reduce((acc, d) => acc + d.n_chunks, 0);

  return (
    <aside aria-label="Documentos" className="flex w-full shrink-0 flex-col gap-4 border-b border-line bg-surface p-5 md:w-[320px] md:overflow-y-auto md:border-b-0 md:border-r lg:w-[340px]">
      <div className="flex items-baseline justify-between">
        <h2 className="m-0 text-sm font-semibold uppercase tracking-wide text-ink">Documentos</h2>
        <span className="text-xs text-ink-muted">{docs ? `${fmtInt(docs.length)} · ${fmtInt(totalChunks)} chunks` : "Cargando…"}</span>
      </div>

      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`relative flex cursor-pointer flex-col items-center gap-1.5 rounded-xl border-[1.5px] border-dashed bg-background px-3 py-4 text-center focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-primary ${dragging ? "border-primary bg-primary-soft" : "border-primary-muted"} ${upload ? "cursor-progress opacity-70" : ""}`}
      >
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary" aria-hidden="true">
          <path d="M12 16V4" />
          <path d="M7 9l5-5 5 5" />
          <path d="M4 20h16" />
        </svg>
        <span className="text-sm font-medium text-ink">Arrastra o elige un archivo</span>
        <span className="text-xs text-ink-muted">PDF, MD o TXT · máx. {MAX_MB} MB</span>
        <input
          type="file"
          accept={ACCEPT.join(",")}
          disabled={!!upload}
          aria-label="Subir documento (PDF, MD o TXT, máximo 20 MB)"
          className="absolute h-px w-px opacity-0"
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = "";
            if (file) void send(file);
          }}
        />
      </label>

      {upload && (
        <div className="flex items-center gap-2.5 rounded-[10px] border border-line bg-background px-3 py-2.5">
          <div className="min-w-0 flex-1">
            <div className="truncate text-[13px] font-medium">{upload.name}</div>
            <div
              role="progressbar"
              aria-label={`Progreso de ${upload.name}`}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={upload.phase === "uploading" ? Math.round(upload.progress * 100) : undefined}
              className="mt-1.5 h-1 rounded-sm bg-primary-tint"
            >
              <div className={`h-1 rounded-sm bg-primary ${upload.phase === "indexing" ? "animate-pulse" : ""}`} style={{ width: `${Math.max(5, Math.round(upload.progress * 100))}%` }} />
            </div>
          </div>
          <span className="text-xs text-ink-muted">{upload.phase === "uploading" ? "Subiendo…" : "Indexando…"}</span>
        </div>
      )}

      <p aria-live="polite" className={`m-0 text-xs empty:hidden ${notice?.kind === "error" ? "text-danger" : "text-ink-muted"}`}>
        {notice?.text}
      </p>

      <label className="flex flex-col gap-1 text-xs text-ink-muted">
        Filtrar
        <input
          type="search"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Buscar documento"
          className="h-[38px] rounded-lg border border-primary-muted bg-background px-3 text-sm text-ink placeholder:text-ink-muted"
        />
      </label>

      <ul className="m-0 flex max-h-72 list-none flex-col gap-1.5 overflow-y-auto p-0 md:max-h-none md:overflow-visible">
        {shown.map((d) => (
          <li key={d.doc_id} className="flex items-center gap-2.5 rounded-[10px] border border-line bg-background px-2.5 py-2">
            <span className="w-[34px] shrink-0 rounded-md bg-primary-soft py-0.5 text-center font-mono text-[10px] font-medium text-primary-hover">{kindOf(d)}</span>
            <div className="min-w-0 flex-1">
              <div className="truncate text-[13px] font-medium" title={d.name}>
                {d.name}
              </div>
              <div className="text-xs text-ink-muted">
                {d.status === "indexed" ? `${fmtInt(d.n_chunks)} chunks · ${fmtDate(d.ingested_at ?? d.updated_at)}` : d.status === "failed" ? "Falló la indexación" : "Indexando…"}
              </div>
            </div>
            <button
              type="button"
              aria-label={`Eliminar ${d.name}`}
              disabled={deleting === d.doc_id}
              onClick={() => void remove(d)}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-ink-muted hover:bg-danger-soft hover:text-danger disabled:opacity-50"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M4 7h16" />
                <path d="M10 11v6" />
                <path d="M14 11v6" />
                <path d="M6 7l1 13h10l1-13" />
                <path d="M9 7V4h6v3" />
              </svg>
            </button>
          </li>
        ))}
        {docs && shown.length === 0 && <li className="text-xs text-ink-muted">{docs.length ? "Ningún documento coincide." : "Aún no hay documentos."}</li>}
      </ul>
    </aside>
  );
}
