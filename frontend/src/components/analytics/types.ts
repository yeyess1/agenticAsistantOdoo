/** Shape of `public/eval/latest.json` (slim report written by `eval/runners/report.py`, E-12). */
export type Mode = "agentic" | "linear";
export type Agent = "docs" | "research" | "direct";

export interface Summary {
  n: number;
  mean: number | null;
  p50: number | null;
  p95: number | null;
}

export interface ScopeAggregate {
  n: number;
  errors: number;
  faithfulness: Summary;
  answer_relevancy: Summary;
  correctness_f1: Summary;
  correctness_precision: number | null;
  correctness_recall: number | null;
  behaviour_pass_rate: number | null;
  behaviour_n: number;
  context_precision: number | null;
  context_recall: number | null;
  context_chunks: number | null;
  citation_correctness: number | null;
  latency_ms: Summary;
  input_tokens: number | null;
  output_tokens: number | null;
  generator_input_tokens: number | null;
  cost_usd_mean: number | null;
  cost_usd_total: number | null;
}

export type Scope = "all" | "docs_questions" | "covered" | "follow_up" | "not_covered" | "out_of_scope";

export interface RoutingReport {
  n: number;
  correct: number;
  accuracy: number | null;
  labels: Agent[];
  confusion: Record<Agent, Record<Agent | "none", number>>;
  per_class: Record<Agent, { precision: number | null; recall: number | null; f1: number | null; support: number }>;
}

export interface RankingAggregate {
  n: number;
  "recall@1": number | null;
  "recall@3": number | null;
  "recall@5": number | null;
  "recall@10": number | null;
  "precision@1": number | null;
  "precision@5": number | null;
  "precision@10": number | null;
  mrr: number | null;
  "context_precision@10": number | null;
}

export interface HnswSweep {
  hnsw_ef: number;
  "recall@1": number;
  "recall@5": number;
  "recall@10": number;
  "min_recall@10": number;
  latency_ms_p50: number;
  latency_ms_p95: number;
}

export interface NodeStats {
  calls: number;
  duration_ms_mean: number | null;
  duration_ms_p95: number | null;
  input_tokens_mean: number | null;
  output_tokens_mean: number | null;
  cost_usd_total: number | null;
  cost_share: number | null;
}

export interface QuestionRun {
  error?: boolean;
  answered_by?: Agent | null;
  route?: Agent | null;
  delegated?: boolean;
  n_rewrites?: number;
  latency_ms?: number | null;
  usage?: { input_tokens: number; output_tokens: number; cost_usd: number };
  context_precision?: number | null;
  context_chunks?: number;
  citation_correctness?: number | null;
  faithfulness?: number | null;
  answer_relevancy?: number | null;
  correctness_f1?: number | null;
  behaviour_passed?: boolean | null;
}

export interface QuestionRow {
  id: string;
  category: "covered" | "not_covered" | "out_of_scope" | "follow_up";
  question: string;
  expected_agent: Agent;
  retrieval: Record<"es" | "en", { "recall@10": number | null; rr: number | null }> | null;
  runs: Partial<Record<Mode, QuestionRun>>;
}

export interface EvalReport {
  run_meta: {
    started_at: string;
    git_sha: string;
    n_items: number;
    golden_counts: Record<string, number>;
    models: Record<string, string>;
    judge_usage: { calls: number; cost_usd: number };
  };
  aggregates: Partial<Record<Mode, Partial<Record<Scope, ScopeAggregate>>>>;
  routing: Partial<Record<Mode, { final_agent: RoutingReport; router_decision: RoutingReport } | null>>;
  retrieval: { es: RankingAggregate; en: RankingAggregate } | null;
  hnsw_vs_exact: {
    n_queries: number;
    top_k: number;
    collection: { points_count: number; indexed_vectors_count: number; segments_count: number; m: number; ef_construct: number };
    exact: { latency_ms_p50: number; latency_ms_p95: number };
    hnsw: HnswSweep[];
  } | null;
  comparison: {
    paired_docs_questions?: Record<
      "faithfulness" | "answer_relevancy" | "correctness_f1",
      { n: number; agentic: number | null; linear: number | null; agentic_wins: number; linear_wins: number }
    >;
  };
  rewriter: { expects_rewrite_n: number; expects_rewrite_triggered: string[]; triggered_without_expectation: string[] };
  node_evidence: {
    contextualize?: { id: string; raw: { "recall@10": number; rr: number }; standalone: { "recall@10": number; rr: number } }[];
    rewriter?: { id: string; before: { "recall@10": number; rr: number }; after: { "recall@10": number; rr: number } }[];
  };
  per_node: Partial<Record<Mode, Record<string, NodeStats>>>;
  costs: { agent_usd: Partial<Record<Mode, number>>; judge_usd: number; total_usd: number };
  per_question: QuestionRow[];
}
