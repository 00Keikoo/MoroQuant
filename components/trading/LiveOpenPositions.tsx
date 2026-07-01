'use client';

import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Clock } from 'lucide-react';
import { getLivePaperPositions } from '@/lib/api/ml-trading';
import type { LivePaperPosition } from '@/lib/types/ml';

const REFRESH_MS = 5_000; // 5 seconds for live updates

export default function LiveOpenPositions() {
  const [positions, setPositions] = useState<LivePaperPosition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPositions = async () => {
      try {
        const data = await getLivePaperPositions();
        setPositions(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    };

    fetchPositions();
    const interval = setInterval(fetchPositions, REFRESH_MS);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="glass-card p-4 flex items-center justify-center min-h-[200px]">
        <div className="w-6 h-6 border-2 border-mq-accent/20 border-t-mq-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card p-4">
        <h3 className="text-sm font-semibold text-white tracking-wide uppercase mb-2">
          Live Open Positions
        </h3>
        <div className="text-xs text-red-400">{error}</div>
      </div>
    );
  }

  if (positions.length === 0) {
    return (
      <div className="glass-card p-4">
        <h3 className="text-sm font-semibold text-white tracking-wide uppercase mb-2">
          Live Open Positions
        </h3>
        <div className="text-xs text-neutral-500">No open positions</div>
      </div>
    );
  }

  const fmtPrice = (v: number) => {
    const abs = Math.abs(v);
    const digits = abs >= 1000 ? 2 : abs >= 1 ? 4 : 6;
    return v.toLocaleString(undefined, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  };

  const fmtPnl = (v: number) => {
    const sign = v >= 0 ? '+' : '';
    return `${sign}$${v.toFixed(2)}`;
  };

  const fmtRoi = (v: number) => {
    const sign = v >= 0 ? '+' : '';
    return `${sign}${v.toFixed(2)}%`;
  };

  const fmtDuration = (hours: number) => {
    if (hours < 1) return `${Math.round(hours * 60)}m`;
    if (hours < 24) return `${hours.toFixed(1)}h`;
    const days = Math.floor(hours / 24);
    const remainingHours = Math.round(hours % 24);
    return `${days}d ${remainingHours}h`;
  };

  return (
    <div className="glass-card overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-mq-panel-border bg-black/40">
        <div className="flex items-baseline gap-2">
          <h3 className="text-sm font-bold text-white tracking-wider uppercase">
            Live Open Positions
          </h3>
          <span className="text-[10px] text-neutral-500 font-mono">
            {positions.length} active · updates every 5s
          </span>
        </div>
      </div>

      <div className="divide-y divide-mq-panel-border">
        {positions.map((pos) => {
          const isLong = pos.direction === 'LONG';
          const pnlPositive = pos.floating_pnl >= 0;

          return (
            <div
              key={pos.id}
              className={`p-4 transition-colors hover:bg-white/[0.02] ${
                isLong ? 'border-l-2 border-l-mq-long/40' : 'border-l-2 border-l-mq-short/40'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="font-bold text-white text-sm">{pos.symbol}</div>
                  <span
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase ${
                      isLong
                        ? 'bg-mq-long-dim/10 text-mq-long border border-mq-long/30'
                        : 'bg-mq-short-dim/10 text-mq-short border border-mq-short/30'
                    }`}
                  >
                    {isLong ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                    {pos.direction}
                  </span>
                  {pos.confidence && (
                    <span className="text-[10px] text-neutral-500 font-mono">
                      {pos.confidence}% conf
                    </span>
                  )}
                  {pos.regime && (
                    <span className="text-[10px] text-neutral-500 font-mono capitalize">
                      {pos.regime}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <Clock className="w-3 h-3 text-neutral-600" />
                  <span className="text-[10px] text-neutral-500 font-mono">
                    {fmtDuration(pos.duration_hours)}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] text-neutral-600 uppercase tracking-wider">Entry</span>
                  <span className="text-xs font-mono text-neutral-300">${fmtPrice(pos.entry_price)}</span>
                </div>

                <div className="flex flex-col gap-1">
                  <span className="text-[10px] text-neutral-600 uppercase tracking-wider">Mark</span>
                  <span className="text-xs font-mono text-white font-semibold">${fmtPrice(pos.mark_price)}</span>
                </div>

                <div className="flex flex-col gap-1">
                  <span className="text-[10px] text-neutral-600 uppercase tracking-wider">PnL</span>
                  <span className={`text-xs font-mono font-bold ${pnlPositive ? 'text-mq-long' : 'text-mq-short'}`}>
                    {fmtPnl(pos.floating_pnl)}
                  </span>
                </div>

                <div className="flex flex-col gap-1">
                  <span className="text-[10px] text-neutral-600 uppercase tracking-wider">ROI</span>
                  <span className={`text-xs font-mono font-bold ${pnlPositive ? 'text-mq-long' : 'text-mq-short'}`}>
                    {fmtRoi(pos.roi_pct)}
                  </span>
                </div>
              </div>

              {(pos.stop_loss || pos.take_profit) && (
                <div className="mt-3 pt-3 border-t border-gray-800/50 flex gap-4 text-[10px]">
                  {pos.stop_loss && (
                    <div className="flex gap-1">
                      <span className="text-neutral-600">SL:</span>
                      <span className="text-mq-short font-mono">${fmtPrice(pos.stop_loss)}</span>
                    </div>
                  )}
                  {pos.take_profit && (
                    <div className="flex gap-1">
                      <span className="text-neutral-600">TP:</span>
                      <span className="text-mq-long font-mono">${fmtPrice(pos.take_profit)}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
