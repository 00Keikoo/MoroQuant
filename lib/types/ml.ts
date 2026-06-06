export interface MLSignal {
  symbol: string;
  timeframe: string;
  direction: 'long' | 'short' | 'neutral';
  confidence: number;
  price: number;
  price_live?: boolean;
  top_features: Record<string, number>;
  regime: string;
  generated_at: string;
  model_type: string;
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
