/**
 * Performance Analytics Service
 *
 * Fetches live trading performance data from the ML backend.
 * Includes retry logic, proper typing, and error handling.
 */

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
}

// ─── Model drift / regime types ───────────────────────────────────

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
  overall_score: number;
  health_status: 'green' | 'yellow' | 'red';
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

export async function getLivePerformanceReport(): Promise<LivePerformanceReport> {
  const base = getApiBaseUrl();
  const response = await fetchWithRetry(`${base}/analytics/live-performance`);

  const data: LivePerformanceReport = await response.json();

  if (data.status !== 'success' && data.status !== 'no_data') {
    throw new Error(`Unexpected status: ${data.status}`);
  }

  return data;
}

export async function getOpenPositions(): Promise<Position[]> {
  const base = getApiBaseUrl();
  const response = await fetchWithRetry(`${base}/positions/open`);
  const data = await response.json();
  return data.positions || [];
}

export async function getRegimePerformance(): Promise<Record<string, RegimeMetrics>> {
  const base = getApiBaseUrl();
  const response = await fetchWithRetry(`${base}/analytics/regimes`);
  const data = await response.json();

  if (data.status !== 'success') return {};
  return data.regimes || {};
}

export async function getConfidenceBuckets(): Promise<Record<string, ConfidenceBucket>> {
  const base = getApiBaseUrl();
  const response = await fetchWithRetry(`${base}/analytics/confidence`);
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
): Promise<ModelDriftReport> {
  const base = getApiBaseUrl();
  const response = await fetchWithRetry(
    `${base}/models/${encodeURIComponent(symbol)}/${encodeURIComponent(timeframe)}/drift`,
  );
  return (await response.json()) as ModelDriftReport;
}

function normalizeHealthStatus(
  score: number | undefined,
  fallback: string,
): 'green' | 'yellow' | 'red' {
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
  return 'red';
}

/**
 * Fetch drift summaries for all active production models in parallel.
 *
 * There is no "list all models" endpoint, so we fan out over the hardcoded
 * ACTIVE_PAIRS × ACTIVE_TIMEFRAMES grid. Each model is fetched independently;
 * a failure on one model is logged and dropped so the panel never blanks.
 */
export async function getModelDriftForActiveModels(): Promise<ModelDriftSummary[]> {
  const tasks: Promise<ModelDriftSummary | null>[] = [];

  for (const symbol of ACTIVE_PAIRS) {
    for (const timeframe of ACTIVE_TIMEFRAMES) {
      tasks.push(
        (async () => {
          try {
            const report = await getModelDrift(symbol, timeframe);
            // Skip models that simply have no data (error/no_model responses).
            if (typeof report.overall_score !== 'number' && !report.health_status) {
              return null;
            }
            return {
              symbol,
              timeframe,
              overall_score:
                typeof report.overall_score === 'number' ? report.overall_score : 0,
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
): Promise<CurrentRegime[]> {
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
