'use client';

import { useState, useEffect, useCallback } from 'react';
import { RefreshCw, TrendingUp, TrendingDown, Wallet } from 'lucide-react';
import { getPaperSummary } from '@/lib/api/ml-trading';
import type { PaperPortfolioSummary } from '@/lib/types/ml';

const REFRESH_MS = 15_000;

const STATUS_COLORS: Record<string, string> = {
  OPEN: 'text-mq-accent',
  TP_HIT: 'text-mq-long',
  SL_HIT: 'text-mq-short',
  EXPIRED: 'text-mq-warning',
  MANUAL_CLOSE: 'text-neutral-400',
};

export default function PaperPortfolio() {
  const [summary, setSummary] = useState<PaperPortfolioSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(async (initial = false) => {
    if (initial) setLoading(true);
    else setIsRefreshing(true);
    try {
      const data = await getPaperSummary();
      setSummary(data);
      setError(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load paper portfolio';
      setError(msg);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchSummary(true);
    const interval = setInterval(() => fetchSummary(false), REFRESH_MS);
    return () => clearInterval(interval);
  }, [fetchSummary]);

  const fmtUsd = (v: number) =>
    `$${v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const fmtPct = (v: number) => `${v.toFixed(2)}%`;

  if (loading) {
    return (
      <div className="glass-card p-4 flex items-center justify-center min-h-[200px]">
        <div className="w-6 h-6 border-2 border-mq-accent/20 border-t-mq-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="glass-card p-4">
        <h3 className="text-sm font-semibold text-white tracking-wide uppercase mb-2">
          Paper Portfolio
        </h3>
        <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
          {error}
        </div>
      </div>
    );
  }

  const acct = summary?.account;
  const stats = summary?.stats;
  const openPositions = summary?.open_positions || [];
  const pnlPositive = (acct?.unrealized_pnl ?? 0) >= 0;

  return (
    <div className="glass-card p-4 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wallet className="w-4 h-4 text-mq-accent" />
          <h3 className="text-sm font-semibold text-white tracking-wide uppercase">
            Paper Portfolio
          </h3>
        </div>
        <button
          onClick={() => fetchSummary(false)}
          disabled={isRefreshing}
          className="p-1.5 rounded-lg text-gray-400 hover:text-mq-accent hover:bg-mq-accent/10 transition-colors disabled:opacity-40"
          title="Refresh"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {error && (
        <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {/* KPI grid */}
      <div className="grid grid-cols-2 gap-2">
        <KpiCell label="Balance" value={acct ? fmtUsd(acct.balance) : '-'} />
        <KpiCell label="Equity" value={acct ? fmtUsd(acct.equity) : '-'} />
        <KpiCell
          label="Unrealized PnL"
          value={acct ? fmtUsd(acct.unrealized_pnl) : '-'}
          tone={pnlPositive ? 'positive' : 'negative'}
          icon={pnlPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
        />
        <KpiCell
          label="Win Rate"
          value={stats ? fmtPct(stats.win_rate) : '-'}
          tone={(stats?.win_rate ?? 0) >= 50 ? 'positive' : 'neutral'}
        />
      </div>

      {/* Realized PnL + counts */}
      {stats && (
        <div className="flex items-center justify-between text-xs bg-gray-900/40 rounded-lg px-3 py-2">
          <span className="text-gray-400">
            Open <span className="text-white font-semibold">{stats.open_count}</span> / {stats.max_open_positions}
          </span>
          <span className="text-gray-400">
            Closed <span className="text-white font-semibold">{stats.closed_count}</span>
          </span>
          <span className={stats.total_realized_pnl >= 0 ? 'text-mq-long' : 'text-mq-short'}>
            Realized {fmtUsd(stats.total_realized_pnl)}
          </span>
        </div>
      )}

      {/* Open positions */}
      <div>
        <div className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider mb-2">
          Open Positions
        </div>
        {openPositions.length === 0 ? (
          <div className="text-xs text-gray-600 italic py-2">No open positions</div>
        ) : (
          <div className="flex flex-col gap-1.5 max-h-48 overflow-y-auto pr-1">
            {openPositions.map((p) => (
              <div
                key={p.id}
                className="flex items-center justify-between bg-gray-900/40 rounded-md px-2.5 py-1.5 text-xs"
              >
                <div className="flex items-center gap-2">
                  <span className="text-white font-semibold">{p.symbol}</span>
                  <span
                    className={`text-[10px] font-bold ${p.direction === 'LONG' ? 'text-mq-long' : 'text-mq-short'}`}
                  >
                    {p.direction}
                  </span>
                </div>
                <div className="flex items-center gap-3 font-mono">
                  <span className="text-gray-400">{p.qty}</span>
                  <span className="text-gray-300">${p.entry_price}</span>
                  <span className={STATUS_COLORS[p.status] || 'text-gray-400'}>
                    {p.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function KpiCell({
  label,
  value,
  tone = 'neutral',
  icon,
}: {
  label: string;
  value: string;
  tone?: 'positive' | 'negative' | 'neutral';
  icon?: React.ReactNode;
}) {
  const toneClass =
    tone === 'positive'
      ? 'text-mq-long'
      : tone === 'negative'
        ? 'text-mq-short'
        : 'text-white';
  return (
    <div className="bg-gray-900/40 rounded-lg px-3 py-2">
      <div className="text-[10px] text-gray-500 uppercase tracking-wider">{label}</div>
      <div className={`flex items-center gap-1 text-sm font-bold font-mono mt-0.5 ${toneClass}`}>
        {icon}
        {value}
      </div>
    </div>
  );
}
