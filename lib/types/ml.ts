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
