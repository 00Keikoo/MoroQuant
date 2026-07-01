import type {
  LiveMetrics,
  EquityPoint,
  RecentTrade,
  Position,
  RegimeMetrics,
  ConfidenceBucket,
  AccountEquity,
  EquitySnapshot,
  EquityRange,
} from '@/lib/services/performanceService';

export interface TradingDataProvider {
  getAccountEquity(): Promise<AccountEquity>;
  getEquityHistory(range?: EquityRange): Promise<EquitySnapshot[]>;
  getMetrics(): Promise<LiveMetrics | null>;
  getOpenPositions(): Promise<Position[]>;
  getRecentTrades(limit?: number): Promise<RecentTrade[]>;
  getRegimePerformance(): Promise<Record<string, RegimeMetrics>>;
  getConfidenceBuckets(): Promise<Record<string, ConfidenceBucket>>;
  getEquityCurve(): Promise<EquityPoint[]>;
}

export type {
  LiveMetrics,
  EquityPoint,
  RecentTrade,
  Position,
  RegimeMetrics,
  ConfidenceBucket,
  AccountEquity,
  EquitySnapshot,
  EquityRange,
};
