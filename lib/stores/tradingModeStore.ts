import { create } from 'zustand';
import { getTradingMode } from '@/lib/api/ml-trading';
import type { TradingMode } from '@/lib/types/ml';

interface TradingModeState {
  mode: TradingMode | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  setModeState: (mode: TradingMode) => void;
}

export const useTradingModeStore = create<TradingModeState>((set) => ({
  mode: null,
  loading: true,
  error: null,
  refresh: async () => {
    try {
      const data = await getTradingMode();
      set({ mode: data.mode, error: null, loading: false });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load mode';
      set({ error: msg, loading: false });
    }
  },
  setModeState: (mode) => set({ mode }),
}));
