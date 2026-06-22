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
