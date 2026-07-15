'use client';

import { useEffect, useState, useMemo } from 'react';
import Sidebar from '@/components/layout/Sidebar';
import {
  getRecentTrades,
  ACTIVE_PAIRS,
  type RecentTrade,
} from '@/lib/services/performanceService';
import { useIsPrivacyMode } from '@/lib/stores/privacyStore';
import {
  maskOr,
  MASK_MONETARY,
  MASK_PRICE,
} from '@/lib/format/privacy';
import SensitiveValue from '@/components/common/SensitiveValue';
import { useTradingMode } from '@/lib/hooks/useTradingMode';

// ─── Formatters (same conventions as performance page) ─────────────

const fmtUsd = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return 'N/A';
  const sign = value >= 0 ? '+' : '-';
  return `${sign}$${Math.abs(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
};

const fmtNum = (value: number | null | undefined, digits = 2): string => {
  if (value === null || value === undefined) return 'N/A';
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
};

const fmtPrice = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return '—';
  const abs = Math.abs(value);
  const digits = abs >= 1000 ? 2 : abs >= 1 ? 4 : 6;
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
};

const fmtDuration = (minutes: number | null | undefined): string => {
  if (minutes === null || minutes === undefined) return '—';
  if (minutes < 1) return '<1m';
  const totalMin = Math.round(minutes);
  const days = Math.floor(totalMin / 1440);
  const hours = Math.floor((totalMin % 1440) / 60);
  const mins = totalMin % 60;
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
};

// ─── Summary stats derived from trade array ────────────────────────

interface TradeStats {
  totalTrades: number;
  totalNetPnl: number;
  winRate: number;
  bestTrade: number | null;
  worstTrade: number | null;
  avgTrade: number | null;
  profitFactor: number;
  totalFees: number;
}

function computeStats(trades: RecentTrade[]): TradeStats {
  if (trades.length === 0) {
    return {
      totalTrades: 0,
      totalNetPnl: 0,
      winRate: 0,
      bestTrade: null,
      worstTrade: null,
      avgTrade: null,
      profitFactor: 0,
      totalFees: 0,
    };
  }

  const wins = trades.filter((t) => t.net_pnl > 0);
  const losses = trades.filter((t) => t.net_pnl < 0);
  const grossWin = wins.reduce((s, t) => s + t.net_pnl, 0);
  const grossLoss = Math.abs(losses.reduce((s, t) => s + t.net_pnl, 0));

  return {
    totalTrades: trades.length,
    totalNetPnl: trades.reduce((s, t) => s + t.net_pnl, 0),
    winRate: (wins.length / trades.length) * 100,
    bestTrade: Math.max(...trades.map((t) => t.net_pnl)),
    worstTrade: Math.min(...trades.map((t) => t.net_pnl)),
    avgTrade: trades.reduce((s, t) => s + t.net_pnl, 0) / trades.length,
    profitFactor: grossLoss > 0 ? grossWin / grossLoss : wins.length > 0 ? Infinity : 0,
    totalFees: trades.reduce((s, t) => s + t.commission, 0),
  };
}

// ─── Status color helper ──────────────────────────────────────────

function pnlColor(value: number): 'text-mq-long' | 'text-mq-short' | 'text-neutral-400' {
  if (value > 0) return 'text-mq-long';
  if (value < 0) return 'text-mq-short';
  return 'text-neutral-400';
}

function pnlStatus(value: number | null | undefined): 'positive' | 'negative' | 'neutral' {
  if (value === null || value === undefined) return 'neutral';
  if (value > 0) return 'positive';
  if (value < 0) return 'negative';
  return 'neutral';
}

// ─── Page ─────────────────────────────────────────────────────────

export default function TradesPage() {
  const privacy = useIsPrivacyMode();
  const { mode } = useTradingMode();
  const [trades, setTrades] = useState<RecentTrade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [symbolFilter, setSymbolFilter] = useState<string>('ALL');

  // Fetch trades on mount and when filter changes
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const tradingMode = mode || 'LIVE';
    const opts = symbolFilter === 'ALL' ? { limit: 200 } : { limit: 200, symbol: symbolFilter };
    getRecentTrades(tradingMode, opts)
      .then((data) => {
        if (!cancelled) setTrades(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Failed to load trade history');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [symbolFilter, mode]);

  const stats = useMemo(() => computeStats(trades), [trades]);

  // Unique symbols present in the data (for filter, minus the manual list)
  const tradedSymbols = useMemo(() => {
    const syms = new Set(trades.map((t) => t.symbol));
    return ACTIVE_PAIRS.filter((s) => syms.has(s));
  }, [trades]);

  return (
    <div className="flex min-h-screen bg-black text-white">
      <Sidebar />

      <main className="flex-1 overflow-y-auto p-6 lg:p-8 space-y-6">
        {/* ─── Header ─────────────────────────────────────── */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">My Trades</h1>
            <p className="text-sm text-mq-muted mt-1">
              Binance Futures trade history &amp; analytics
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* Symbol filter */}
            <select
              value={symbolFilter}
              onChange={(e) => setSymbolFilter(e.target.value)}
              className="bg-black/30 border border-mq-panel-border rounded-lg px-3 py-2 text-xs text-neutral-300 font-mono focus:outline-none focus:border-mq-accent/50"
            >
              <option value="ALL">All Pairs</option>
              {tradedSymbols.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* ─── Summary Cards ──────────────────────────────── */}
        {trades.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <SummaryCard
              label="Total Net PnL"
              value={maskOr(fmtUsd(stats.totalNetPnl), MASK_MONETARY, privacy)}
              status={pnlStatus(stats.totalNetPnl)}
            />
            <SummaryCard
              label="Win Rate"
              value={`${fmtNum(stats.winRate, 1)}%`}
              status={stats.winRate >= 50 ? 'positive' : 'negative'}
            />
            <SummaryCard
              label="Best Trade"
              value={maskOr(fmtUsd(stats.bestTrade), MASK_MONETARY, privacy)}
              status="positive"
            />
            <SummaryCard
              label="Worst Trade"
              value={maskOr(fmtUsd(stats.worstTrade), MASK_MONETARY, privacy)}
              status="negative"
            />
            <SummaryCard
              label="Average Trade"
              value={maskOr(fmtUsd(stats.avgTrade), MASK_MONETARY, privacy)}
              status={pnlStatus(stats.avgTrade)}
            />
            <SummaryCard
              label="Profit Factor"
              value={stats.profitFactor === Infinity ? '∞' : fmtNum(stats.profitFactor)}
              status={stats.profitFactor >= 1 ? 'positive' : 'negative'}
            />
            <SummaryCard
              label="Total Fees"
              value={maskOr(fmtUsd(stats.totalFees), MASK_MONETARY, privacy)}
              status="neutral"
            />
            <SummaryCard
              label="Total Trades"
              value={String(stats.totalTrades)}
              status="neutral"
            />
          </div>
        )}

        {/* ─── Loading / Error / Empty ────────────────────── */}
        {loading && (
          <div className="rounded-xl border border-mq-panel-border bg-black/30 p-12 text-center">
            <div className="text-mq-muted animate-pulse">Loading trade history…</div>
          </div>
        )}

        {error && !loading && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/5 p-6 text-center">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        {!loading && !error && trades.length === 0 && (
          <div className="rounded-xl border border-mq-panel-border bg-black/30 p-12 text-center space-y-4">
            <p className="text-neutral-400 text-sm">
              No Binance trade history found.
            </p>
            <pre className="text-mq-accent text-xs font-mono bg-black/50 rounded-lg px-4 py-3 inline-block">
              python -m cli.commands sync-trades
            </pre>
            <p className="text-neutral-500 text-xs">
              Sync your Binance Futures fills first, then reload this page.
            </p>
          </div>
        )}

        {/* ─── Trade History Table ────────────────────────── */}
        {!loading && trades.length > 0 && (
          <div className="rounded-xl border border-mq-panel-border bg-black/30 overflow-hidden">
            <div className="px-5 py-4 border-b border-mq-panel-border">
              <h2 className="text-sm font-semibold tracking-wide text-neutral-300">
                Trade History
                <span className="ml-2 text-[10px] text-mq-muted font-normal">
                  {trades.length} trades
                </span>
              </h2>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-mq-panel-border text-neutral-500">
                    <th className="px-4 py-3 text-left font-medium">Symbol</th>
                    <th className="px-4 py-3 text-left font-medium">Side</th>
                    <th className="px-4 py-3 text-right font-medium">Entry</th>
                    <th className="px-4 py-3 text-right font-medium">Exit</th>
                    <th className="px-4 py-3 text-right font-medium">Qty</th>
                    <th className="px-4 py-3 text-right font-medium">Lev</th>
                    <th className="px-4 py-3 text-right font-medium">Gross PnL</th>
                    <th className="px-4 py-3 text-right font-medium">Fees</th>
                    <th className="px-4 py-3 text-right font-medium">Net PnL</th>
                    <th className="px-4 py-3 text-right font-medium">Duration</th>
                    <th className="px-4 py-3 text-left font-medium">Regime</th>
                    <th className="px-4 py-3 text-right font-medium">Exit Time</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.map((trade, idx) => {
                    const profit = trade.net_pnl > 0;
                    return (
                      <tr
                        key={`${trade.symbol}-${trade.exit_time}-${idx}`}
                        className="border-b border-mq-panel-border/40 hover:bg-white/[0.02] transition-colors"
                      >
                        {/* Symbol */}
                        <td className="px-4 py-3 font-semibold text-white">
                          {trade.symbol}
                        </td>

                        {/* Side badge */}
                        <td className="px-4 py-3">
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${
                              trade.direction === 'long'
                                ? 'bg-mq-long/15 text-mq-long'
                                : 'bg-mq-short/15 text-mq-short'
                            }`}
                          >
                            {trade.direction.toUpperCase()}
                          </span>
                        </td>

                        {/* Entry price */}
                        <td className="px-4 py-3 text-right font-mono text-neutral-300">
                          <SensitiveValue
                            value={trade.entry_price}
                            mask={MASK_PRICE}
                            formatter={(v) => fmtPrice(Number(v))}
                          />
                        </td>

                        {/* Exit price */}
                        <td className="px-4 py-3 text-right font-mono text-neutral-300">
                          {trade.exit_price !== null ? (
                            <SensitiveValue
                              value={trade.exit_price}
                              mask={MASK_PRICE}
                              formatter={(v) => fmtPrice(Number(v))}
                            />
                          ) : (
                            '—'
                          )}
                        </td>

                        {/* Quantity */}
                        <td className="px-4 py-3 text-right font-mono text-neutral-400">
                          {trade.quantity}
                        </td>

                        {/* Leverage — not available in user_trade_history */}
                        <td className="px-4 py-3 text-right font-mono text-neutral-500">
                          —
                        </td>

                        {/* Gross PnL */}
                        <td className={`px-4 py-3 text-right font-mono ${pnlColor(trade.gross_pnl)}`}>
                          <SensitiveValue
                            value={trade.gross_pnl}
                            mask={MASK_MONETARY}
                            formatter={(v) => `${profit ? '+' : ''}${Number(v).toFixed(2)}`}
                          />
                        </td>

                        {/* Fees */}
                        <td className="px-4 py-3 text-right font-mono text-neutral-500">
                          <SensitiveValue
                            value={trade.commission}
                            mask={MASK_PRICE}
                            formatter={(v) => Number(v).toFixed(4)}
                          />
                        </td>

                        {/* Net PnL */}
                        <td className={`px-4 py-3 text-right font-mono font-semibold ${pnlColor(trade.net_pnl)}`}>
                          <SensitiveValue
                            value={trade.net_pnl}
                            mask={MASK_MONETARY}
                            formatter={(v) => `${profit ? '+' : ''}${Number(v).toFixed(2)}`}
                          />
                        </td>

                        {/* Duration */}
                        <td className="px-4 py-3 text-right font-mono text-neutral-400">
                          {fmtDuration(trade.duration_minutes)}
                        </td>

                        {/* Regime */}
                        <td className="px-4 py-3 text-neutral-400 capitalize">
                          {trade.regime || '—'}
                        </td>

                        {/* Exit Time */}
                        <td className="px-4 py-3 text-right font-mono text-neutral-400">
                          {trade.exit_time
                            ? new Date(trade.exit_time).toLocaleDateString(undefined, {
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                              })
                            : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// ─── Summary card sub-component ─────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  positive: 'text-mq-long',
  negative: 'text-mq-short',
  neutral: 'text-neutral-300',
};

interface SummaryCardProps {
  label: string;
  value: string;
  status?: 'positive' | 'negative' | 'neutral';
}

function SummaryCard({ label, value, status = 'neutral' }: SummaryCardProps) {
  return (
    <div className="rounded-lg border border-mq-panel-border bg-black/30 p-4 space-y-1">
      <div className="text-[10px] text-neutral-500 font-medium tracking-wider uppercase">
        {label}
      </div>
      <div className={`text-lg font-bold font-mono tracking-tight ${STATUS_COLORS[status]}`}>
        {value}
      </div>
    </div>
  );
}
