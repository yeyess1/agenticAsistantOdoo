/**
 * Typed client of the agent and ingestion APIs through the same-origin proxy (`/api/*`).
 * Types come from the FastAPI OpenAPI specs (U-05): `npm run gen:api` regenerates them.
 */
import type { components as AgentComponents } from "./agent.gen";
import type { components as IngestionComponents } from "./ingestion.gen";

type AgentSchemas = AgentComponents["schemas"];
type IngestionSchemas = IngestionComponents["schemas"];

export type QueryRequest = AgentSchemas["QueryRequest"];
export type QueryResponse = AgentSchemas["QueryResponse"];
export type SourceRef = AgentSchemas["SourceRef"];
export type StepRecord = AgentSchemas["StepRecord"];
export type Mode = NonNullable<QueryRequest["mode"]>;
export type InsightsResponse = AgentSchemas["InsightsResponse"];
export type DocumentOut = IngestionSchemas["DocumentOut"];
export type DocumentList = IngestionSchemas["DocumentList"];
export type IngestResult = IngestionSchemas["IngestResult"];

const AGENT = "/api/agent";
const INGESTION = "/api/ingestion";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Errors are `{detail: {error: {code, message}}}` (typed) or FastAPI's 422 `{detail: [...]}`. */
function toApiError(status: number, body: unknown): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (detail && typeof detail === "object" && "error" in detail) {
    const { code, message } = (detail as { error: { code: string; message: string } }).error;
    return new ApiError(status, code, message);
  }
  if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: string; loc?: unknown[] } | undefined;
    return new ApiError(status, "validation_error", first?.msg ?? "Solicitud inválida");
  }
  return new ApiError(status, "http_error", `Error HTTP ${status}`);
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch (err) {
    throw new ApiError(0, "network_error", (err as Error).message);
  }
  if (res.status === 204) return undefined as T;
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok) throw toApiError(res.status, body);
  return body as T;
}

export function query(body: QueryRequest, signal?: AbortSignal): Promise<QueryResponse> {
  return request<QueryResponse>(`${AGENT}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
}

export type InsightsFilters = { origin?: "ui" | "eval"; mode?: Mode; days?: number };

export function getInsights(filters: InsightsFilters = {}, signal?: AbortSignal): Promise<InsightsResponse> {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(filters)) if (v !== undefined) params.set(k, String(v));
  const qs = params.toString();
  return request<InsightsResponse>(`${AGENT}/insights${qs ? `?${qs}` : ""}`, { cache: "no-store", signal });
}

export function listDocuments(): Promise<DocumentList> {
  return request<DocumentList>(`${INGESTION}/documents?limit=500`);
}

export function deleteDocument(docId: string): Promise<void> {
  return request<void>(`${INGESTION}/documents/${encodeURIComponent(docId)}`, { method: "DELETE" });
}

/** Multipart upload with progress (XHR: fetch has no upload progress events). */
export function uploadDocument(file: File, onProgress?: (fraction: number) => void): Promise<IngestResult> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${INGESTION}/documents`);
    xhr.responseType = "json";
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress?.(e.loaded / e.total);
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve(xhr.response as IngestResult);
      else reject(toApiError(xhr.status, xhr.response));
    };
    xhr.onerror = () => reject(new ApiError(0, "network_error", "No se pudo conectar con el servicio"));
    const form = new FormData();
    form.append("file", file);
    xhr.send(form);
  });
}

/** Human message for an API error (Spanish UI). */
export function errorMessage(err: unknown): string {
  if (!(err instanceof ApiError)) return "Error inesperado";
  switch (err.code) {
    case "file_too_large":
      return "El archivo supera el tamaño máximo (20 MB).";
    case "unsupported_type":
      return "Formato no soportado: usa PDF, MD o TXT.";
    case "unprocessable_document":
      return "No se pudo leer el documento (vacío o dañado).";
    case "upstream_timeout":
      return "El servicio tardó demasiado en responder. Intenta de nuevo.";
    case "llm_unavailable":
      return "El modelo de lenguaje no respondió. Intenta de nuevo en un momento.";
    case "retrieval_unavailable":
    case "embeddings_unavailable":
      return "El servicio de búsqueda no está disponible.";
    case "network_error":
    case "upstream_unreachable":
      return "No se pudo conectar con el servicio.";
    case "not_found":
      return "El documento ya no existe.";
    case "document_deleted_during_ingestion":
      return "El documento se eliminó mientras se indexaba; no quedó nada guardado. Súbelo de nuevo si lo necesitas.";
    default:
      return err.message || `Error ${err.status}`;
  }
}
