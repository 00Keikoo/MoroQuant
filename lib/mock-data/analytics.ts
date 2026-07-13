export interface Performance {
  grossProfit: number;
  grossLoss: number;
  netProfit: number;
  averageWin: number;
  averageLoss: number;
  winRate: number;
  profitFactor: number;
  sharpeRatio: number;
  maxDrawdown: number;
}

export interface TradeStats {
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  averageTradeLength: string;
  bestTrade: number;
  worstTrade: number;
}

export interface EquityCurvePoint {
  timestamp: string;
  value: number;
}

export interface DrawdownPeriod {
  start: string;
  end: string;
  depth: number;
  duration: string;
}

export interface AnalyticsData {
  performance: Performance;
  tradeStats: TradeStats;
  equityCurve: EquityCurvePoint[];
  drawdownPeriods: DrawdownPeriod[];
}

export const analyticsData: AnalyticsData = {
  performance: {
    grossProfit: 421980.44,
    grossLoss: -12450.12,
    netProfit: 409530.32,
    averageWin: 1204.00,
    averageLoss: -450.20,
    winRate: 0.738,
    profitFactor: 33.89,
    sharpeRatio: 3.42,
    maxDrawdown: -2.14
  },
  tradeStats: {
    totalTrades: 1248,
    winningTrades: 921,
    losingTrades: 327,
    averageTradeLength: "14h 23m",
    bestTrade: 28420.50,
    worstTrade: -3840.20
  },
  equityCurve: [
    { timestamp: "2026-07-06T00:00:00Z", value: 10000000 },
    { timestamp: "2026-07-07T00:00:00Z", value: 10050000 },
    { timestamp: "2026-07-08T00:00:00Z", value: 10025000 },
    { timestamp: "2026-07-09T00:00:00Z", value: 10080000 },
    { timestamp: "2026-07-10T00:00:00Z", value: 10110000 },
    { timestamp: "2026-07-11T00:00:00Z", value: 10095000 },
    { timestamp: "2026-07-12T00:00:00Z", value: 10125000 },
    { timestamp: "2026-07-13T00:00:00Z", value: 10142408 }
  ],
  drawdownPeriods: [
    {
      start: "2026-07-08T00:00:00Z",
      end: "2026-07-08T18:00:00Z",
      depth: -0.0050,
      duration: "18h"
    },
    {
      start: "2026-07-11T00:00:00Z",
      end: "2026-07-11T12:00:00Z",
      depth: -0.0014,
      duration: "12h"
    }
  ]
};
