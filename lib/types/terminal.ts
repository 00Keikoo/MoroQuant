/**
 * Canonical Frontend Models for Terminal Components
 *
 * These interfaces define the ONLY data contracts that terminal components
 * may consume. Backend-specific field names MUST NOT appear in components.
 * All backend responses are normalized to these canonical models in the
 * service layer (lib/services/terminalService.ts).
 */

export interface Position {
  symbol: string;
  side: "LONG" | "SHORT";
  entry_price: number;
  mark_price: number;
  quantity: number;
  unrealized_pnl: number;
  realized_pnl: number;
  margin: number | null;
  take_profit: number | null;
  stop_loss: number | null;
  confidence: number | null;
  duration_hours: number | null;
  status: string | null;
  // Risk/reward metrics from backend
  risk?: number | null;
  reward?: number | null;
  risk_reward?: number | null;
}

export interface Account {
  equity: number;
  balance: number;
  available_balance: number;
  margin_used: number;
  free_margin: number;
  realized_pnl: number;
  unrealized_pnl: number;
  daily_pnl: number;
  exposure: number;
  last_updated: string;
  // Extended fields from backend normalization
  initial_balance?: number;
  wallet_balance?: number;
  margin_ratio?: number;
  account_health?: number;
  total_return_pct?: number;
}

export interface Performance {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  profit_factor: number;
  expectancy: number;
  sharpe: number;
  sortino: number | null;
  calmar: number | null;
  recovery_factor: number | null;
  max_drawdown: number | null;
  max_drawdown_pct: number | null;
  avg_hold_hours: number | null;
  total_realized_pnl: number;
}

export interface ExecutionAnalytics {
  total_trades: number;
  avg_eqs: number;
  avg_mae: number;
  avg_mfe: number;
  avg_lost_opportunity: number;
  avg_profit_capture: number;
  avg_hold_hours: number;
  trailing_activated: number;
  break_even_saves: number;
  avg_sl_moves: number;
  additional_profit_saved: number;
  exit_reasons: Record<string, number>;
}

export interface RecentTrade {
  symbol: string;
  side: "LONG" | "SHORT";
  entry_time: number;
  exit_time: number;
  duration_minutes: number;
  entry_price: number;
  exit_price: number;
  quantity: number;
  gross_pnl: number;
  commission: number;
  net_pnl: number;
  regime: string;
  confidence: number | null;
  outcome: "win" | "loss" | "breakeven";
}

export interface ResearchSummary {
  active_signals: number;
  model_health: string;
  regime: string;
  confidence_avg: number;
}

export interface EquityPoint {
  timestamp: number;
  equity: number;
  cumulative_pnl: number;
}
