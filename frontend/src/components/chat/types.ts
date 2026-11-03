import type { Mode, QueryResponse, SourceRef, StepRecord } from "@/lib/api/client";

/** A node seen in the SSE stream (U-10): running until its `node_finished` arrives. */
export type LiveStep = { node: string; agent: StepRecord["agent"]; durationMs: number | null };

export type LiveState = { steps: LiveStep[]; text: string; sources: SourceRef[] };

export type ChatMessage =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; status: "pending"; mode: Mode; live: LiveState }
  | { id: string; role: "assistant"; status: "done"; response: QueryResponse }
  | { id: string; role: "assistant"; status: "error"; error: string; mode: Mode };
