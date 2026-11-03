import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

export interface ContextQualityDistribution {
  high: number;   // fraction 0–1
  medium: number;
  low: number;
  none: number;
}

export interface Keyword {
  keyword: string;
  count: number;
  frequency: number;
}

export interface MetricsData {
  period: {
    from: string | null;
    to: string | null;
  };
  requests: {
    total: number;
    successful: number;
    failed: number;
    success_rate: number;
  };
  users: {
    unique: number;
    scoped_user_id: string | null;
    avg_requests_per_user: number;
  };
  business_metrics: {
    deflection_rate: number;
    deflected_cases: number;
    cost_comparison: {
      rag_total_usd: number;
      human_total_usd: number;
      savings_total_usd: number;
      rag_per_query_usd: number;
      human_per_query_usd: number;
    };
  };
  latency_ms: {
    avg_total: number;
    avg_retrieval: number;
    avg_generation: number;
    max_total: number;
    min_total: number;
  };
  tokens: {
    total_input: number;
    total_output: number;
    total: number;
    avg_input_per_request: number;
    avg_output_per_request: number;
    avg_total_per_request: number;
  };
  costs: {
    total_usd: number;
    avg_per_request_usd: number;
  };
  retrieval: {
    avg_relevance_score: number;
    context_quality_distribution: ContextQualityDistribution;
    mmr_applied_count: number;
  };
  insights: {
    top_keywords: Keyword[];
  };
}

export type TimeWindow = "1h" | "6h" | "24h" | "7d" | "30d";

export const WINDOW_LABELS: Record<TimeWindow, string> = {
  "1h": "Última hora",
  "6h": "Últimas 6h",
  "24h": "Últimas 24h",
  "7d": "Últimos 7 días",
  "30d": "Últimos 30 días",
};

const WINDOW_HOURS: Record<TimeWindow, number> = {
  "1h": 1,
  "6h": 6,
  "24h": 24,
  "7d": 168,
  "30d": 720,
};

export async function getGlobalMetrics(
  window: TimeWindow = "24h"
): Promise<MetricsData> {
  const hours = WINDOW_HOURS[window];
  const { data } = await api.get<MetricsData>(`/api/metrics?hours=${hours}`);
  return data;
}

export async function getUserMetrics(
  userId: string,
  days = 30
): Promise<MetricsData> {
  const { data } = await api.get<MetricsData>(
    `/api/metrics/${userId}?days=${days}`
  );
  return data;
}
