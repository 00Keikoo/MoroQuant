/**
 * Performance Analytics Service
 *
 * Fetches trading performance data from the ML backend.
 * Routes requests based on Trading Mode (OFF/PAPER/LIVE).
 * Includes retry logic, proper typing, and error handling.
 */

import type { TradingMode } from '@/lib/types/ml';

// Re-export TradingMode for hooks
export type { TradingMode } from '@/lib/types/ml';

// ─── Types ───────────────────────────────────────────────────────

export interface LiveMetrics {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  avg_pnl: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  expectancy: number;
  roi: number;
  gross_profit: number;
  gross_loss: number;
  sharpe_ratio: number | null;
  max_drawdown: number;
  max_drawdown_pct: number;
  avg_hold_time_hours: number | null;
}

export interface EquityPoint {
  timestamp: number;
  cumulative_pnl: number;
  trade_count: number;
  trade_pnl: number;
  /** Absolute account equity = starting_balance + cumulative_pnl. */
  equity?: number;
}

export interface RecentTrade {
  symbol: string;
  side: string;
  direction: string;
  entry_time: number;
  exit_time: number;
  duration_minutes: number;
  entry_price: number;
  exit_price: number | null;
  quantity: number;
  gross_pnl: number;
  commission: number;
  net_pnl: number;
  regime: string;
  confidence: number | null;
  outcome: 'win' | 'loss' | 'breakeven';
  matched_signal_id: string | null;
  fill_count: number;
}

export interface Position {
  symbol: string;
  side: string;
  entry_price: number;
  mark_price: number;
  unrealized_pnl: number;
  quantity: number;
  take_profit: number | null;
  stop_loss: number | null;
  signal?: {
    direction: string;
    confidence: number;
  };
  agreement: string;
}

export type LivePosition = Position;


export interface RegimeMetrics {
  regime_label: string;
  total_trades: number;
  win_rate: number;
  profit_factor: number | string;
  expectancy: number;
}

export interface ConfidenceBucket {
  bucket: string;
  total_trades: number;
  win_rate: number;
  expectancy: number;
  total_pnl: number;
}

export interface LivePerformanceReport {
  status: string;
  symbol: string;
  period_days: string;
  metrics: LiveMetrics;
  timestamp: string;
  equity_curve: EquityPoint[];
  /** Embedded recent closed positions (newest first). */
  recent_trades?: RecentTrade[];
}

// ─── Model drift / regime types ───────────────────────────────────

/** Real Binance Futures account equity. */
export interface AccountEquity {
  wallet_balance: number | null;
  unrealized_pnl: number | null;
  margin_balance: number | null;
  available_balance: number | null;
  source: 'binance' | 'unavailable';
  reason?: string;
}

/** A single persisted Binance equity snapshot. */
export interface EquitySnapshot {
  /** ISO timestamp string. */
  timestamp: string;
  /** True account equity = margin_balance (wallet + unrealized PnL). */
  equity: number;
  wallet_balance: number;
  unrealized_pnl: number;
}

/** Time range for equity history queries. */
export type EquityRange = '1d' | '7d' | '30d' | 'all';

/** Legacy closed-trade equity curve response shape. */
export interface ClosedTradeEquityResponse {
  status: string;
  equity_curve: EquityPoint[];
  count: number;
  definition: string;
  timestamp: string;
}

/**
 * Drift report shape returned by GET /api/models/{symbol}/{timeframe}/drift.
 * Only the fields consumed by the UI are typed; the backend returns more
 * (feature_drift, confidence_drift, regime_drift, retrain_reasons, ...).
 */
export interface ModelDriftReport {
  symbol: string;
  timeframe: string;
  health_status: 'green' | 'yellow' | 'red' | string;
  overall_score: number;
  retrain_required: boolean;
  timestamp?: string;
}

/**
 * Compact per-model summary used by the Model Health widget. Errors per
 * individual model are swallowed so a single failing model never breaks the
 * panel — they are simply omitted from the returned list.
 */
export interface ModelDriftSummary {
  symbol: string;
  timeframe: string;
  overall_score: number | null;
  health_status: 'green' | 'yellow' | 'red' | 'unknown';
  timestamp?: string;
}

/** Latest live regime label for a symbol, sourced from its newest signal. */
export interface CurrentRegime {
  symbol: string;
  regime: string;
}

/** Production symbols trained by the ML scheduler (see scheduler.py). */
export const ACTIVE_PAIRS = [
  'BTCUSDT',
  'ETHUSDT',
  'BNBUSDT',
  'SOLUSDT',
  'HYPEUSDT',
] as const;

/** Timeframes the ML service runs models for. */
export const ACTIVE_TIMEFRAMES = ['1h', '4h'] as const;

// ─── Helpers ─────────────────────────────────────────────────────

const API_BASE =
  typeof window !== 'undefined'
    ? `${process.env.NEXT_PUBLIC_API_URL || `http://${window.location.hostname}:8000`}/api`
    : 'http://localhost:8000/api';

function getApiBaseUrl(): string {
  if (typeof window !== 'undefined') {
    return process.env.NEXT_PUBLIC_API_URL || `http://${window.location.hostname}:8000/api`;
  }
  return 'http://localhost:8000/api';
}

async function fetchWithTimeout(
  url: string,
  timeoutMs = 8000,
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, { signal: controller.signal });
    clearTimeout(timeoutId);
    return response;
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof DOMException && err.name === 'AbortError') {
      const timeoutError = new Error('Request timed out');
      timeoutError.name = 'TimeoutError';
      throw timeoutError;
    }
    throw err;
  }
}

async function fetchWithRetry(
  url: string,
  retries = 3,
  backoffMs = 1000,
): Promise<Response> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await fetchWithTimeout(url);

      if (response.ok) return response;

      // Don't retry client errors (4xx)
      if (response.status >= 400 && response.status < 500) {
        throw new Error(`Client error: ${response.status} ${response.statusText}`);
      }

      lastError = new Error(`Server error: ${response.status} ${response.statusText}`);
    } catch (err) {
      if (err instanceof Error && err.name === 'TimeoutError') {
        lastError = err;
      } else if (err instanceof Error) {
        lastError = err;
      } else {
        lastError = new Error(String(err));
      }
    }

    // Exponential backoff before retry (skip on last attempt)
    if (attempt < retries) {
      await new Promise((resolve) => setTimeout(resolve, backoffMs * Math.pow(2, attempt)));
    }
  }

  throw lastError || new Error('Request failed after retries');
}

// ─── Normalization Layer ─────────────────────────────────────────

/**
 * Normalize paper analytics response to canonical LiveMetrics.
 * Backend: /api/paper/analytics
 * Fields: total_trades, win_rate, total_realized_pnl, avg_trade_pnl,
 *         profit_factor, expectancy, avg_hold_hours, sharpe_ratio
 */
function normalizePaperAnalytics(
  backend: any,
  positions: any[],
  initialBalance: number,
): LiveMetrics {
  const wins = positions.filter((p: any) => (Number(p.realized_pnl) || 0) > 0);
  const losses = positions.filter((p: any) => (Number(p.realized_pnl) || 0) <= 0);

  const gross_profit = wins.reduce((sum: number, p: any) => sum + (Number(p.realized_pnl) || 0), 0);
  const gross_loss = Math.abs(losses.reduce((sum: number, p: any) => sum + (Number(p.realized_pnl) || 0), 0));

  const avg_win = wins.length > 0 ? gross_profit / wins.length : 0;
  const avg_loss = losses.length > 0 ? gross_loss / losses.length : 0;

  const roi = (backend.total_realized_pnl / initialBalance) * 100;

  return {
    total_trades: Number(backend.total_trades) || 0,
    winning_trades: wins.length,
    losing_trades: losses.length,
    win_rate: Number(backend.win_rate) || 0,
    total_pnl: Number(backend.total_realized_pnl) || 0,
    avg_pnl: Number(backend.avg_trade_pnl) || 0,
    avg_win: Number(avg_win.toFixed(2)),
    avg_loss: Number(avg_loss.toFixed(2)),
    profit_factor: Number(backend.profit_factor) || 0,
    expectancy: Number(backend.expectancy) || 0,
    roi: Number(roi.toFixed(4)),
    gross_profit: Number(gross_profit.toFixed(2)),
    gross_loss: Number(gross_loss.toFixed(2)),
    sharpe_ratio: backend.sharpe_ratio !== null ? Number(backend.sharpe_ratio) : null,
    max_drawdown: 0,
    max_drawdown_pct: 0,
    avg_hold_time_hours: backend.avg_hold_hours !== null ? Number(backend.avg_hold_hours) : null,
  };
}

/**
 * Compute max drawdown from equity curve.
 */
function computeMaxDrawdown(equityCurve: EquityPoint[], startingBalance: number): {
  max_drawdown: number;
  max_drawdown_pct: number;
} {
  if (equityCurve.length === 0) {
    return { max_drawdown: 0, max_drawdown_pct: 0 };
  }

  let runningMax = 0;
  let maxDd = 0;
  let maxDdPct = 0;

  equityCurve.forEach((pt: any) => {
    if (pt.cumulative_pnl > runningMax) {
      runningMax = pt.cumulative_pnl;
    }
    const dd = runningMax - pt.cumulative_pnl;
    if (dd > maxDd) {
      maxDd = dd;
    }

    const peakVal = startingBalance + runningMax;
    const ddPct = (dd / peakVal) * 100;
    if (ddPct > maxDdPct) {
      maxDdPct = ddPct;
    }
  });

  return {
    max_drawdown: maxDd,
    max_drawdown_pct: maxDdPct,
  };
}

/**
 * Normalize paper closed position to canonical RecentTrade.
 * Backend: /api/paper/positions/closed
 * Fields: id, symbol, direction, entry_price, current_price, realized_pnl,
 *         opened_at, closed_at, confidence, regime, qty, duration_minutes, signal_id
 */
function normalizePaperPosition(pos: any): RecentTrade {
  let entryTs = Date.now();
  let exitTs = Date.now();

  if (pos.opened_at) {
    let dateStr = pos.opened_at;
    if (!dateStr.includes('T') && dateStr.includes(' ')) dateStr = dateStr.replace(' ', 'T');
    if (!dateStr.endsWith('Z') && !dateStr.includes('+')) dateStr += 'Z';
    entryTs = new Date(dateStr).getTime();
  }

  if (pos.closed_at) {
    let dateStr = pos.closed_at;
    if (!dateStr.includes('T') && dateStr.includes(' ')) dateStr = dateStr.replace(' ', 'T');
    if (!dateStr.endsWith('Z') && !dateStr.includes('+')) dateStr += 'Z';
    exitTs = new Date(dateStr).getTime();
  }

  const pnl = Number(pos.realized_pnl) || 0;

  return {
    symbol: pos.symbol || '',
    side: (pos.direction || '').toUpperCase(),
    direction: (pos.direction || '').toUpperCase(),
    entry_time: entryTs,
    exit_time: exitTs,
    duration_minutes: Number(pos.duration_minutes) || 0,
    entry_price: Number(pos.entry_price) || 0,
    exit_price: Number(pos.current_price || pos.exit_price) || 0,
    quantity: Number(pos.qty) || 0,
    gross_pnl: pnl,
    commission: 0,
    net_pnl: pnl,
    regime: pos.regime || 'unknown',
    confidence: pos.confidence !== undefined ? Number(pos.confidence) : null,
    outcome: pnl > 0 ? ('win' as const) : ('loss' as const),
    matched_signal_id: pos.signal_id || null,
    fill_count: 1,
  };
}

/**
 * Normalize paper open position to canonical Position.
 * Backend: /api/paper/positions/live
 * Fields: id, symbol, direction, entry_price, mark_price, qty, floating_pnl,
 *         confidence, regime, stop_loss, take_profit
 */
function normalizePaperOpenPosition(pos: any): Position {
  const side = (pos.direction || '').toLowerCase();
  const unrealized_pnl = Number(pos.floating_pnl !== undefined ? pos.floating_pnl : pos.unrealized_pnl) || 0;
  const quantity = Number(pos.qty || pos.quantity) || 0;

  return {
    symbol: pos.symbol || '',
    side,
    entry_price: Number(pos.entry_price) || 0,
    mark_price: Number(pos.mark_price) || 0,
    unrealized_pnl,
    quantity,
    take_profit: pos.take_profit !== undefined ? pos.take_profit : null,
    stop_loss: pos.stop_loss !== undefined ? pos.stop_loss : null,
    signal: pos.confidence !== undefined ? {
      direction: side,
      confidence: Number(pos.confidence) || 0,
    } : undefined,
    agreement: 'match',
  };
}

/**
 * Normalize live open position to canonical Position.
 * Backend: /api/positions/open
 * Fields: symbol, side, position_amt, entry_price, mark_price, unrealized_pnl,
 *         take_profit, stop_loss, signal
 */
function normalizeLiveOpenPosition(pos: any): Position {
  const side = (pos.side || pos.direction || '').toLowerCase();
  const unrealized_pnl = Number(pos.unrealized_pnl !== undefined ? pos.unrealized_pnl : pos.floating_pnl) || 0;
  const quantity = Number(pos.position_amt || pos.qty || pos.quantity) || 0;

  return {
    symbol: pos.symbol || '',
    side,
    entry_price: Number(pos.entry_price) || 0,
    mark_price: Number(pos.mark_price) || 0,
    unrealized_pnl,
    quantity,
    take_profit: pos.take_profit !== undefined ? pos.take_profit : null,
    stop_loss: pos.stop_loss !== undefined ? pos.stop_loss : null,
    signal: pos.signal ? {
      direction: String(pos.signal.direction || '').toLowerCase(),
      confidence: Number(pos.signal.confidence) || 0,
    } : (pos.direction && pos.confidence ? {
      direction: String(pos.direction).toLowerCase(),
      confidence: Number(pos.confidence) || 0,
    } : undefined),
    agreement: pos.agreement || 'match',
  };
}

/**
 * Normalize confidence bucket to canonical ConfidenceBucket.
 * Backend: /api/paper/analytics/confidence
 * Fields: bucket, total_trades, win_rate, total_pnl, avg_pnl, profit_factor
 */
function normalizeConfidenceBucket(bucket: any): ConfidenceBucket {
  return {
    bucket: bucket.bucket || '',
    total_trades: Number(bucket.total_trades) || 0,
    win_rate: Number(bucket.win_rate) || 0,
    expectancy: Number(bucket.avg_pnl) || 0,
    total_pnl: Number(bucket.total_pnl) || 0,
  };
}

/**
 * Normalize regime metrics to canonical RegimeMetrics.
 * Backend: /api/paper/analytics/regime
 * Fields: regime, total_trades, win_rate, total_pnl, avg_pnl
 */
function normalizeRegimeMetrics(regime: any): RegimeMetrics {
  const totalPnl = Number(regime.total_pnl) || 0;
  const totalTrades = Number(regime.total_trades) || 0;
  const winRate = Number(regime.win_rate) || 0;
  const expectancy = Number(regime.avg_pnl) || 0;

  // Estimate profit factor from win rate and expectancy
  let profitFactor: number | string = 0;
  if (totalTrades > 0 && winRate > 0 && winRate < 100) {
    const avgWin = expectancy > 0 ? expectancy / (winRate / 100) : 0;
    const avgLoss = expectancy < 0 ? Math.abs(expectancy / (1 - winRate / 100)) : 0;
    if (avgLoss > 0) {
      profitFactor = (avgWin * winRate) / (avgLoss * (100 - winRate));
    }
  }

  return {
    regime_label: regime.regime || 'unknown',
    total_trades: totalTrades,
    win_rate: winRate,
    profit_factor: typeof profitFactor === 'number' ? profitFactor : 0,
    expectancy,
  };
}

// ─── API Functions ────────────────────────────────────────────────

export async function getLivePerformanceReport(mode: TradingMode): Promise<LivePerformanceReport> {
  if (mode === 'OFF') {
    return {
      status: 'no_data',
      symbol: '',
      period_days: '',
      metrics: {
        total_trades: 0,
        winning_trades: 0,
        losing_trades: 0,
        win_rate: 0,
        total_pnl: 0,
        avg_pnl: 0,
        avg_win: 0,
        avg_loss: 0,
        profit_factor: 0,
        expectancy: 0,
        roi: 0,
        gross_profit: 0,
        gross_loss: 0,
        sharpe_ratio: null,
        max_drawdown: 0,
        max_drawdown_pct: 0,
        avg_hold_time_hours: null,
      },
      timestamp: new Date().toISOString(),
      equity_curve: [],
      recent_trades: [],
    };
  }

  const base = getApiBaseUrl();

  if (mode === 'PAPER') {
    // Fetch account to get initial_balance
    const accountResponse = await fetchWithRetry(`${base}/paper/account/live`);
    const accountData = await accountResponse.json();

    // Validate initial_balance - required for financial integrity
    const initialBalance = Number(accountData.initial_balance);
    if (!initialBalance || isNaN(initialBalance) || initialBalance <= 0) {
      throw new Error('Portfolio unavailable: initial_balance missing or invalid');
    }

    // Fetch paper analytics and closed positions
    const analyticsResponse = await fetchWithRetry(`${base}/paper/analytics`);
    const paperAnalytics = await analyticsResponse.json();

    if (paperAnalytics.status !== 'success' && paperAnalytics.status !== 'no_data') {
      throw new Error(`Unexpected status: ${paperAnalytics.status}`);
    }

    if (paperAnalytics.status === 'no_data') {
      return {
        status: 'no_data',
        symbol: 'all',
        period_days: 'all_time',
        metrics: {
          total_trades: 0,
          winning_trades: 0,
          losing_trades: 0,
          win_rate: 0,
          total_pnl: 0,
          avg_pnl: 0,
          avg_win: 0,
          avg_loss: 0,
          profit_factor: 0,
          expectancy: 0,
          roi: 0,
          gross_profit: 0,
          gross_loss: 0,
          sharpe_ratio: null,
          max_drawdown: 0,
          max_drawdown_pct: 0,
          avg_hold_time_hours: null,
        },
        timestamp: paperAnalytics.timestamp || new Date().toISOString(),
        equity_curve: [],
        recent_trades: [],
      };
    }

    const closedPositionsResponse = await fetchWithRetry(`${base}/paper/positions/closed?limit=1000`);
    const closedData = await closedPositionsResponse.json();
    const positions = (closedData.positions || []).slice().reverse();

    // Build equity curve
    let cumulative_pnl = 0;
    const equity_curve = positions.map((pos: any, idx: number) => {
      const pnl = Number(pos.realized_pnl) || 0;
      cumulative_pnl += pnl;

      let ts = Date.now();
      if (pos.closed_at) {
        let dateStr = pos.closed_at;
        if (!dateStr.includes('T') && dateStr.includes(' ')) {
          dateStr = dateStr.replace(' ', 'T');
        }
        if (!dateStr.endsWith('Z') && !dateStr.includes('+')) {
          dateStr += 'Z';
        }
        ts = new Date(dateStr).getTime();
      }

      return {
        timestamp: ts,
        cumulative_pnl: Number(cumulative_pnl.toFixed(2)),
        trade_count: idx + 1,
        trade_pnl: Number(pnl.toFixed(2)),
        equity: Number((initialBalance + cumulative_pnl).toFixed(2)),
      };
    });

    // Normalize metrics using normalization layer
    const metrics = normalizePaperAnalytics(paperAnalytics, positions, initialBalance);
    const drawdown = computeMaxDrawdown(equity_curve, initialBalance);
    metrics.max_drawdown = Number(drawdown.max_drawdown.toFixed(2));
    metrics.max_drawdown_pct = Number(drawdown.max_drawdown_pct.toFixed(2));

    // Normalize recent trades
    const recent_trades = positions
      .slice().reverse()
      .slice(0, 20)
      .map(normalizePaperPosition);

    return {
      status: 'success',
      symbol: 'all',
      period_days: 'all_time',
      metrics,
      timestamp: paperAnalytics.timestamp || new Date().toISOString(),
      equity_curve,
      recent_trades,
    };
  }

  // Route based on Trading Mode (LIVE / Default)
  const endpoint = `${base}/analytics/live-performance`;

  const response = await fetchWithRetry(endpoint);
  const data: LivePerformanceReport = await response.json();

  if (data.status !== 'success' && data.status !== 'no_data') {
    throw new Error(`Unexpected status: ${data.status}`);
  }

  return data;
}

/**
 * Fetch recent CLOSED POSITIONS (completed round trips), newest first.
 * GET /api/analytics/recent-trades (LIVE) or /api/paper/positions/closed (PAPER)
 */
export async function getRecentTrades(
  mode: TradingMode,
  opts?: { limit?: number; symbol?: string; daysBack?: number },
): Promise<RecentTrade[]> {
  if (mode === 'OFF') {
    return [];
  }

  const base = getApiBaseUrl();
  const params = new URLSearchParams();
  if (opts?.limit !== undefined) params.set('limit', String(opts.limit));
  if (opts?.symbol) params.set('symbol', opts.symbol);
  if (opts?.daysBack !== undefined) params.set('days_back', String(opts.daysBack));
  const qs = params.toString();

  const endpoint = mode === 'PAPER'
    ? `${base}/paper/positions/closed${qs ? `?${qs}` : ''}`
    : `${base}/analytics/recent-trades${qs ? `?${qs}` : ''}`;

  const response = await fetchWithRetry(endpoint);
  const data = await response.json();
  const rawTrades = data.trades || data.positions || [];

  // Normalize trades based on mode
  if (mode === 'PAPER') {
    return rawTrades.map(normalizePaperPosition);
  } else {
    // LIVE mode trades should already be in canonical format from backend
    // but we still map to ensure consistency
    return rawTrades.map((trade: any) => ({
      symbol: trade.symbol || '',
      side: (trade.side || trade.direction || '').toUpperCase(),
      direction: (trade.direction || trade.side || '').toUpperCase(),
      entry_time: trade.entry_time || Date.now(),
      exit_time: trade.exit_time || Date.now(),
      duration_minutes: Number(trade.duration_minutes) || 0,
      entry_price: Number(trade.entry_price) || 0,
      exit_price: Number(trade.exit_price) || 0,
      quantity: Number(trade.quantity) || 0,
      gross_pnl: Number(trade.gross_pnl) || 0,
      commission: Number(trade.commission) || 0,
      net_pnl: Number(trade.net_pnl) || 0,
      regime: trade.regime || 'unknown',
      confidence: trade.confidence !== undefined ? Number(trade.confidence) : null,
      outcome: trade.outcome || ((Number(trade.net_pnl) || 0) > 0 ? 'win' : 'loss') as 'win' | 'loss' | 'breakeven',
      matched_signal_id: trade.matched_signal_id || null,
      fill_count: Number(trade.fill_count) || 1,
    }));
  }
}

export async function getOpenPositions(mode: TradingMode): Promise<Position[]> {
  if (mode === 'OFF') {
    return [];
  }

  const base = getApiBaseUrl();

  const endpoint = mode === 'PAPER'
    ? `${base}/paper/positions/live`
    : `${base}/positions/open`;

  const response = await fetchWithRetry(endpoint);
  const data = await response.json();
  const rawPositions = data.positions || [];

  // Normalize positions based on mode
  if (mode === 'PAPER') {
    return rawPositions.map(normalizePaperOpenPosition);
  } else {
    return rawPositions.map(normalizeLiveOpenPosition);
  }
}

export async function getRegimePerformance(mode: TradingMode): Promise<Record<string, RegimeMetrics>> {
  if (mode === 'OFF') {
    return {};
  }

  const base = getApiBaseUrl();

  const endpoint = mode === 'PAPER'
    ? `${base}/paper/analytics/regime`
    : `${base}/analytics/regimes`;

  const response = await fetchWithRetry(endpoint);
  const data = await response.json();

  if (data.status !== 'success') return {};

  const regimes = data.regimes || {};
  const normalized: Record<string, RegimeMetrics> = {};

  for (const [key, value] of Object.entries(regimes)) {
    normalized[key] = normalizeRegimeMetrics(value);
  }

  return normalized;
}

export async function getConfidenceBuckets(mode: TradingMode): Promise<Record<string, ConfidenceBucket>> {
  if (mode === 'OFF') {
    return {};
  }

  const base = getApiBaseUrl();

  const endpoint = mode === 'PAPER'
    ? `${base}/paper/analytics/confidence`
    : `${base}/analytics/confidence`;

  const response = await fetchWithRetry(endpoint);
  const data = await response.json();

  if (data.status !== 'success') return {};

  const buckets = data.confidence_buckets || {};
  const normalized: Record<string, ConfidenceBucket> = {};

  for (const [key, value] of Object.entries(buckets)) {
    normalized[key] = normalizeConfidenceBucket(value);
  }

  return normalized;
}

// ─── Model drift & current-regime fetchers ──────────────────────────

/**
 * Fetch the full drift report for a single model.
 * GET /api/models/{symbol}/{timeframe}/drift
 */
export async function getModelDrift(
  symbol: string,
  timeframe: string,
  mode: TradingMode,
): Promise<ModelDriftReport> {
  if (mode === 'OFF') {
    return {
      symbol,
      timeframe,
      health_status: 'unknown',
      overall_score: 0,
      retrain_required: false,
      timestamp: new Date().toISOString(),
    };
  }

  const base = getApiBaseUrl();
  const response = await fetchWithRetry(
    `${base}/models/${encodeURIComponent(symbol)}/${encodeURIComponent(timeframe)}/drift`,
  );
  return (await response.json()) as ModelDriftReport;
}

function normalizeHealthStatus(
  score: number | null | undefined,
  fallback: string,
): 'green' | 'yellow' | 'red' | 'unknown' {
  // If the backend explicitly sent 'unknown' (no drift baseline), preserve it.
  if (fallback === 'unknown') {
    return 'unknown';
  }
  // Explicit score wins (task spec thresholds).
  if (typeof score === 'number' && !Number.isNaN(score)) {
    if (score < 0.2) return 'green';
    if (score < 0.4) return 'yellow';
    return 'red';
  }
  // Otherwise trust the backend's own health_status field.
  if (fallback === 'green' || fallback === 'yellow' || fallback === 'red') {
    return fallback;
  }
  return 'unknown';
}

/**
 * Fetch drift summaries for all active production models in parallel.
 *
 * There is no "list all models" endpoint, so we fan out over the hardcoded
 * ACTIVE_PAIRS × ACTIVE_TIMEFRAMES grid. Each model is fetched independently;
 * a failure on one model is logged and dropped so the panel never blanks.
 */
export async function getModelDriftForActiveModels(mode: TradingMode): Promise<ModelDriftSummary[]> {
  if (mode === 'OFF') {
    return [];
  }

  const tasks: Promise<ModelDriftSummary | null>[] = [];

  for (const symbol of ACTIVE_PAIRS) {
    for (const timeframe of ACTIVE_TIMEFRAMES) {
      tasks.push(
        (async () => {
          try {
            const report = await getModelDrift(symbol, timeframe, mode);
            // Skip models that have no data at all (no score, no status).
            if (report.overall_score == null && !report.health_status) {
              return null;
            }
            return {
              symbol,
              timeframe,
              overall_score: report.overall_score ?? null,
              health_status: normalizeHealthStatus(
                report.overall_score,
                report.health_status,
              ),
              timestamp: report.timestamp,
            };
          } catch {
            return null;
          }
        })(),
      );
    }
  }

  const results = await Promise.all(tasks);
  return results.filter((r): r is ModelDriftSummary => r !== null);
}

/**
 * Fetch the current live market regime for each requested symbol.
 *
 * Sourced from each symbol's most recent 1h signal (the `regime` field on
 * a signal reflects the live market phase at generation time). Symbols with
 * no signal are returned with an "unknown" regime rather than dropped.
 */
export async function getCurrentRegimes(
  symbols: readonly string[] = ACTIVE_PAIRS,
  mode: TradingMode = 'LIVE',
): Promise<CurrentRegime[]> {
  if (mode === 'OFF') {
    return [];
  }

  const base = getApiBaseUrl();

  const tasks = symbols.map(async (symbol): Promise<CurrentRegime> => {
    try {
      const response = await fetchWithRetry(
        `${base}/signals/latest?symbol=${encodeURIComponent(symbol)}&timeframe=1h`,
      );
      const data = await response.json();
      return {
        symbol,
        regime: typeof data?.regime === 'string' && data.regime ? data.regime : 'unknown',
      };
    } catch {
      return { symbol, regime: 'unknown' };
    }
  });

  return Promise.all(tasks);
}

/**
 * Fetch real account equity from Binance Futures.
 * GET /api/account/equity
 *
 * Returns null balances with source='unavailable' if Binance is
 * unreachable — never throws.
 */
export async function getAccountEquity(mode: TradingMode): Promise<AccountEquity> {
  if (mode === 'OFF') {
    return {
      wallet_balance: null,
      unrealized_pnl: null,
      margin_balance: null,
      available_balance: null,
      source: 'unavailable',
      reason: 'mode_off',
    };
  }

  try {
    const base = getApiBaseUrl();
    const response = await fetchWithRetry(`${base}/account/equity`);
    return (await response.json()) as AccountEquity;
  } catch {
    return {
      wallet_balance: null,
      unrealized_pnl: null,
      margin_balance: null,
      available_balance: null,
      source: 'unavailable',
      reason: 'fetch_error',
    };
  }
}

/**
 * Fetch persisted Binance equity snapshots (true account equity over time).
 * GET /api/account/equity-history?range=7d
 *
 * Returns an empty list if no snapshots exist. Never throws.
 */
export async function getAccountEquityHistory(
  range: EquityRange,
  mode: TradingMode,
): Promise<EquitySnapshot[]> {
  if (mode === 'OFF') {
    return [];
  }

  try {
    const base = getApiBaseUrl();
    const endpoint = mode === 'PAPER'
      ? `${base}/paper/equity-history?range=${range}`
      : `${base}/account/equity-history?range=${range}`;
    const response = await fetchWithRetry(endpoint);
    const data = await response.json();
    return Array.isArray(data) ? (data as EquitySnapshot[]) : [];
  } catch {
    return [];
  }
}

/**
 * Fetch the legacy synthetic closed-trade equity curve.
 * GET /api/analytics/closed-trade-equity
 *
 * equity[n] = starting_balance + cumulative_net_realized_pnl[n].
 * Never throws — returns empty list on failure.
 */
export async function getClosedTradeEquity(mode: TradingMode): Promise<EquityPoint[]> {
  if (mode === 'OFF') {
    return [];
  }

  try {
    const base = getApiBaseUrl();
    const response = await fetchWithRetry(`${base}/analytics/closed-trade-equity`);
    const data: ClosedTradeEquityResponse = await response.json();
    return data.equity_curve || [];
  } catch {
    return [];
  }
}

export interface SignalHistoryEntry {
  symbol: string;
  timeframe: string;
  timestamp: string;
  direction: 'long' | 'short' | 'neutral';
  confidence: number;
  created_at: string;
}

export async function getSignalHistory(limit: number, mode: TradingMode): Promise<SignalHistoryEntry[]> {
  if (mode === 'OFF') {
    return [];
  }

  try {
    const base = getApiBaseUrl();
    const response = await fetchWithRetry(
      `${base}/signals/history?limit=${limit}`
    );
    const data = await response.json();
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

/**
 * Fetch live paper trading positions with real-time mark prices.
 * GET /api/paper/positions/live
 */
export async function getLivePositions(mode: TradingMode): Promise<LivePosition[]> {
  return getOpenPositions(mode);
}
