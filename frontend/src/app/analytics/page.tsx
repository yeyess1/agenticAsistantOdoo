"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  getGlobalMetrics,
  type MetricsData,
  type TimeWindow,
} from "@/lib/metricsApi";
import StatCard from "@/components/Dashboard/StatCard";
import Filters from "@/components/Dashboard/Filters";
import ContextQualityChart from "@/components/Dashboard/ContextQualityChart";
import LatencyChart from "@/components/Dashboard/LatencyChart";
import TokenUsageChart from "@/components/Dashboard/TokenUsageChart";
import ConversationsPanel from "@/components/Dashboard/ConversationsPanel";
import DeflectionRateCard from "@/components/Dashboard/DeflectionRateCard";
import CostComparisonCard from "@/components/Dashboard/CostComparisonCard";
import TopKeywordsSection from "@/components/Dashboard/TopKeywordsSection";

function fmt(n: number): string {
  return new Intl.NumberFormat("es-CO").format(n);
}

// ── Skeleton loader ──────────────────────────────────────────────────────────
function SkeletonCard({ className = "" }: { className?: string }) {
  return (
    <div
      className={`bg-white dark:bg-zinc-900 rounded-2xl border border-line dark:border-zinc-800 p-6 shadow-sm animate-pulse ${className}`}
    >
      <div className="h-3 bg-gray-200 dark:bg-zinc-700 rounded w-1/3 mb-4" />
      <div className="h-8 bg-gray-200 dark:bg-zinc-700 rounded w-1/2 mb-2" />
      <div className="h-3 bg-primary-soft dark:bg-zinc-800 rounded w-2/3" />
    </div>
  );
}

// ── Icons ────────────────────────────────────────────────────────────────────
const icons = {
  chat: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
    </svg>
  ),
  users: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
    </svg>
  ),
  clock: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  dollar: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
};

// ── Main page ─────────────────────────────────────────────────────────────────
export default function AnalyticsPage() {
  const [data, setData] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeWindow, setTimeWindow] = useState<TimeWindow>("24h");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = useCallback(
    async (window: TimeWindow) => {
      setLoading(true);
      setError(null);
      try {
        const result = await getGlobalMetrics(window);
        setData(result);
        setLastUpdated(new Date());
      } catch (err) {
        setError("No se pudo cargar las métricas. Verifica que el backend esté disponible.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    fetchData(timeWindow);
  }, [timeWindow, fetchData]);

  function handleWindowChange(w: TimeWindow) {
    setTimeWindow(w);
  }

  function handleRefresh() {
    fetchData(timeWindow);
  }

  const hasData = data && data.requests.total > 0;

  return (
    <div className="min-h-screen bg-surface dark:bg-zinc-950 flex flex-col">
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <header className="bg-primary text-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Left: back + branding */}
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="flex items-center gap-1 text-white/80 hover:text-white transition-colors text-sm"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
              </svg>
              Chat
            </Link>
            <div className="h-4 w-px bg-white/20" />
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/20 text-xs font-bold">
                BB
              </div>
              <div>
                <h1 className="text-sm font-semibold leading-tight">Analytics Dashboard</h1>
                <p className="text-xs text-white/80">Métricas del asistente</p>
              </div>
            </div>
          </div>

          {/* Right: live badge */}
          <div className="flex items-center gap-2 text-xs text-white/80">
            <span className="h-2 w-2 rounded-full bg-green-400 animate-pulse" />
            Sistema activo
          </div>
        </div>
      </header>

      {/* ── Content ───────────────────────────────────────────────────────── */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 flex flex-col gap-8">

        {/* Page title + filters */}
        <div className="flex flex-col gap-4">
          <div>
            <h2 className="text-xl font-bold text-ink dark:text-white">
              Métricas en Tiempo Real
            </h2>
            <p className="text-sm text-ink-muted dark:text-gray-400 mt-0.5">
              Calidad RAG, conversaciones, latencia y uso de tokens
            </p>
          </div>
          <Filters
            window={timeWindow}
            onWindowChange={handleWindowChange}
            onRefresh={handleRefresh}
            loading={loading}
            lastUpdated={lastUpdated}
          />
        </div>

        {/* Error state */}
        {error && (
          <div className="rounded-2xl border border-red-100 bg-red-50 dark:bg-red-900/20 dark:border-red-900 p-5 text-sm text-red-600 dark:text-red-400 flex items-start gap-3">
            <svg className="h-5 w-5 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
            {error}
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && !hasData && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 mb-4">
              <svg className="h-8 w-8 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
              </svg>
            </div>
            <h3 className="text-base font-semibold text-ink dark:text-gray-300">
              Sin datos en este período
            </h3>
            <p className="text-sm text-ink-muted mt-1">
              Inicia conversaciones con el agente para ver métricas aquí.
            </p>
            <Link
              href="/"
              className="mt-4 inline-flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-hover transition-colors"
            >
              Ir al Chat
            </Link>
          </div>
        )}

        {/* ── Loading skeletons ─────────────────────────────────────────── */}
        {loading && (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <SkeletonCard className="h-72" />
              <SkeletonCard className="h-72" />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <SkeletonCard className="h-64" />
              <SkeletonCard className="h-64" />
            </div>
          </>
        )}

        {/* ── Dashboard content ─────────────────────────────────────────── */}
        {!loading && hasData && data && (
          <>
            {/* Row 1 — Top Keywords (Primary insight) */}
            <TopKeywordsSection keywords={data.insights?.top_keywords ?? []} />

            {/* Row 2 — Business KPIs: Cost + Deflection */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <CostComparisonCard
                ragTotalUsd={data.business_metrics?.cost_comparison?.rag_total_usd ?? 0}
                humanTotalUsd={data.business_metrics?.cost_comparison?.human_total_usd ?? 0}
                savingsTotalUsd={data.business_metrics?.cost_comparison?.savings_total_usd ?? 0}
                ragPerQueryUsd={data.business_metrics?.cost_comparison?.rag_per_query_usd ?? 0}
                humanPerQueryUsd={data.business_metrics?.cost_comparison?.human_per_query_usd ?? 9}
              />
              <DeflectionRateCard
                deflectionRate={data.business_metrics?.deflection_rate ?? 0}
                deflectedCases={data.business_metrics?.deflected_cases ?? 0}
                totalCases={data.requests.total}
              />
            </div>

            {/* Row 3 — Performance: Latency + Context Quality */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <LatencyChart
                avgTotal={data.latency_ms.avg_total}
                avgRetrieval={data.latency_ms.avg_retrieval}
                avgGeneration={data.latency_ms.avg_generation}
                maxTotal={data.latency_ms.max_total}
              />
              <ContextQualityChart
                distribution={data.retrieval.context_quality_distribution}
                avgScore={data.retrieval.avg_relevance_score}
                mmrCount={data.retrieval.mmr_applied_count}
                totalRequests={data.requests.total}
              />
            </div>

            {/* Row 4 — Usage: Conversations + Tokens */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ConversationsPanel
                total={data.requests.total}
                successful={data.requests.successful}
                failed={data.requests.failed}
                successRate={data.requests.success_rate}
                uniqueUsers={data.users.unique}
                avgPerUser={data.users.avg_requests_per_user}
                periodFrom={data.period.from}
                periodTo={data.period.to}
              />
              <TokenUsageChart
                totalInput={data.tokens.total_input}
                totalOutput={data.tokens.total_output}
                avgInput={data.tokens.avg_input_per_request}
                avgOutput={data.tokens.avg_output_per_request}
                totalCost={data.costs.total_usd}
                avgCostPerRequest={data.costs.avg_per_request_usd}
              />
            </div>
          </>
        )}
      </main>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer className="border-t border-line dark:border-zinc-800 bg-white dark:bg-zinc-900 py-4">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between text-xs text-ink-muted">
          <span>Asistente Dev · Analytics</span>
          <span>Powered by Gemini + BGE-M3 + Supabase pgvector</span>
        </div>
      </footer>
    </div>
  );
}
