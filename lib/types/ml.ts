export interface MLSignal {
  symbol: string;
  timeframe: string;
  direction: 'long' | 'short' | 'neutral';
  confidence: number;
  price: number;
  price_live?: boolean;
  stop_loss?: number;
  take_profit?: number;
  atr?: number;
  risk_reward?: string;
  valid_until?: string;
  max_hold_candles?: number;
  tp_sl_source?: 'optimized' | 'default';
  top_features: Record<string, number>;
  regime: string;
  generated_at: string;
  model_type: string;
  mtf_conflict?: boolean;
  signal_status?: 'ACTIVE' | 'TP_HIT' | 'SL_HIT' | 'EXPIRED';
  status_reason?: string;
  error?: string;
  message?: string;
}

export interface MLSymbolInfo {
  timeframe: string;
  candle_count: number;
}

export interface MLSymbolsResponse {
  symbols: Record<string, MLSymbolInfo[]>;
  total_symbols: number;
}

export interface MLDbInfo {
  status: string;
  ohlcv_records: number;
  macro_events: number;
  signals: number;
  ohlcv_breakdown: Array<{
    symbol: string;
    timeframe: string;
    count: number;
  }>;
}

export interface BacktestTrade {
  type: 'long' | 'short';
  entry_price: number;
  entry_timestamp: number;
  entry_idx: number;
  exit_price: number;
  exit_timestamp: number;
  exit_idx: number;
  pnl: number;
  pnl_pct: number;
  hold_candles: number;
}

export interface BacktestEquityPoint {
  timestamp: number;
  equity: number;
  signal: string;
}

export interface BacktestMetrics {
  total_return_pct: number;
  win_rate_pct: number;
  profit_factor: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  total_trades: number;
  avg_profit_per_trade: number;
}

export interface BacktestResults {
  symbol: string;
  timeframe: string;
  equity_curve: BacktestEquityPoint[];
  trades: BacktestTrade[];
  trade_count: number;
  metrics?: BacktestMetrics;
  error?: string;
  message?: string;
}

export interface OpenPosition {
  id: string;
  symbol: string;
  direction: 'long' | 'short';
  entry_price: number;
  leverage: number;
  size_usdt: number;
  opened_at: string;
  notes?: string;
}

export interface ClosedTrade {
  id?: number;
  symbol: string;
  direction: 'long' | 'short';
  entry_price: number;
  exit_price: number;
  leverage: number;
  size_usdt: number;
  pnl: number;
  pnl_pct: number;
  opened_at: string;
  closed_at: string;
  notes?: string;
  created_at?: string;
}

export interface TradeHistoryResponse {
  trades: ClosedTrade[];
  summary: {
    total_pnl: number;
    win_rate: number;
    total_trades: number;
    best_trade: ClosedTrade | null;
    worst_trade: ClosedTrade | null;
  };
}

// ── Trading Mode Manager ──────────────────────────────────────────────

export type TradingMode = 'OFF' | 'PAPER' | 'LIVE' | 'MAINTENANCE';

export interface TradingModeResponse {
  mode: TradingMode;
  updated_at: string | null;
}

export interface TradingModeUpdate {
  success: boolean;
  old_mode: TradingMode;
  new_mode: TradingMode;
  error?: string;
  message?: string;
  valid_modes?: TradingMode[];
}

// ── Paper Broker ──────────────────────────────────────────────────────

export type PaperPositionStatus = 'OPEN' | 'TP_HIT' | 'SL_HIT' | 'EXPIRED' | 'MANUAL_CLOSE';

export interface PaperAccount {
  id: number;
  balance: number;
  equity: number;
  unrealized_pnl: number;
  updated_at: string;
}

export interface PaperPosition {
  id: number;
  symbol: string;
  direction: 'LONG' | 'SHORT';
  entry_price: number;
  current_price: number | null;
  size_usdt: number;
  qty: number;
  stop_loss: number | null;
  take_profit: number | null;
  signal_id: number | null;
  status: PaperPositionStatus;
  realized_pnl: number;
  opened_at: string;
  closed_at: string | null;
  mae?: number;
  mfe?: number;
  mae_timestamp?: string;
  mfe_timestamp?: string;
  eqs?: number;
  profit_capture_ratio?: number;
  final_exit_reason?: string;
  trailing_stop_activated?: number;
  sl_move_count?: number;
  break_even_triggered?: number;
  confidence?: number;
  regime?: string;
  timeframe?: string;
  execution_policy?: 'OFF' | 'FIXED_SL' | 'BREAK_EVEN' | 'TRAILING';
  additional_profit_saved?: number;
}

export interface PaperStats {
  open_count: number;
  closed_count: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_realized_pnl: number;
  starting_balance: number;
  max_open_positions: number;
  risk_per_trade_pct: number;
}

export interface PaperPortfolioSummary {
  status: string;
  account: PaperAccount;
  open_positions: PaperPosition[];
  closed_positions: PaperPosition[];
  stats: PaperStats;
  timestamp?: string;
}

// ── Paper Equity History ───────────────────────────────────────────────

export interface PaperEquityPoint {
  timestamp: string;
  equity: number;
  balance: number;
  unrealized_pnl: number;
}

// ── Paper Analytics ────────────────────────────────────────────────────

export interface PaperAnalytics {
  total_trades: number;
  win_rate: number;
  total_realized_pnl: number;
  avg_trade_pnl: number;
  profit_factor: number;
  expectancy: number;
  sharpe_ratio: number | null;
  avg_hold_hours: number;
  open_positions: number;
  closed_positions: number;
  status?: string;
  timestamp?: string;
}

export interface PaperConfidenceBucket {
  bucket: string;
  total_trades: number;
  win_rate: number;
  total_pnl: number;
  avg_pnl: number;
  profit_factor: number;
}

export interface PaperRegimeMetrics {
  regime: string;
  total_trades: number;
  win_rate: number;
  total_pnl: number;
  avg_pnl: number;
}

export interface PaperResearchSummary {
  trades: number;
  win_rate: number;
  profit_factor: number;
  sharpe: number | null;
  expectancy: number;
  avg_hold_hours: number;
  open_positions: number;
  last_updated: string;
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

export interface LivePaperPosition {
  id: number;
  symbol: string;
  direction: 'LONG' | 'SHORT';
  entry_price: number;
  mark_price: number;
  qty: number;
  size_usdt: number;
  floating_pnl: number;
  roi_pct: number;
  duration_hours: number;
  confidence: number | null;
  regime: string | null;
  stop_loss: number | null;
  take_profit: number | null;
  opened_at: string;
}

export interface LivePaperAccount {
  balance: number;
  equity: number;
  unrealized_pnl: number;
  available_balance: number;
}

// ── Paper Trade (flat list item) ─────────────────────────────────────

export interface PaperTrade {
  symbol: string;
  direction: string;
  entry_price: number;
  exit_price: number | null;
  realized_pnl: number;
  opened_at: string;
  closed_at: string | null;
  status: string;
}
