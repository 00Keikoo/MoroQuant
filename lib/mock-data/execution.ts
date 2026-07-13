export interface Latency {
  orderToExchange: number;
  marketDataFeed: number;
  signalToOrder: number;
  totalRoundtrip: number;
}

export interface Order {
  id: string;
  instrument: string;
  side: 'BUY' | 'SELL';
  type: 'LIMIT' | 'MARKET';
  price: number;
  size: number;
  filled: number;
  remaining: number;
  status: 'PENDING' | 'PARTIAL' | 'FILLED';
  timestamp: string;
}

export interface OrderFlow {
  totalOrders: number;
  executed: number;
  pending: number;
  cancelled: number;
  fillRate: number;
}

export interface Slippage {
  average: number;
  max: number;
  min: number;
}

export interface ExecutionData {
  latency: Latency;
  activeOrders: Order[];
  orderFlow: OrderFlow;
  slippage: Slippage;
}

export const executionData: ExecutionData = {
  latency: {
    orderToExchange: 1.2,
    marketDataFeed: 0.8,
    signalToOrder: 2.4,
    totalRoundtrip: 4.4
  },
  activeOrders: [
    {
      id: "ord_001",
      instrument: "BTC-USDT-PERP",
      side: "BUY",
      type: "LIMIT",
      price: 63000.00,
      size: 5.00,
      filled: 2.50,
      remaining: 2.50,
      status: "PARTIAL",
      timestamp: "2026-07-13T09:45:12Z"
    },
    {
      id: "ord_002",
      instrument: "ETH-USDT-PERP",
      side: "SELL",
      type: "MARKET",
      price: 3392.10,
      size: 25.00,
      filled: 25.00,
      remaining: 0.00,
      status: "FILLED",
      timestamp: "2026-07-13T09:44:58Z"
    },
    {
      id: "ord_003",
      instrument: "SOL-USDT-PERP",
      side: "BUY",
      type: "LIMIT",
      price: 141.50,
      size: 1000.00,
      filled: 0.00,
      remaining: 1000.00,
      status: "PENDING",
      timestamp: "2026-07-13T09:43:22Z"
    }
  ],
  orderFlow: {
    totalOrders: 1248,
    executed: 92,
    pending: 156,
    cancelled: 1000,
    fillRate: 0.738
  },
  slippage: {
    average: 0.0012,
    max: 0.0084,
    min: 0.0001
  }
};
