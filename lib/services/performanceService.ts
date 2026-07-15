/**
 * Performance Analytics Service
 *
 * Fetches trading performance data from the ML backend.
 * Routes requests based on Trading Mode (OFF/PAPER/LIVE).
 * Includes retry logic, proper typing, and error handling.
 */

import type { TradingMode } from '@/lib/types/ml';

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
  signal?: {
    direction: string;
    confidence: number;
  };
  agreement: string;
}

export interface LivePosition {
  symbol: string;
  side: string;
  entry_price: number;
  mark_price: number;
  quantity: number;
  unrealized_pnl: number;
  take_profit: number | null;
  stop_loss: number | null;
}

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

async function fetchWithRetry(
  url: string,
  retries = 3,
  backoffMs = 1000,
): Promise<Response> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(15000) });

      if (response.ok) return response;

      // Don't retry client errors (4xx)
      if (response.status >= 400 && response.status < 500) {
        throw new Error(`Client error: ${response.status} ${response.statusText}`);
      }

      lastError = new Error(`Server error: ${response.status} ${response.statusText}`);
    } catch (err) {
      if (err instanceof DOMException && err.name === 'TimeoutError') {
        lastError = new Error('Request timed out');
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

  // Route based on Trading Mode
  const endpoint = mode === 'PAPER'
    ? `${base}/paper/analytics`
    : `${base}/analytics/live-performance`;

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

  // Route based on Trading Mode
  const endpoint = mode === 'PAPER'
    ? `${base}/paper/positions/closed${qs ? `?${qs}` : ''}`
    : `${base}/analytics/recent-trades${qs ? `?${qs}` : ''}`;

  const response = await fetchWithRetry(endpoint);
  const data = await response.json();
  return data.trades || data.positions || [];
}

export async function getOpenPositions(mode: TradingMode): Promise<Position[]> {
  if (mode === 'OFF') {
    return [];
  }

  const base = getApiBaseUrl();

  // Route based on Trading Mode
  const endpoint = mode === 'PAPER'
    ? `${base}/paper/positions/live`
    : `${base}/positions/open`;

  const response = await fetchWithRetry(endpoint);
  const data = await response.json();
  return data.positions || [];
}

export async function getRegimePerformance(mode: TradingMode): Promise<Record<string, RegimeMetrics>> {
  if (mode === 'OFF') {
    return {};
  }

  const base = getApiBaseUrl();

  // Route based on Trading Mode
  const endpoint = mode === 'PAPER'
    ? `${base}/paper/analytics/regime`
    : `${base}/analytics/regimes`;

  const response = await fetchWithRetry(endpoint);
  const data = await response.json();

  if (data.status !== 'success') return {};
  return data.regimes || {};
}

export async function getConfidenceBuckets(mode: TradingMode): Promise<Record<string, ConfidenceBucket>> {
  if (mode === 'OFF') {
    return {};
  }

  const base = getApiBaseUrl();

  // Route based on Trading Mode
  const endpoint = mode === 'PAPER'
    ? `${base}/paper/analytics/confidence`
    : `${base}/analytics/confidence`;

  const response = await fetchWithRetry(endpoint);
  const data = await response.json();

  if (data.status !== 'success') return {};
  return data.confidence_buckets || {};
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
  if (mode === 'OFF') {
    return [];
  }

  try {
    const base = getApiBaseUrl();
    const response = await fetchWithRetry(`${base}/paper/positions/live`);
    const data = await response.json();
    return data.positions || [];
  } catch {
    return [];
  }
}
