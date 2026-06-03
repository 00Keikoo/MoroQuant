import { create } from 'zustand';
import { HyperliquidMarket, Position } from '../types';

interface HyperliquidState {
  markets: HyperliquidMarket[];
  positions: Position[];
  loading: boolean;

  setMarkets: (markets: HyperliquidMarket[]) => void;
  setPositions: (positions: Position[]) => void;
  setLoading: (loading: boolean) => void;
}

export const useHyperliquidStore = create<HyperliquidState>((set) => ({
  markets: [],
  positions: [],
  loading: false,

  setMarkets: (markets) => set({ markets }),
  setPositions: (positions) => set({ positions }),
  setLoading: (loading) => set({ loading }),
}));
