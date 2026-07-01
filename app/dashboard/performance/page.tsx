'use client';

import { useState, useEffect, useCallback } from 'react';
import Sidebar from '@/components/layout/Sidebar';
import PerformanceCard, { type CardStatus } from '@/components/performance/PerformanceCard';
import {
  TrueEquityCurve,
  ClosedTradeEquityCurve,
  RangeSelector,
} from '@/components/performance/EquityCurveChart';
import StatisticsGrid from '@/components/performance/StatisticsGrid';
import PerformanceHeader from '@/components/performance/PerformanceHeader';
import {
  getLivePerformanceReport,
  getRecentTrades,
  getOpenPositions,
  getRegimePerformance,
  getConfidenceBuckets,
  getAccountEquity,
  getAccountEquityHistory,
  getClosedTradeEquity,
  type LiveMetrics,
  type EquityPoint,
  type EquitySnapshot,
  type EquityRange,
  type RecentTrade,
  type Position,
  type RegimeMetrics,
  type ConfidenceBucket,
  type AccountEquity,
} from '@/lib/services/performanceService';
import { useIsPrivacyMode } from '@/lib/stores/privacyStore';
import { maskOr, MASK_MONETARY, MASK_PERCENT, MASK_PRICE } from '@/lib/format/privacy';
import SensitiveValue from '@/components/common/SensitiveValue';
import TradingModeManager from '@/components/trading/TradingModeManager';
import PaperPortfolio from '@/components/trading/PaperPortfolio';
import ResearchSummaryCard from '@/components/trading/ResearchSummaryCard';
import LiveOpenPositions from '@/components/trading/LiveOpenPositions';
import { useTradingMode } from '@/lib/hooks/useTradingMode';
import { getDataProvider } from '@/lib/providers';

const AUTO_REFRESH_MS = 30_000;

export default function PerformanceDashboard() {
  const privacy = useIsPrivacyMode();
  const { mode, isPaper } = useTradingMode();
  const [metrics, setMetrics] = useState<LiveMetrics | null>(null);
  const [equityCurve, setEquityCurve] = useState<EquityPoint[]>([]);
  const [accountEquity, setAccountEquity] = useState<AccountEquity | null>(null);
  const [equityHistory, setEquityHistory] = useState<EquitySnapshot[]>([]);
  const [equityRange, setEquityRange] = useState<EquityRange>('7d');
  const [closedTradeEquity, setClosedTradeEquity] = useState<EquityPoint[]>([]);
  const [recentTrades, setRecentTrades] = useState<RecentTrade[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [regimes, setRegimes] = useState<Record<string, RegimeMetrics>>({});
  const [confidence, setConfidence] = useState<Record<string, ConfidenceBucket>>({});
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const fetchAllData = useCallback(async (initial = false) => {
    if (initial) {
      setLoading(true);
    } else {
      setIsRefreshing(true);
    }

    try {
      const provider = getDataProvider(mode);

      const [
        equityData,
        historyData,
        metricsData,
        positionsData,
        tradesData,
        regimesData,
        confidenceData,
        equityCurveData,
      ] = await Promise.all([
        provider.getAccountEquity(),
        provider.getEquityHistory(equityRange),
        provider.getMetrics(),
        provider.getOpenPositions(),
        provider.getRecentTrades(20),
        provider.getRegimePerformance(),
        provider.getConfidenceBuckets(),
        provider.getEquityCurve(),
      ]);

      setAccountEquity(equityData);
      setEquityHistory(historyData);
      setMetrics(metricsData);
      setPositions(positionsData);
      setRecentTrades(tradesData);
      setRegimes(regimesData);
      setConfidence(confidenceData);
      setEquityCurve(equityCurveData);
      setClosedTradeEquity(equityCurveData);

      setError(null);
      setLastUpdated(new Date().toISOString());
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch analytics data';
      setError(
        `Backend error: ${message}. Ensure ml_service is running on port 8000.`,
      );
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, [equityRange, isPaper]);

  // Refetch equity history whenever the range selector changes, without
  // forcing the full loading spinner (only the chart refreshes).
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const provider = getDataProvider(mode);
        const historyData = await provider.getEquityHistory(equityRange);
        if (!cancelled) {
          setEquityHistory(historyData);
          const equityCurveData = await provider.getEquityCurve();
          setEquityCurve(equityCurveData);
          setClosedTradeEquity(equityCurveData);
        }
      } catch {
        // Swallow — keep the previous data.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [equityRange, mode]);

  useEffect(() => {
    fetchAllData(true);
    const interval = setInterval(() => fetchAllData(false), AUTO_REFRESH_MS);
    return () => clearInterval(interval);
  }, [fetchAllData]);

  // ─── Loading state ────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex h-screen bg-mq-bg text-white">
        <Sidebar />
        <div className="flex-1 flex flex-col items-center justify-center">
          <div className="w-8 h-8 border-2 border-mq-accent/20 border-t-mq-accent rounded-full animate-spin mb-4" />
          <div className="text-neutral-400 text-sm font-medium">Loading analytics...</div>
        </div>
      </div>
    );
  }

  // ─── Error state ──────────────────────────────────────────────
  if (error && !metrics) {
    return (
      <div className="flex h-screen bg-mq-bg text-white">
        <Sidebar />
        <div className="flex-1 flex flex-col items-center justify-center p-8">
          <svg
            className="w-12 h-12 text-mq-short mb-4"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <div className="text-mq-short font-bold text-sm mb-1">Connection Error</div>
          <div className="text-neutral-400 text-xs max-w-md text-center mb-6">{error}</div>
          <button
            onClick={() => fetchAllData(true)}
            className="px-4 py-2 bg-mq-accent-dim/20 text-mq-accent border border-mq-accent/30 rounded-md text-sm font-semibold hover:bg-mq-accent-dim/40 transition-all"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  // ─── Helpers ──────────────────────────────────────────────────
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

  // Price formatter: adapts decimals to magnitude (crypto-friendly).
  const fmtPrice = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return '—';
    const abs = Math.abs(value);
    const digits = abs >= 1000 ? 2 : abs >= 1 ? 4 : 6;
    return value.toLocaleString(undefined, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  };

  // Duration formatter: minutes → "Xh Ym" / "Xd Yh" / "Ym".
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

  const pnlStatus = (value: number): CardStatus =>
    value > 0 ? 'positive' : value < 0 ? 'negative' : 'neutral';

  // ─── Recent trades (from backend closed-position schema) ─────
  // The list is already newest-first from the backend; no re-sort needed.
  const visibleTrades = recentTrades.slice(0, 20);

  return (
    <div className="flex h-screen bg-mq-bg text-white">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        <PerformanceHeader
          lastUpdated={lastUpdated}
          isRefreshing={isRefreshing}
          onRefresh={() => fetchAllData(false)}
          autoRefreshSeconds={AUTO_REFRESH_MS / 1000}
        />

        <main className="flex-1 overflow-y-auto p-6 bg-gradient-to-b from-black via-mq-bg to-black">
          <div className="space-y-6">
            {/* Inline error banner if data is stale */}
            {error && metrics && (
              <div className="flex items-center gap-3 p-3 rounded-lg bg-mq-short-dim/10 border border-mq-short/30 text-mq-short text-xs font-medium">
                <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                Showing stale data — {error}
              </div>
            )}

            {/* ─── Trading Mode Manager + Paper Portfolio + Research Summary ─── */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
              <div className="xl:col-span-1">
                <TradingModeManager />
              </div>
              <div className="xl:col-span-1">
                <PaperPortfolio />
              </div>
              {isPaper && (
                <div className="xl:col-span-1">
                  <ResearchSummaryCard />
                </div>
              )}
            </div>

            {/* ─── KPI Cards (4x2) ─────────────────────────────── */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
              {/* ─── Account Equity (from Binance) ────────────── */}
              {accountEquity && accountEquity.source === 'binance' && (
                <>
                  <PerformanceCard
                    label="Account Equity"
                    value={maskOr(`$${fmtNum(accountEquity.margin_balance)}`, MASK_MONETARY, privacy)}
                    sublabel={isPaper ? 'Paper broker equity' : 'Binance Futures margin'}
                    status="neutral"
                  />
                  <PerformanceCard
                    label="Wallet Balance"
                    value={maskOr(`$${fmtNum(accountEquity.wallet_balance)}`, MASK_MONETARY, privacy)}
                    sublabel={maskOr(`Unrealized ${fmtUsd(accountEquity.unrealized_pnl)}`, MASK_MONETARY, privacy, 'Unrealized —')}
                    status={accountEquity.unrealized_pnl !== null ? pnlStatus(accountEquity.unrealized_pnl) : 'neutral'}
                  />
                  <PerformanceCard
                    label="Available Balance"
                    value={maskOr(`$${fmtNum(accountEquity.available_balance)}`, MASK_MONETARY, privacy)}
                    sublabel="For new orders"
                    status={accountEquity.available_balance !== null && accountEquity.available_balance > 0 ? 'positive' : 'negative'}
                  />
                </>
              )}
              {accountEquity && accountEquity.source === 'unavailable' && (
                <PerformanceCard
                  label="Account Equity"
                  value="Unavailable"
                  sublabel="Binance API not reachable"
                  status="neutral"
                />
              )}
              {!accountEquity && (
                <PerformanceCard
                  label="Account Equity"
                  value="—"
                  sublabel="Loading..."
                  status="neutral"
                />
              )}
              {/* ─── Performance Metrics (rest of grid) ────── */}
              {metrics && (
                <>
                  <PerformanceCard
                    label="Win Rate"
                    value={`${fmtNum(metrics.win_rate)}%`}
                    sublabel={`${metrics.winning_trades}W / ${metrics.losing_trades}L`}
                    status={metrics.win_rate >= 50 ? 'positive' : 'neutral'}
                  />
                  <PerformanceCard
                    label="Total Trades"
                    value={String(metrics.total_trades)}
                    sublabel="Closed positions"
                    status="neutral"
                  />
                  <PerformanceCard
                    label="Net PnL"
                    value={maskOr(fmtUsd(metrics.total_pnl), MASK_MONETARY, privacy)}
                    sublabel={maskOr(`ROI ${fmtNum(metrics.roi)}%`, MASK_PERCENT, privacy)}
                    status={pnlStatus(metrics.total_pnl)}
                  />
                  <PerformanceCard
                    label="Profit Factor"
                    value={fmtNum(metrics.profit_factor)}
                    sublabel={metrics.profit_factor >= 1 ? 'Profitable' : 'Unprofitable'}
                    status={metrics.profit_factor >= 1 ? 'positive' : 'negative'}
                  />
                  <PerformanceCard
                    label="Expectancy"
                    value={maskOr(fmtUsd(metrics.expectancy), MASK_MONETARY, privacy)}
                    sublabel="Per trade"
                    status={pnlStatus(metrics.expectancy)}
                  />
                  <PerformanceCard
                    label="Sharpe Ratio"
                    value={metrics.sharpe_ratio !== null ? fmtNum(metrics.sharpe_ratio) : 'Calculating...'}
                    sublabel="Risk-adjusted return"
                    status={metrics.sharpe_ratio !== null && metrics.sharpe_ratio >= 1 ? 'positive' : 'neutral'}
                  />
                  <PerformanceCard
                    label="Max Drawdown"
                    value={maskOr(fmtUsd(metrics.max_drawdown), MASK_MONETARY, privacy)}
                    sublabel={maskOr(`${fmtNum(metrics.max_drawdown_pct)}% peak-to-trough`, MASK_PERCENT, privacy)}
                    status="negative"
                  />
                  <PerformanceCard
                    label="Avg Hold Time"
                    value={metrics.avg_hold_time_hours !== null ? `${fmtNum(metrics.avg_hold_time_hours)}h` : 'N/A'}
                    sublabel="Per trade"
                    status="neutral"
                  />
                </>
              )}
            </div>

            {/* ─── True Account Equity Curve (Binance) ─────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-10 gap-6">
              <section className="lg:col-span-7 glass-card p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-baseline gap-2">
                    <h3 className="text-sm font-bold text-white tracking-wider uppercase">
                      {isPaper ? 'Paper Account Equity Curve' : 'True Account Equity Curve'}
                    </h3>
                    <span className="text-[10px] text-neutral-500 font-mono">
                      {isPaper ? 'Paper broker' : 'Binance'} · {equityHistory.length} snapshots
                    </span>
                  </div>
                  <RangeSelector selected={equityRange} onSelect={setEquityRange} />
                </div>
                <TrueEquityCurve data={equityHistory} height={360} privacy={privacy} />
              </section>

              {/* ─── Confidence Analysis ──────────────────────────── */}
              {Object.keys(confidence).length > 0 ? (
                <section className="lg:col-span-3 glass-card overflow-hidden">
                  <div className="flex items-center justify-between p-4 border-b border-mq-panel-border bg-black/40">
                    <div className="flex items-baseline gap-2">
                      <h3 className="text-sm font-bold text-white tracking-wider uppercase">
                        Confidence
                      </h3>
                      <span className="text-[10px] text-neutral-500 font-mono">
                        Win rate by bucket
                      </span>
                    </div>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-mq-panel-border">
                          <th className="text-left px-4 py-3 text-[10px] font-bold text-neutral-500 uppercase tracking-wider">Bucket</th>
                          <th className="text-right px-4 py-3 text-[10px] font-bold text-neutral-500 uppercase tracking-wider">Trades</th>
                          <th className="text-right px-4 py-3 text-[10px] font-bold text-neutral-500 uppercase tracking-wider">Win%</th>
                          <th className="text-right px-4 py-3 text-[10px] font-bold text-neutral-500 uppercase tracking-wider">PnL</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(confidence).map(([key, bucket]) => {
                          const profitable = bucket.total_pnl >= 0;
                          return (
                            <tr
                              key={key}
                              className={`border-b border-mq-panel-border last:border-0 transition-colors ${
                                profitable ? 'bg-mq-long/[0.03] hover:bg-mq-long/[0.06]' : 'bg-mq-short/[0.03] hover:bg-mq-short/[0.06]'
                              }`}
                            >
                              <td className="px-4 py-3 font-semibold text-white text-xs">{bucket.bucket}</td>
                              <td className="px-4 py-3 text-right font-mono text-neutral-300 text-xs">{bucket.total_trades}</td>
                              <td className="px-4 py-3 text-right font-mono text-neutral-300 text-xs">{fmtNum(bucket.win_rate)}%</td>
                              <td className={`px-4 py-3 text-right font-mono font-semibold text-xs ${profitable ? 'text-mq-long' : 'text-mq-short'}`}>
                                <SensitiveValue value={bucket.total_pnl} formatter={(v) => fmtUsd(Number(v))} />
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </section>
              ) : (
                <section className="lg:col-span-3 glass-card p-8 flex items-center justify-center">
                  <span className="text-neutral-500 text-xs">No confidence data</span>
                </section>
              )}
            </div>

            {/* ─── Statistics + Regime (50/50) ─────────────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {metrics && (
                <section>
                  <div className="flex items-baseline gap-2 mb-3">
                    <h3 className="text-sm font-bold text-white tracking-wider uppercase">
                      Trading Statistics
                    </h3>
                    <span className="text-[10px] text-neutral-500 font-mono">
                      Detailed breakdown
                    </span>
                  </div>
                  <StatisticsGrid metrics={metrics} />
                </section>
              )}

              {Object.keys(regimes).length > 0 ? (
                <section className="glass-card overflow-hidden">
                  <div className="flex items-center justify-between p-4 border-b border-mq-panel-border bg-black/40">
                    <div className="flex items-baseline gap-2">
                      <h3 className="text-sm font-bold text-white tracking-wider uppercase">
                        Regime Performance
                      </h3>
                      <span className="text-[10px] text-neutral-500 font-mono">
                        Performance by market regime
                      </span>
                    </div>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-mq-panel-border">
                          <th className="text-left px-4 py-3 text-[10px] font-bold text-neutral-500 uppercase tracking-wider">Regime</th>
                          <th className="text-right px-4 py-3 text-[10px] font-bold text-neutral-500 uppercase tracking-wider">Trades</th>
                          <th className="text-right px-4 py-3 text-[10px] font-bold text-neutral-500 uppercase tracking-wider">Win Rate</th>
                          <th className="text-right px-4 py-3 text-[10px] font-bold text-neutral-500 uppercase tracking-wider">P.F.</th>
                          <th className="text-right px-4 py-3 text-[10px] font-bold text-neutral-500 uppercase tracking-wider">Expect.</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(regimes).map(([key, regime]) => {
                          const isUnknown = regime.regime_label === 'unknown' || regime.regime_label === 'Unknown';
                          const label = isUnknown ? 'Unknown (historical data)' : regime.regime_label;
                          return (
                            <tr
                              key={key}
                              className="border-b border-mq-panel-border last:border-0 hover:bg-white/[0.02] transition-colors"
                            >
                              <td className="px-4 py-3 font-semibold text-white capitalize text-xs">{label}</td>
                              <td className="px-4 py-3 text-right font-mono text-neutral-300 text-xs">{regime.total_trades}</td>
                              <td className="px-4 py-3 text-right font-mono text-neutral-300 text-xs">{fmtNum(regime.win_rate)}%</td>
                              <td className={`px-4 py-3 text-right font-mono font-semibold text-xs ${Number(regime.profit_factor) >= 1 ? 'text-mq-long' : 'text-mq-short'}`}>
                                {regime.profit_factor}
                              </td>
                              <td className={`px-4 py-3 text-right font-mono font-semibold text-xs ${regime.expectancy >= 0 ? 'text-mq-long' : 'text-mq-short'}`}>
                                <SensitiveValue value={regime.expectancy} formatter={(v) => fmtUsd(Number(v))} />
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </section>
              ) : (
                <section className="glass-card p-8 flex items-center justify-center">
                  <span className="text-neutral-500 text-xs">No regime data</span>
                </section>
              )}
            </div>

            {/* ─── Closed Trade Equity Curve (legacy/strategy) ──── */}
            {closedTradeEquity.length > 0 && (
              <section className="glass-card p-5">
                <div className="flex items-baseline justify-between mb-4">
                  <div className="flex items-baseline gap-2">
                    <h3 className="text-sm font-bold text-white tracking-wider uppercase">
                      Closed Trade Curve
                    </h3>
                    <span className="text-[10px] text-neutral-500 font-mono">
                      Realized PnL only · {closedTradeEquity.length} trades
                    </span>
                  </div>
                  <span className="text-[10px] text-neutral-600 font-mono">
                    starting_balance + Σ net realized PnL
                  </span>
                </div>
                <ClosedTradeEquityCurve data={closedTradeEquity} height={260} privacy={privacy} />
              </section>
            )}

            {/* ─── Live Open Positions (Paper Mode Real-time) ───────── */}
            {isPaper && <LiveOpenPositions />}

            {/* ─── Open Positions (Live Mode Static) ───────────────── */}
            {!isPaper && positions.length > 0 && (
              <section className="glass-card overflow-hidden">
                <div className="flex items-center justify-between p-4 border-b border-mq-panel-border bg-black/40">
                  <div className="flex items-baseline gap-2">
                    <h3 className="text-sm font-bold text-white tracking-wider uppercase">
                      Open Positions
                    </h3>
                    <span className="text-[10px] text-neutral-500 font-mono">
                      {positions.length} active
                    </span>
                  </div>
                </div>
                <div className="divide-y divide-mq-panel-border">
                  {positions.map((pos, idx) => {
                    const isLong = pos.side === 'long';
                    const pnlPositive = pos.unrealized_pnl >= 0;
                    return (
                      <div
                        key={idx}
                        className={`flex items-center justify-between p-4 transition-colors hover:bg-white/[0.02] ${
                          isLong ? 'border-l-2 border-l-mq-long/40' : 'border-l-2 border-l-mq-short/40'
                        }`}
                      >
                        <div className="flex items-center gap-4">
                          <div className="font-bold text-white">{pos.symbol}</div>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase ${
                              isLong
                                ? 'bg-mq-long-dim/10 text-mq-long border border-mq-long/30'
                                : 'bg-mq-short-dim/10 text-mq-short border border-mq-short/30'
                            }`}
                          >
                            {pos.side}
                          </span>
                          <div className="text-xs text-neutral-400 font-mono">
                            <span className="text-neutral-600">Entry:</span>{' '}
                            <SensitiveValue
                              value={pos.entry_price}
                              mask={MASK_PRICE}
                              formatter={(v) => `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 4 })}`}
                            />
                          </div>
                          <div className="text-xs text-neutral-400 font-mono">
                            <span className="text-neutral-600">Mark:</span>{' '}
                            <SensitiveValue
                              value={pos.mark_price}
                              mask={MASK_PRICE}
                              formatter={(v) => `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 4 })}`}
                            />
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          {pos.signal && (
                            <div
                              className={`text-[10px] px-2 py-0.5 rounded font-mono font-semibold ${
                                pos.agreement === 'match'
                                  ? 'bg-mq-long-dim/10 text-mq-long'
                                  : pos.agreement === 'conflict'
                                    ? 'bg-mq-short-dim/10 text-mq-short'
                                    : 'bg-neutral-800 text-neutral-400'
                              }`}
                            >
                              {pos.signal.direction} ({pos.signal.confidence}%)
                            </div>
                          )}
                          <div
                            className={`text-sm font-bold font-mono ${pnlPositive ? 'text-mq-long' : 'text-mq-short'}`}
                          >
                            <SensitiveValue
                              value={pos.unrealized_pnl}
                              mask={MASK_MONETARY}
                              formatter={(v) => `${pnlPositive ? '+' : ''}$${Number(v).toFixed(2)}`}
                            />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            {/* ─── Recent Trades ────────────────────────────────── */}
            {visibleTrades.length > 0 && (
              <section className="glass-card overflow-hidden">
                <div className="flex items-center justify-between p-4 border-b border-mq-panel-border bg-black/40">
                  <div className="flex items-baseline gap-2">
                    <h3 className="text-sm font-bold text-white tracking-wider uppercase">
                      Recent Trades
                    </h3>
                    <span className="text-[10px] text-neutral-500 font-mono">
                      Last {visibleTrades.length} closed positions
                    </span>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-mq-panel-border">
                        <th className="text-left px-4 py-3 text-[10px] font-bold text-neutral-500 uppercase tracking-wider">Symbol</th>
                        <th className="text-left px-4 py-3 text-[10px] font-bold text-neutral-500 uppercase tracking-wider">Side</th>
                        <th className="text-right px-4 py-3 text-[10px] font-bold text-neutral-500 uppercase tracking-wider">Entry</th>
                        <th className="text-right px-4 py-3 text-[10px] font-bold text-neutral-500 uppercase tracking-wider">Exit</th>
                        <th className="text-right px-4 py-3 text-[10px] font-bold text-neutral-500 uppercase tracking-wider">Duration</th>
                        <th className="text-right px-4 py-3 text-[10px] font-bold text-neutral-500 uppercase tracking-wider">Net PnL</th>
                        <th className="text-right px-4 py-3 text-[10px] font-bold text-neutral-500 uppercase tracking-wider">Fees</th>
                        <th className="text-left px-4 py-3 text-[10px] font-bold text-neutral-500 uppercase tracking-wider">Regime</th>
                      </tr>
                    </thead>
                    <tbody>
                      {visibleTrades.map((trade, idx) => {
                        const isLong = trade.direction === 'long';
                        const pnlPositive = trade.net_pnl >= 0;
                        const exitTime = new Date(trade.exit_time);
                        return (
                          <tr
                            key={`${trade.symbol}-${trade.exit_time}-${idx}`}
                            className="border-b border-mq-panel-border last:border-0 hover:bg-white/[0.02] transition-colors"
                          >
                            <td className="px-4 py-3 font-bold text-white text-xs">{trade.symbol}</td>
                            <td className="px-4 py-3">
                              <span
                                className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                                  isLong
                                    ? 'bg-mq-long-dim/10 text-mq-long'
                                    : 'bg-mq-short-dim/10 text-mq-short'
                                }`}
                              >
                                {isLong ? 'Long' : 'Short'}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-right font-mono text-neutral-300 text-xs">
                              <SensitiveValue value={trade.entry_price} mask={MASK_PRICE} formatter={(v) => fmtPrice(Number(v))} />
                            </td>
                            <td className="px-4 py-3 text-right font-mono text-neutral-300 text-xs">
                              {trade.exit_price !== null ? (
                                <SensitiveValue value={trade.exit_price} mask={MASK_PRICE} formatter={(v) => fmtPrice(Number(v))} />
                              ) : (
                                '—'
                              )}
                            </td>
                            <td className="px-4 py-3 text-right font-mono text-neutral-400 text-xs">
                              {fmtDuration(trade.duration_minutes)}
                            </td>
                            <td className={`px-4 py-3 text-right font-mono font-semibold text-xs ${pnlPositive ? 'text-mq-long' : 'text-mq-short'}`}>
                              <SensitiveValue
                                value={trade.net_pnl}
                                mask={MASK_MONETARY}
                                formatter={(v) => `${pnlPositive ? '+' : ''}${Number(v).toFixed(2)}`}
                              />
                            </td>
                            <td className="px-4 py-3 text-right font-mono text-neutral-500 text-xs">
                              <SensitiveValue value={trade.commission} mask={MASK_PRICE} formatter={(v) => Number(v).toFixed(4)} />
                            </td>
                            <td className="px-4 py-3 text-neutral-400 text-xs capitalize">
                              {trade.regime || '—'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {/* No data state */}
            {!metrics && !error && (
              <div className="glass-card p-12 flex flex-col items-center justify-center text-center">
                <svg className="w-10 h-10 text-neutral-600 mb-3" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
                </svg>
                <div className="text-neutral-400 text-sm font-semibold mb-1">No trade data yet</div>
                <div className="text-neutral-500 text-xs">Performance metrics will appear once trades are recorded.</div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
