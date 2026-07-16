/**
 * Terminal Service - Frontend Contract Normalization Layer
 *
 * This service is the ONLY translation boundary between backend API responses
 * and terminal components. All backend-specific field names are normalized here.
 * Terminal components MUST NEVER access backend schemas directly.
 *
 * Architecture:
 * Backend API → terminalService (normalizers) → Canonical Models → Components
 */

import type { TradingMode } from '@/lib/types/ml';
import type {
  Account,
  Position,
  Performance,
  ExecutionAnalytics,
  RecentTrade,
  ResearchSummary,
  EquityPoint,
} from '@/lib/types/terminal';

const API_BASE =
  typeof window !== 'undefined'
    ? `${process.env.NEXT_PUBLIC_API_URL || `http://${window.location.hostname}:8000`}/api`
    : 'http://localhost:8000/api';

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

    if (attempt < retries) {
      await new Promise((resolve) => setTimeout(resolve, backoffMs * Math.pow(2, attempt)));
    }
  }

  throw lastError || new Error('Request failed after retries');
}

/**
 * Normalize Account Response
 *
 * Backend (PAPER): GET /api/paper/account/live
 * Returns flat: { balance, equity, unrealized_pnl, available_balance, status, timestamp }
 *
 * Frontend Canonical: Account interface
 */
function normalizeAccountResponse(backend: any): Account {
  const equity = Number(backend.equity || backend.account?.equity) || 0;
  const balance = Number(backend.balance || backend.account?.balance) || 0;
  const unrealized_pnl = Number(backend.unrealized_pnl || backend.account?.unrealized_pnl) || 0;
  const available_balance = Number(backend.available_balance || backend.account?.available_balance) || 0;

  const margin_used = equity > 0 ? equity - available_balance : 0;
  const free_margin = available_balance;

  return {
    equity,
    balance,
    available_balance,
    margin_used,
    free_margin,
    realized_pnl: 0,
    unrealized_pnl,
    daily_pnl: Number(backend.daily_pnl) || 0,
    exposure: Math.abs(unrealized_pnl),
    last_updated: backend.timestamp || new Date().toISOString(),
  };
}

/**
 * Normalize Position Response (Open Positions)
 *
 * Backend (PAPER): GET /api/paper/positions/live
 * Fields: id, symbol, direction, entry_price, mark_price, qty, floating_pnl,
 *         confidence, regime, stop_loss, take_profit
 *
 * Backend (LIVE): GET /api/positions/open
 * Fields: symbol, side, position_amt, entry_price, mark_price, unrealized_pnl,
 *         take_profit, stop_loss, signal
 *
 * Frontend Canonical: Position interface
 */
function normalizePosition(backend: any): Position {
  const side = (backend.direction || backend.side || '').toUpperCase();
  const unrealized_pnl = Number(backend.floating_pnl !== undefined ? backend.floating_pnl : backend.unrealized_pnl) || 0;
  const quantity = Number(backend.qty || backend.position_amt || backend.quantity) || 0;
  const entry_price = Number(backend.entry_price) || 0;
  const mark_price = Number(backend.mark_price) || 0;

  let duration_hours: number | null = null;
  if (backend.opened_at) {
    const openedMs = new Date(backend.opened_at).getTime();
    const nowMs = Date.now();
    duration_hours = (nowMs - openedMs) / (1000 * 60 * 60);
  }

  return {
    symbol: backend.symbol || '',
    side: side === 'LONG' || side === 'SHORT' ? side : 'LONG',
    entry_price,
    mark_price,
    quantity,
    unrealized_pnl,
    realized_pnl: Number(backend.realized_pnl) || 0,
    margin: backend.margin !== undefined ? Number(backend.margin) : null,
    take_profit: backend.take_profit !== undefined ? Number(backend.take_profit) : null,
    stop_loss: backend.stop_loss !== undefined ? Number(backend.stop_loss) : null,
    confidence: backend.confidence !== undefined ? Number(backend.confidence) : null,
    duration_hours,
    status: backend.status || null,
  };
}

/**
 * Normalize Performance Response
 *
 * Backend (PAPER): GET /api/paper/analytics
 * Fields: total_trades, win_rate, total_realized_pnl, avg_trade_pnl,
 *         profit_factor, expectancy, avg_hold_hours, sharpe_ratio
 *
 * Frontend Canonical: Performance interface
 */
function normalizePerformance(backend: any): Performance {
  return {
    total_trades: Number(backend.total_trades) || 0,
    winning_trades: Number(backend.winning_trades) || 0,
    losing_trades: Number(backend.losing_trades) || 0,
    win_rate: Number(backend.win_rate) || 0,
    profit_factor: Number(backend.profit_factor) || 0,
    expectancy: Number(backend.expectancy || backend.avg_trade_pnl) || 0,
    sharpe: Number(backend.sharpe_ratio || backend.sharpe) || 0,
    sortino: backend.sortino !== undefined ? Number(backend.sortino) : null,
    calmar: backend.calmar !== undefined ? Number(backend.calmar) : null,
    recovery_factor: backend.recovery_factor !== undefined ? Number(backend.recovery_factor) : null,
    max_drawdown: backend.max_drawdown !== undefined ? Number(backend.max_drawdown) : null,
    max_drawdown_pct: backend.max_drawdown_pct !== undefined ? Number(backend.max_drawdown_pct) : null,
    avg_hold_hours: backend.avg_hold_hours !== undefined ? Number(backend.avg_hold_hours) : null,
    total_realized_pnl: Number(backend.total_realized_pnl || backend.total_pnl) || 0,
  };
}

/**
 * Normalize Execution Analytics Response
 *
 * Backend (PAPER): GET /api/paper/analytics/execution
 * Returns NESTED: { status, execution: { total_trades, avg_eqs, ... }, timestamp }
 *
 * Frontend Canonical: ExecutionAnalytics interface (FLAT)
 */
function normalizeExecutionAnalytics(backend: any): ExecutionAnalytics {
  const execution = backend.execution || backend;

  return {
    total_trades: Number(execution.total_trades) || 0,
    avg_eqs: Number(execution.avg_eqs) || 0,
    avg_mae: Number(execution.avg_mae) || 0,
    avg_mfe: Number(execution.avg_mfe) || 0,
    avg_lost_opportunity: Number(execution.avg_lost_opportunity) || 0,
    avg_profit_capture: Number(execution.avg_profit_capture) || 0,
    avg_hold_hours: Number(execution.avg_hold_hours) || 0,
    trailing_activated: Number(execution.trailing_activated) || 0,
    break_even_saves: Number(execution.break_even_saves) || 0,
    avg_sl_moves: Number(execution.avg_sl_moves) || 0,
    additional_profit_saved: Number(execution.additional_profit_saved) || 0,
    exit_reasons: execution.exit_reasons || {},
  };
}

/**
 * Normalize Recent Trade Response
 *
 * Backend (PAPER): GET /api/paper/positions/closed
 * Fields: id, symbol, direction, entry_price, current_price, realized_pnl,
 *         opened_at, closed_at, confidence, regime, qty, duration_minutes, signal_id
 *
 * Frontend Canonical: RecentTrade interface
 */
function normalizeRecentTrade(backend: any): RecentTrade {
  const pnl = Number(backend.realized_pnl || backend.net_pnl) || 0;
  const side = (backend.direction || backend.side || '').toUpperCase();

  let entry_time = Date.now();
  let exit_time = Date.now();

  if (backend.opened_at || backend.entry_time) {
    const dateStr = backend.opened_at || backend.entry_time;
    entry_time = new Date(dateStr).getTime();
  }

  if (backend.closed_at || backend.exit_time) {
    const dateStr = backend.closed_at || backend.exit_time;
    exit_time = new Date(dateStr).getTime();
  }

  return {
    symbol: backend.symbol || '',
    side: side === 'LONG' || side === 'SHORT' ? side : 'LONG',
    entry_time,
    exit_time,
    duration_minutes: Number(backend.duration_minutes) || 0,
    entry_price: Number(backend.entry_price) || 0,
    exit_price: Number(backend.current_price || backend.exit_price) || 0,
    quantity: Number(backend.qty || backend.quantity) || 0,
    gross_pnl: pnl,
    commission: Number(backend.commission) || 0,
    net_pnl: pnl,
    regime: backend.regime || 'unknown',
    confidence: backend.confidence !== undefined ? Number(backend.confidence) : null,
    outcome: pnl > 0 ? 'win' : pnl < 0 ? 'loss' : 'breakeven',
  };
}

/**
 * Normalize Research Summary Response
 *
 * Backend (PAPER): GET /api/paper/analytics/summary
 */
function normalizeResearchSummary(backend: any): ResearchSummary {
  return {
    active_signals: Number(backend.active_signals) || 0,
    model_health: backend.model_health || 'unknown',
    regime: backend.regime || 'unknown',
    confidence_avg: Number(backend.confidence_avg || backend.avg_confidence) || 0,
  };
}

/**
 * Normalize Equity History Response
 *
 * Backend (PAPER): GET /api/paper/equity-history
 */
function normalizeEquityPoint(backend: any): EquityPoint {
  return {
    timestamp: new Date(backend.timestamp).getTime(),
    equity: Number(backend.equity) || 0,
    cumulative_pnl: Number(backend.cumulative_pnl) || 0,
  };
}

// ─── PUBLIC API ─────────────────────────────────────────────────────

export async function getAccount(mode: TradingMode): Promise<Account> {
  if (mode === 'OFF') {
    return {
      equity: 0,
      balance: 0,
      available_balance: 0,
      margin_used: 0,
      free_margin: 0,
      realized_pnl: 0,
      unrealized_pnl: 0,
      daily_pnl: 0,
      exposure: 0,
      last_updated: new Date().toISOString(),
    };
  }

  const endpoint = mode === 'PAPER'
    ? `${API_BASE}/paper/account/live`
    : `${API_BASE}/account`;

  const response = await fetchWithRetry(endpoint);
  const data = await response.json();

  return normalizeAccountResponse(data);
}

export async function getPositions(mode: TradingMode): Promise<Position[]> {
  if (mode === 'OFF') {
    return [];
  }

  const endpoint = mode === 'PAPER'
    ? `${API_BASE}/paper/positions/live`
    : `${API_BASE}/positions/open`;

  const response = await fetchWithRetry(endpoint);
  const data = await response.json();

  const positions = data.positions || [];
  return positions.map(normalizePosition);
}

export async function getPerformance(mode: TradingMode): Promise<Performance> {
  if (mode === 'OFF') {
    return {
      total_trades: 0,
      winning_trades: 0,
      losing_trades: 0,
      win_rate: 0,
      profit_factor: 0,
      expectancy: 0,
      sharpe: 0,
      sortino: null,
      calmar: null,
      recovery_factor: null,
      max_drawdown: null,
      max_drawdown_pct: null,
      avg_hold_hours: null,
      total_realized_pnl: 0,
    };
  }

  const endpoint = mode === 'PAPER'
    ? `${API_BASE}/paper/analytics`
    : `${API_BASE}/analytics/performance`;

  const response = await fetchWithRetry(endpoint);
  const data = await response.json();

  return normalizePerformance(data);
}

export async function getExecutionAnalytics(mode: TradingMode): Promise<ExecutionAnalytics> {
  if (mode === 'OFF') {
    return {
      total_trades: 0,
      avg_eqs: 0,
      avg_mae: 0,
      avg_mfe: 0,
      avg_lost_opportunity: 0,
      avg_profit_capture: 0,
      avg_hold_hours: 0,
      trailing_activated: 0,
      break_even_saves: 0,
      avg_sl_moves: 0,
      additional_profit_saved: 0,
      exit_reasons: {},
    };
  }

  const endpoint = mode === 'PAPER'
    ? `${API_BASE}/paper/analytics/execution`
    : `${API_BASE}/analytics/execution`;

  const response = await fetchWithRetry(endpoint);
  const data = await response.json();

  return normalizeExecutionAnalytics(data);
}

export async function getRecentTrades(
  mode: TradingMode,
  limit = 20
): Promise<RecentTrade[]> {
  if (mode === 'OFF') {
    return [];
  }

  const endpoint = mode === 'PAPER'
    ? `${API_BASE}/paper/positions/closed?limit=${limit}`
    : `${API_BASE}/analytics/recent-trades?limit=${limit}`;

  const response = await fetchWithRetry(endpoint);
  const data = await response.json();

  const trades = data.positions || data.trades || [];
  return trades.map(normalizeRecentTrade);
}

export async function getResearchSummary(mode: TradingMode): Promise<ResearchSummary> {
  if (mode === 'OFF') {
    return {
      active_signals: 0,
      model_health: 'unknown',
      regime: 'unknown',
      confidence_avg: 0,
    };
  }

  const endpoint = mode === 'PAPER'
    ? `${API_BASE}/paper/analytics/summary`
    : `${API_BASE}/analytics/research-summary`;

  const response = await fetchWithRetry(endpoint);
  const data = await response.json();

  return normalizeResearchSummary(data);
}

export async function getEquityHistory(mode: TradingMode): Promise<EquityPoint[]> {
  if (mode === 'OFF') {
    return [];
  }

  const endpoint = mode === 'PAPER'
    ? `${API_BASE}/paper/equity-history`
    : `${API_BASE}/account/equity-history`;

  try {
    const response = await fetchWithRetry(endpoint);
    const data = await response.json();

    if (Array.isArray(data)) {
      return data.map(normalizeEquityPoint);
    }

    if (data.equity_curve && Array.isArray(data.equity_curve)) {
      return data.equity_curve.map(normalizeEquityPoint);
    }

    return [];
  } catch (error) {
    console.error('Failed to fetch equity history:', error);
    return [];
  }
}
