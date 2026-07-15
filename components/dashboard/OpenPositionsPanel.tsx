'use client';

/**
 * Live Open Positions panel.
 *
 * Data source: GET /api/positions/open (FastAPI :8000), fetched via
 * getOpenPositions() in performanceService. Auto-refreshes every 30s.
 *
 * Renders a responsive table on desktop and stacked cards on mobile so it
 * never overflows on small screens. PnL is colored green/red.
 */

import { useOpenPositions } from '@/lib/hooks/usePerformanceData';
import { useTradingMode } from '@/lib/hooks/useTradingMode';
import SkeletonTable from '@/components/shared/widgets/SkeletonTable';
import WidgetEmpty from '@/components/shared/widgets/WidgetEmpty';
import WidgetError from '@/components/shared/widgets/WidgetError';
import type { Position } from '@/lib/services/performanceService';

function formatPrice(v: number): string {
  if (!Number.isFinite(v)) return '-';
  return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function pnlPct(p: Position): number | null {
  if (!Number.isFinite(p.entry_price) || !Number.isFinite(p.mark_price) || p.entry_price === 0) {
    return null;
  }
  const dir = (p.side || '').toLowerCase();
  const raw = (p.mark_price - p.entry_price) / p.entry_price;
  const signed = dir === 'short' ? -raw : raw;
  return signed * 100;
}

export default function OpenPositionsPanel() {
  const { mode } = useTradingMode();
  const { data: positions = [], isLoading, error, dataUpdatedAt, refetch } = useOpenPositions();

  const totalPnl = positions.reduce((sum, p) => sum + (Number.isFinite(p.unrealized_pnl) ? p.unrealized_pnl : 0), 0);
  const lastUpdated = dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString() : null;

  return (
    <section className="glass-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-mq-panel-border bg-black/40">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-bold tracking-wider text-white uppercase">
            Live Open Positions
          </h2>
          <span className={`flex items-center gap-1 text-[10px] font-bold tracking-wider ${
            mode === 'PAPER' ? 'text-mq-warning' : mode === 'LIVE' ? 'text-mq-long' : 'text-mq-muted'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${
              mode === 'PAPER' ? 'bg-mq-warning animate-pulse-slow' : mode === 'LIVE' ? 'bg-mq-long animate-pulse-slow' : 'bg-mq-muted'
            }`} />
            {mode || 'OFF'}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {totalPnl !== 0 && (
            <span
              className={`text-xs font-mono font-semibold ${
                totalPnl >= 0 ? 'text-mq-long' : 'text-mq-short'
              }`}
            >
              Total: {totalPnl >= 0 ? '+' : ''}
              {totalPnl.toFixed(2)} USDT
            </span>
          )}
          {lastUpdated && (
            <span className="text-[10px] text-mq-muted font-mono hidden sm:inline">
              {lastUpdated}
            </span>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="p-4">
        {isLoading ? (
          <SkeletonTable rows={3} columns={6} />
        ) : error ? (
          <WidgetError error={error} onRetry={refetch} />
        ) : positions.length === 0 ? (
          <WidgetEmpty
            message="No open positions"
            description="Synced from Binance Futures every 30s"
          />
        ) : (
          <>
            {/* Desktop / tablet table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[10px] uppercase tracking-wider text-mq-muted border-b border-mq-panel-border">
                    <th className="py-2 pr-3 font-semibold">Symbol</th>
                    <th className="py-2 pr-3 font-semibold">Dir</th>
                    <th className="py-2 pr-3 font-semibold text-right">Entry</th>
                    <th className="py-2 pr-3 font-semibold text-right">Mark</th>
                    <th className="py-2 pr-3 font-semibold text-right">uPnL</th>
                    <th className="py-2 pr-3 font-semibold text-right">PnL %</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((p, i) => {
                    const pnl = Number.isFinite(p.unrealized_pnl) ? p.unrealized_pnl : 0;
                    const pct = pnlPct(p);
                    const profit = pnl >= 0;
                    const dir = (p.side || '').toUpperCase();
                    return (
                      <tr
                        key={`${p.symbol}-${i}`}
                        className="border-b border-mq-panel-border/50 last:border-0 hover:bg-white/[0.02]"
                      >
                        <td className="py-2 pr-3 font-semibold text-white">{p.symbol}</td>
                        <td className="py-2 pr-3">
                          <span
                            className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                              dir === 'SHORT'
                                ? 'bg-mq-short-dim text-mq-short'
                                : dir === 'LONG'
                                  ? 'bg-mq-long-dim text-mq-long'
                                  : 'bg-white/[0.05] text-mq-muted'
                            }`}
                          >
                            {dir || '-'}
                          </span>
                        </td>
                        <td className="py-2 pr-3 text-right font-mono text-neutral-300">
                          {formatPrice(p.entry_price)}
                        </td>
                        <td className="py-2 pr-3 text-right font-mono text-neutral-300">
                          {formatPrice(p.mark_price)}
                        </td>
                        <td className={`py-2 pr-3 text-right font-mono font-semibold ${profit ? 'text-mq-long' : 'text-mq-short'}`}>
                          {profit ? '+' : ''}
                          {pnl.toFixed(2)}
                        </td>
                        <td className={`py-2 pr-3 text-right font-mono ${profit ? 'text-mq-long' : 'text-mq-short'}`}>
                          {pct !== null ? `${profit ? '+' : ''}${pct.toFixed(2)}%` : '-'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="md:hidden space-y-2">
              {positions.map((p, i) => {
                const pnl = Number.isFinite(p.unrealized_pnl) ? p.unrealized_pnl : 0;
                const pct = pnlPct(p);
                const profit = pnl >= 0;
                const dir = (p.side || '').toUpperCase();
                return (
                  <div
                    key={`${p.symbol}-${i}`}
                    className="rounded-md border border-mq-panel-border bg-black/30 p-3"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-bold text-white">{p.symbol}</span>
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                          dir === 'SHORT'
                            ? 'bg-mq-short-dim text-mq-short'
                            : dir === 'LONG'
                              ? 'bg-mq-long-dim text-mq-long'
                              : 'bg-white/[0.05] text-mq-muted'
                        }`}
                      >
                        {dir || '-'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-mq-muted">Entry</span>
                        <div className="font-mono text-neutral-300">{formatPrice(p.entry_price)}</div>
                      </div>
                      <div>
                        <span className="text-mq-muted">Mark</span>
                        <div className="font-mono text-neutral-300">{formatPrice(p.mark_price)}</div>
                      </div>
                      <div>
                        <span className="text-mq-muted">uPnL</span>
                        <div className={`font-mono font-semibold ${profit ? 'text-mq-long' : 'text-mq-short'}`}>
                          {profit ? '+' : ''}
                          {pnl.toFixed(2)}
                        </div>
                      </div>
                      <div>
                        <span className="text-mq-muted">PnL %</span>
                        <div className={`font-mono ${profit ? 'text-mq-long' : 'text-mq-short'}`}>
                          {pct !== null ? `${profit ? '+' : ''}${pct.toFixed(2)}%` : '-'}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </section>
  );
}
