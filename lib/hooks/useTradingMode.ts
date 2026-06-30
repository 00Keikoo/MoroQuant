'use client';

import { useEffect } from 'react';
import { useTradingModeStore } from '@/lib/stores/tradingModeStore';
import type { TradingMode } from '@/lib/types/ml';

const REFRESH_MS = 30_000;

export interface UseTradingModeResult {
  mode: TradingMode | null;
  isPaper: boolean;
  isLive: boolean;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

/**
 * React hook that subscribes to the current trading mode and
 * auto-refreshes every 30 seconds via a shared Zustand store.
 *
 * Returns convenience flags `isPaper` and `isLive` so consumers can
 * branch data-source selection without re-implementing the mode check.
 */
export function useTradingMode(): UseTradingModeResult {
  const { mode, loading, error, refresh } = useTradingModeStore();

  useEffect(() => {
    // Fetch initial state if it's not yet populated
    if (mode === null && loading) {
      refresh();
    }
    const interval = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(interval);
  }, [refresh, mode, loading]);

  return {
    mode,
    isPaper: mode === 'PAPER',
    isLive: mode === 'LIVE',
    loading,
    error,
    refresh,
  };
}

