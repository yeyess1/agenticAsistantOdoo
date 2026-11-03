/**
 * SSE client for `POST /query/stream` (U-10, challenge C): `fetch` + ReadableStream (EventSource
 * cannot POST). Event payloads follow ARCHITECTURE §5.3; `final` carries the same
 * `QueryResponse` as the REST endpoint.
 */
import { ApiError, type QueryRequest, type QueryResponse, type SourceRef, type StepRecord } from "./client";

type Base = { run_id: string; thread_id: string; seq: number; ts: string };
type Agent = StepRecord["agent"];

export type AgentEvent =
  | (Base & { type: "node_started"; node: string; agent: Agent })
  | (Base & { type: "node_finished"; node: string; agent: Agent; duration_ms: number; model?: string | null; detail?: Record<string, unknown> })
  | (Base & { type: "token"; node: string; text: string })
  | (Base & { type: "sources"; sources: SourceRef[] })
  | (Base & { type: "interrupt"; kind: string; payload: Record<string, unknown> })
  | (Base & { type: "final"; response: QueryResponse })
  | (Base & { type: "error"; code: string; message: string; node?: string | null });

/** Parse one SSE frame (`event:` / `data:` lines). */
function parseFrame(frame: string): AgentEvent | null {
  const data = frame
    .split("\n")
    .filter((l) => l.startsWith("data:"))
    .map((l) => l.slice(5).trimStart())
    .join("\n");
  if (!data) return null;
  try {
    return JSON.parse(data) as AgentEvent;
  } catch {
    return null;
  }
}

/** Stream one turn; calls `onEvent` per event and resolves with the `final` response. */
export async function queryStream(body: QueryRequest, onEvent: (e: AgentEvent) => void, signal?: AbortSignal): Promise<QueryResponse> {
  let res: Response;
  try {
    res = await fetch("/api/agent/query/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    throw new ApiError(0, "network_error", (err as Error).message);
  }
  if (!res.ok || !res.body) {
    const payload: unknown = await res.json().catch(() => null);
    const error = (payload as { detail?: { error?: { code: string; message: string } } } | null)?.detail?.error;
    throw new ApiError(res.status, error?.code ?? "http_error", error?.message ?? `Error HTTP ${res.status}`);
  }

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  let final: QueryResponse | null = null;
  let failure: ApiError | null = null;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value.replaceAll("\r\n", "\n");
    let cut: number;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const event = parseFrame(buffer.slice(0, cut));
      buffer = buffer.slice(cut + 2);
      if (!event) continue;
      onEvent(event);
      if (event.type === "final") final = event.response;
      else if (event.type === "error" && !event.node) failure = new ApiError(502, event.code, event.message);
    }
  }
  if (final) return final;
  throw failure ?? new ApiError(502, "stream_incomplete", "La respuesta se cortó antes de terminar");
}
