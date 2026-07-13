export interface Position {
  id: string;
  instrument: string;
  side: 'LONG' | 'SHORT';
  size: number;
  entryPrice: number;
  markPrice: number;
  unrealizedPnl: number;
  pnlPercent: number;
  openTime: string;
}

export interface Trade {
  id: string;
  instrument: string;
  side: 'LONG' | 'SHORT';
  entryPrice: number;
  exitPrice: number;
  size: number;
  realizedPnl: number;
  pnlPercent: number;
  openTime: string;
  closeTime: string;
  duration: string;
}

export interface TradesData {
  activePositions: Position[];
  tradeHistory: Trade[];
}

export const tradesData: TradesData = {
  activePositions: [
    {
      id: "pos_001",
      instrument: "BTC-USDT-PERP",
      side: "LONG",
      size: 14.50,
      entryPrice: 62142.00,
      markPrice: 63410.50,
      unrealizedPnl: 18393.25,
      pnlPercent: 2.04,
      openTime: "2026-07-12T14:23:10Z"
    },
    {
      id: "pos_002",
      instrument: "ETH-USDT-PERP",
      side: "SHORT",
      size: 125.00,
      entryPrice: 3412.20,
      markPrice: 3392.10,
      unrealizedPnl: 2512.50,
      pnlPercent: 0.59,
      openTime: "2026-07-12T16:45:32Z"
    }
  ],
  tradeHistory: [
    {
      id: "trade_001",
      instrument: "BTC-USDT-PERP",
      side: "LONG",
      entryPrice: 61800.00,
      exitPrice: 62500.00,
      size: 10.00,
      realizedPnl: 7000.00,
      pnlPercent: 1.13,
      openTime: "2026-07-11T09:15:00Z",
      closeTime: "2026-07-12T11:30:00Z",
      duration: "26h 15m"
    },
    {
      id: "trade_002",
      instrument: "ETH-USDT-PERP",
      side: "SHORT",
      entryPrice: 3500.00,
      exitPrice: 3420.00,
      size: 150.00,
      realizedPnl: 12000.00,
      pnlPercent: 2.29,
      openTime: "2026-07-10T14:20:00Z",
      closeTime: "2026-07-11T08:45:00Z",
      duration: "18h 25m"
    },
    {
      id: "trade_003",
      instrument: "SOL-USDT-PERP",
      side: "LONG",
      entryPrice: 145.00,
      exitPrice: 143.50,
      size: 5000.00,
      realizedPnl: -7500.00,
      pnlPercent: -1.03,
      openTime: "2026-07-09T10:30:00Z",
      closeTime: "2026-07-09T18:15:00Z",
      duration: "7h 45m"
    }
  ]
};
