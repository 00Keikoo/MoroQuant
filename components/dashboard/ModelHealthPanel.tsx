'use client';

/**
 * Production Model Health panel.
 *
 * Data source: GET /api/models/{symbol}/{timeframe}/drift (FastAPI :8000),
 * fanned out over all active production models via
 * getModelDriftForActiveModels().
 *
 * Drift computation is expensive, so this panel fetches once on mount and
 * on explicit refresh (no tight auto-refresh loop).
 *
 * Status thresholds (task spec):
 *   overall_score < 0.2  → green
 *   0.2 ≤ score < 0.4    → yellow
 *   score ≥ 0.4          → red
 */

import { useModelHealth } from '@/lib/hooks/usePerformanceData';
import SkeletonCard from '@/components/shared/widgets/SkeletonCard';
import WidgetEmpty from '@/components/shared/widgets/WidgetEmpty';
import WidgetError from '@/components/shared/widgets/WidgetError';
import type { ModelDriftSummary } from '@/lib/services/performanceService';

type Status = ModelDriftSummary['health_status'];

const STATUS_STYLE: Record<Status, { dot: string; label: string; text: string }> = {
  green: { dot: 'bg-mq-long', label: 'Healthy', text: 'text-mq-long' },
  yellow: { dot: 'bg-mq-warning', label: 'Warning', text: 'text-mq-warning' },
  red: { dot: 'bg-mq-short', label: 'Critical', text: 'text-mq-short' },
  unknown: { dot: 'bg-neutral-500', label: 'Unknown', text: 'text-neutral-500' },
};

interface ModelHealthPanelProps {
  /** Compact variant hides the per-card score bars (used inside analytics tiles). */
  compact?: boolean;
}

export default function ModelHealthPanel({ compact = false }: ModelHealthPanelProps) {
  const { data: models = [], isLoading, isFetching, error, refetch } = useModelHealth();

  const summary = {
    green: models.filter((m) => m.health_status === 'green').length,
    yellow: models.filter((m) => m.health_status === 'yellow').length,
    red: models.filter((m) => m.health_status === 'red').length,
  };

  return (
    <section className="glass-card overflow-hidden flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-mq-panel-border bg-black/40">
        <h2 className="text-sm font-bold tracking-wider text-white uppercase">
          Production Model Health
        </h2>
        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="text-[10px] font-semibold text-mq-muted hover:text-white transition-colors disabled:opacity-50 flex items-center gap-1 cursor-pointer"
        >
          <svg
            className={`w-3 h-3 ${isFetching ? 'animate-spin text-mq-accent' : ''}`}
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {isFetching ? 'Scanning' : 'Refresh'}
        </button>
      </div>

      {/* Summary chips */}
      {!compact && !isLoading && !error && models.length > 0 && (
        <div className="flex items-center gap-3 px-4 py-2 border-b border-mq-panel-border">
          <span className="flex items-center gap-1 text-[10px] font-semibold text-mq-long">
            <span className="w-1.5 h-1.5 rounded-full bg-mq-long" /> {summary.green} Healthy
          </span>
          <span className="flex items-center gap-1 text-[10px] font-semibold text-mq-warning">
            <span className="w-1.5 h-1.5 rounded-full bg-mq-warning" /> {summary.yellow} Warning
          </span>
          <span className="flex items-center gap-1 text-[10px] font-semibold text-mq-short">
            <span className="w-1.5 h-1.5 rounded-full bg-mq-short" /> {summary.red} Critical
          </span>
        </div>
      )}

      {/* Body */}
      <div className="p-4 flex-1">
        {isLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <SkeletonCard key={i} height="h-16" />
            ))}
          </div>
        ) : error ? (
          <WidgetError error={error} onRetry={refetch} />
        ) : models.length === 0 ? (
          <WidgetEmpty
            message="No model drift data available"
            description="Ensure the ML service is running"
          />
        ) : (
          <div className={`grid gap-2 ${compact ? 'grid-cols-2 sm:grid-cols-3' : 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5'}`}>
            {models.map((m) => {
              const style = STATUS_STYLE[m.health_status];
              return (
                <div
                  key={`${m.symbol}-${m.timeframe}`}
                  className="rounded-md border border-mq-panel-border bg-black/30 p-3 hover:border-white/10 transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-white truncate">{m.symbol}</span>
                    <span className="text-[10px] text-mq-muted font-mono">{m.timeframe}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className={`w-2 h-2 rounded-full ${style.dot} shrink-0`} />
                    <span className={`text-[11px] font-semibold ${style.text}`}>{style.label}</span>
                    <span className="text-[10px] text-mq-muted font-mono ml-auto">
                      {m.overall_score !== null ? (m.overall_score * 100).toFixed(0) : '--'}%
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
