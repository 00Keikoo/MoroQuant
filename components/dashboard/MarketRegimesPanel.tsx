'use client';

/**
 * Current Market Regimes panel.
 *
 * Data source: each active symbol's latest 1h signal `regime` field, fetched
 * via getCurrentRegimes(). Auto-refreshes every 5 minutes.
 *
 * Regime badge colors (task spec):
 *   Trending → green   (text-mq-long)
 *   Choppy   → yellow  (text-mq-warning)
 *   Volatile → red     (text-mq-short)
 *   Range    → blue    (text-mq-accent)
 */

import { useCurrentRegimes } from '@/lib/hooks/usePerformanceData';
import SkeletonCard from '@/components/shared/widgets/SkeletonCard';
import WidgetEmpty from '@/components/shared/widgets/WidgetEmpty';
import WidgetError from '@/components/shared/widgets/WidgetError';
import { ACTIVE_PAIRS } from '@/lib/services/performanceService';

type RegimeKind = 'trending' | 'choppy' | 'volatile' | 'range' | 'unknown';

const REGIME_STYLE: Record<RegimeKind, { label: string; cls: string; dot: string }> = {
  trending: { label: 'Trending', cls: 'bg-mq-long-dim text-mq-long', dot: 'bg-mq-long' },
  choppy: { label: 'Choppy', cls: 'bg-mq-warning-dim text-mq-warning', dot: 'bg-mq-warning' },
  volatile: { label: 'Volatile', cls: 'bg-mq-short-dim text-mq-short', dot: 'bg-mq-short' },
  range: { label: 'Range', cls: 'bg-mq-accent-dim/30 text-mq-accent', dot: 'bg-mq-accent' },
  unknown: { label: 'Unknown', cls: 'bg-white/[0.05] text-mq-muted', dot: 'bg-mq-muted' },
};

function classifyRegime(raw: string): { kind: RegimeKind; label: string } {
  if (!raw || raw === 'unknown') return { kind: 'unknown', label: 'Unknown' };
  const label = raw.toLowerCase();
  if (label.includes('trend')) return { kind: 'trending', label: raw };
  if (label.includes('chop')) return { kind: 'choppy', label: raw };
  if (label.includes('volat') || label.includes('high_vol')) return { kind: 'volatile', label: raw };
  if (label.includes('range') || label.includes('rang')) return { kind: 'range', label: raw };
  // Fallback: unknown regime kinds still render with their raw label.
  return { kind: 'unknown', label: raw };
}

export default function MarketRegimesPanel() {
  const { data: regimes = [], isLoading, error, refetch } = useCurrentRegimes();

  return (
    <section className="glass-card overflow-hidden flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-mq-panel-border bg-black/40">
        <h2 className="text-sm font-bold tracking-wider text-white uppercase">
          Current Market Regimes
        </h2>
        <span className="text-[10px] text-mq-muted font-mono">5m refresh</span>
      </div>

      {/* Body */}
      <div className="p-4 flex-1">
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {ACTIVE_PAIRS.map((_, i) => (
              <SkeletonCard key={i} height="h-9" />
            ))}
          </div>
        ) : error ? (
          <WidgetError error={error} onRetry={refetch} />
        ) : regimes.length === 0 ? (
          <WidgetEmpty message="No regime data available" />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {regimes.map((r) => {
              const { kind, label } = classifyRegime(r.regime);
              const style = REGIME_STYLE[kind];
              return (
                <div
                  key={r.symbol}
                  className="flex items-center justify-between rounded-md border border-mq-panel-border bg-black/30 px-3 py-2 hover:border-white/10 transition-colors"
                >
                  <span className="text-xs font-bold text-white">{r.symbol}</span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded flex items-center gap-1 ${style.cls}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
                    {label}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
