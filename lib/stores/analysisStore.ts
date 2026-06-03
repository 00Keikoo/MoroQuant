import { create } from 'zustand';
import { MarketAnalysis } from '../types';

interface AnalysisState {
  analysis: MarketAnalysis | null;
  loading: boolean;
  error: string | null;

  setAnalysis: (analysis: MarketAnalysis) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useAnalysisStore = create<AnalysisState>((set) => ({
  analysis: null,
  loading: false,
  error: null,

  setAnalysis: (analysis) => set({ analysis, error: null }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}));
