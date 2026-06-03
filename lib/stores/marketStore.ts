import { create } from 'zustand';
import { MarketPair, Orderbook, Candlestick, Timeframe, TechnicalIndicators } from '../types';

interface MarketState {
  pairs: Map<string, MarketPair>;
  selectedPair: string;
  orderbooks: Map<string, Orderbook>;
  candlesticks: Map<string, Candlestick[]>;
  timeframe: Timeframe;
  indicators: Map<string, TechnicalIndicators>;

  setPairs: (pairs: MarketPair[]) => void;
  updatePair: (symbol: string, data: Partial<MarketPair>) => void;
  setSelectedPair: (symbol: string) => void;
  updateOrderbook: (symbol: string, orderbook: Orderbook) => void;
  updateCandlesticks: (symbol: string, candlesticks: Candlestick[]) => void;
  setTimeframe: (timeframe: Timeframe) => void;
  updateIndicators: (symbol: string, indicators: TechnicalIndicators) => void;
}

export const useMarketStore = create<MarketState>((set) => ({
  pairs: new Map(),
  selectedPair: 'BTCUSDT',
  orderbooks: new Map(),
  candlesticks: new Map(),
  timeframe: '15m',
  indicators: new Map(),

  setPairs: (pairs) => set((state) => {
    const pairsMap = new Map(state.pairs);
    pairs.forEach(pair => pairsMap.set(pair.symbol, pair));
    return { pairs: pairsMap };
  }),

  updatePair: (symbol, data) => set((state) => {
    const pairsMap = new Map(state.pairs);
    const existing = pairsMap.get(symbol);
    if (existing) {
      pairsMap.set(symbol, { ...existing, ...data });
    }
    return { pairs: pairsMap };
  }),

  setSelectedPair: (symbol) => set({ selectedPair: symbol }),

  updateOrderbook: (symbol, orderbook) => set((state) => {
    const orderbooksMap = new Map(state.orderbooks);
    orderbooksMap.set(symbol, orderbook);
    return { orderbooks: orderbooksMap };
  }),

  updateCandlesticks: (symbol, candlesticks) => set((state) => {
    const candlesticksMap = new Map(state.candlesticks);
    candlesticksMap.set(symbol, candlesticks);
    return { candlesticks: candlesticksMap };
  }),

  setTimeframe: (timeframe) => set({ timeframe }),

  updateIndicators: (symbol, indicators) => set((state) => {
    const indicatorsMap = new Map(state.indicators);
    indicatorsMap.set(symbol, indicators);
    return { indicators: indicatorsMap };
  }),
}));
