'use client';

import { useState, useEffect, useCallback } from 'react';
import { getTradingMode } from '@/lib/api/ml-trading';
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
 * auto-refreshes every 30 seconds.
 *
 * Returns convenience flags `isPaper` and `isLive` so consumers can
 * branch data-source selection without re-implementing the mode check.
 */
export function useTradingMode(): UseTradingModeResult {
  const [mode, setMode] = useState<TradingMode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await getTradingMode();
      setMode(data.mode);
      setError(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load mode';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(interval);
  }, [refresh]);

  return {
    mode,
    isPaper: mode === 'PAPER',
    isLive: mode === 'LIVE',
    loading,
    error,
    refresh,
  };
}
