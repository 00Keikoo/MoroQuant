export interface PortfolioSummary {
  totalEquity: number;
  availableBalance: number;
  totalMarginUsed: number;
  unrealizedPnl: number;
  dailyPnl: number;
  dailyReturn: number;
}

export interface PortfolioPosition {
  instrument: string;
  side: 'LONG' | 'SHORT';
  size: number;
  entryPrice: number;
  markPrice: number;
  unrealizedPnl: number;
  leverage: string;
  marginUsed: number;
  weight: number;
}

export interface PortfolioData {
  summary: PortfolioSummary;
  positions: PortfolioPosition[];
  targetWeights: Record<string, number>;
}

export const portfolioData: PortfolioData = {
  summary: {
    totalEquity: 10142408.00,
    availableBalance: 9428826.00,
    totalMarginUsed: 713582.00,
    unrealizedPnl: 24838.25,
    dailyPnl: 142408.20,
    dailyReturn: 1.4
  },
  positions: [
    {
      instrument: "BTC-USDT-PERP",
      side: "LONG",
      size: 14.50,
      entryPrice: 62142.00,
      markPrice: 63410.50,
      unrealizedPnl: 18393.25,
      leverage: "20.0x",
      marginUsed: 42100.00,
      weight: 0.42
    },
    {
      instrument: "ETH-USDT-PERP",
      side: "SHORT",
      size: 125.00,
      entryPrice: 3412.20,
      markPrice: 3392.10,
      unrealizedPnl: 2512.50,
      leverage: "15.0x",
      marginUsed: 28400.00,
      weight: 0.28
    },
    {
      instrument: "SOL-USDT-PERP",
      side: "LONG",
      size: 4200.00,
      entryPrice: 142.10,
      markPrice: 141.95,
      unrealizedPnl: -630.00,
      leverage: "10.0x",
      marginUsed: 59682.00,
      weight: 0.18
    },
    {
      instrument: "XAU-USD",
      side: "LONG",
      size: 1250000,
      entryPrice: 2342.15,
      markPrice: 2345.80,
      unrealizedPnl: 4562.50,
      leverage: "5.0x",
      marginUsed: 585537.50,
      weight: 0.12
    }
  ],
  targetWeights: {
    "BTC-USDT-PERP": 0.40,
    "ETH-USDT-PERP": 0.30,
    "SOL-USDT-PERP": 0.20,
    "XAU-USD": 0.10
  }
};
