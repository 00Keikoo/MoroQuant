import { MarketPair, Orderbook, Candlestick, Timeframe } from '../types';

const BINANCE_WS_BASE = 'wss://fstream.binance.com/ws';
const BINANCE_API_BASE = 'https://fapi.binance.com/fapi/v1';

export const TOP_FUTURES_PAIRS = [
  'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'ARBUSDT',
  'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'MATICUSDT', 'DOTUSDT',
  'AVAXUSDT', 'LINKUSDT', 'UNIUSDT', 'ATOMUSDT', 'LTCUSDT',
  'NEARUSDT', 'APTUSDT', 'OPUSDT', 'INJUSDT', 'SUIUSDT'
];

const timeframeMap: Record<Timeframe, string> = {
  '1m': '1m',
  '5m': '5m',
  '15m': '15m',
  '1h': '1h',
  '4h': '4h',
  '1D': '1d',
};

export class BinanceWebSocket {
  private ws: WebSocket | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private subscriptions: Set<string> = new Set();

  constructor(
    private onPriceUpdate: (symbol: string, data: Partial<MarketPair>) => void,
    private onOrderbookUpdate: (symbol: string, orderbook: Orderbook) => void
  ) {}

  connect(symbols: string[]) {
    const streams = symbols.flatMap(symbol => [
      `${symbol.toLowerCase()}@ticker`,
      `${symbol.toLowerCase()}@depth20@100ms`,
    ]);

    const wsUrl = `${BINANCE_WS_BASE}/${streams.join('/')}`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('Binance WebSocket connected');
      symbols.forEach(s => this.subscriptions.add(s));
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.e === '24hrTicker') {
          const symbol = data.s;
          this.onPriceUpdate(symbol, {
            symbol,
            price: parseFloat(data.c),
            change24h: parseFloat(data.P),
            volume24h: parseFloat(data.v),
            high24h: parseFloat(data.h),
            low24h: parseFloat(data.l),
          });
        } else if (data.e === 'depthUpdate') {
          const symbol = data.s;
          this.onOrderbookUpdate(symbol, {
            bids: data.b.map((b: string[]) => ({
              price: parseFloat(b[0]),
              quantity: parseFloat(b[1]),
            })),
            asks: data.a.map((a: string[]) => ({
              price: parseFloat(a[0]),
              quantity: parseFloat(a[1]),
            })),
            lastUpdate: data.E,
          });
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket closed, reconnecting...');
      this.reconnectTimeout = setTimeout(() => {
        this.connect(Array.from(this.subscriptions));
      }, 5000);
    };
  }

  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.subscriptions.clear();
  }
}

export async function fetchCandlesticks(
  symbol: string,
  timeframe: Timeframe,
  limit: number = 500
): Promise<Candlestick[]> {
  const interval = timeframeMap[timeframe];
  const url = `/api/binance/klines?symbol=${symbol}&interval=${interval}&limit=${limit}`;

  const response = await fetch(url);
  const data = await response.json();

  if (!Array.isArray(data)) {
    throw new Error(data.msg || 'Binance API error');
  }

  return data.map((candle: any[]) => ({
    time: candle[0] / 1000,
    open: parseFloat(candle[1]),
    high: parseFloat(candle[2]),
    low: parseFloat(candle[3]),
    close: parseFloat(candle[4]),
    volume: parseFloat(candle[5]),
  }));
}

export async function fetchFundingRate(symbol: string): Promise<number> {
  const url = `/api/binance/funding-rate?symbol=${symbol}`;
  const response = await fetch(url);
  const data = await response.json();
  return data[0] ? parseFloat(data[0].fundingRate) : 0;
}

export async function fetchOpenInterest(symbol: string): Promise<number> {
  const url = `/api/binance/open-interest?symbol=${symbol}`;
  const response = await fetch(url);
  const data = await response.json();
  return parseFloat(data.openInterest);
}

export async function fetchLongShortRatio(symbol: string): Promise<number> {
  const url = `/api/binance/long-short-ratio?symbol=${symbol}`;
  const response = await fetch(url);
  const data = await response.json();
  return data[0] ? parseFloat(data[0].longShortRatio) : 1;
}
