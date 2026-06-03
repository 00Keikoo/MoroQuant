export interface MarketPair {
  symbol: string;
  price: number;
  change24h: number;
  volume24h: number;
  high24h: number;
  low24h: number;
  fundingRate?: number;
  openInterest?: number;
  longShortRatio?: number;
}

export interface OrderbookLevel {
  price: number;
  quantity: number;
}

export interface Orderbook {
  bids: OrderbookLevel[];
  asks: OrderbookLevel[];
  lastUpdate: number;
}

export interface Candlestick {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export type Timeframe = '1m' | '5m' | '15m' | '1h' | '4h' | '1D';

export interface NewsItem {
  id: string;
  title: string;
  description: string;
  url: string;
  source: string;
  publishedAt: string;
  category: 'macro' | 'geopolitical' | 'crypto' | 'central-bank';
  aiAnalysis?: NewsAnalysis;
}

export interface NewsAnalysis {
  cause: string;
  marketImpact: 'bullish' | 'bearish' | 'neutral';
  affectedAssets: string[];
  institutionalPerspective: string;
}

export interface MarketAnalysis {
  sentiment: 'risk-on' | 'risk-off' | 'neutral';
  keyLevels: {
    [symbol: string]: {
      support: number[];
      resistance: number[];
    };
  };
  bias: {
    [symbol: string]: 'long' | 'short' | 'neutral';
  };
  riskFactors: string[];
  summary: string;
  timestamp: number;
}

export interface HyperliquidMarket {
  name: string;
  type: 'crypto' | 'stock' | 'commodity';
  price: number;
  fundingRate: number;
  openInterest: number;
  volume24h: number;
}

export interface Position {
  symbol: string;
  side: 'long' | 'short';
  size: number;
  entryPrice: number;
  leverage: number;
  unrealizedPnl: number;
  liquidationPrice: number;
}

export interface TechnicalIndicators {
  rsi: number;
  macd: {
    macd: number;
    signal: number;
    histogram: number;
  };
  bollingerBands: {
    upper: number;
    middle: number;
    lower: number;
  };
  ema20: number;
  ema50: number;
  ema200: number;
}
