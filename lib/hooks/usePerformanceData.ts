/**
 * React Query hooks for performance data fetching.
 *
 * Provides shared cache across dashboard widgets to eliminate duplicate fetches.
 * All hooks use staleTime to prevent redundant API calls within refresh windows.
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTradingMode } from './useTradingMode';
import { dashboardKeys } from '@/lib/query/dashboardKeys';
import {
  QUERY_STALE_TIME,
  QUERY_GC_TIME,
  REFETCH_ON_WINDOW_FOCUS,
  MODEL_HEALTH_REFRESH_INTERVAL,
} from '@/lib/config/dashboard';
import {
  getLivePerformanceReport,
  getOpenPositions,
  getModelDriftForActiveModels,
  getCurrentRegimes,
  getAccountEquityHistory,
  getRegimePerformance,
  getConfidenceBuckets,
  getSignalHistory,
  ACTIVE_PAIRS,
  type LivePerformanceReport,
  type Position,
  type ModelDriftSummary,
  type CurrentRegime,
  type EquitySnapshot,
  type EquityRange,
  type RegimeMetrics,
  type ConfidenceBucket,
  type SignalHistoryEntry,
  type TradingMode,
} from '@/lib/services/performanceService';

// Legacy query keys for backward compatibility (deprecated - use dashboardKeys)
export const performanceKeys = {
  all: ['performance'] as const,
  report: (mode: TradingMode) => [...performanceKeys.all, 'report', mode] as const,
  positions: (mode: TradingMode) => [...performanceKeys.all, 'positions', mode] as const,
  modelHealth: (mode: TradingMode) => [...performanceKeys.all, 'modelHealth', mode] as const,
  regimes: (mode: TradingMode) => [...performanceKeys.all, 'regimes', mode] as const,
  equityHistory: (mode: TradingMode, range: EquityRange) => [...performanceKeys.all, 'equity', mode, range] as const,
  regimePerformance: (mode: TradingMode) => [...performanceKeys.all, 'regimePerformance', mode] as const,
  confidenceBuckets: (mode: TradingMode) => [...performanceKeys.all, 'confidence', mode] as const,
  signalHistory: (mode: TradingMode, limit: number) => [...performanceKeys.all, 'signals', mode, limit] as const,
};

/**
 * Fetch live performance report with centralized cache config.
 * Shared by KpiCards and performance page.
 */
export function usePerformanceReport(options?: { enabled?: boolean }) {
  const { mode } = useTradingMode();

  return useQuery({
    queryKey: dashboardKeys.performance(mode || 'OFF'),
    queryFn: () => getLivePerformanceReport(mode || 'OFF'),
    staleTime: QUERY_STALE_TIME,
    gcTime: QUERY_GC_TIME,
    enabled: options?.enabled !== false && mode !== null,
    refetchOnWindowFocus: REFETCH_ON_WINDOW_FOCUS,
    placeholderData: (previousData) => previousData,
  });
}

/**
 * Fetch open positions with centralized cache config.
 * Shared by KpiCards, OpenPositionsPanel, and performance page.
 */
export function useOpenPositions(options?: { enabled?: boolean }) {
  const { mode } = useTradingMode();

  return useQuery({
    queryKey: dashboardKeys.positions(mode || 'OFF'),
    queryFn: () => getOpenPositions(mode || 'OFF'),
    staleTime: QUERY_STALE_TIME,
    gcTime: QUERY_GC_TIME,
    enabled: options?.enabled !== false && mode !== null,
    refetchOnWindowFocus: REFETCH_ON_WINDOW_FOCUS,
    placeholderData: (previousData) => previousData,
  });
}

/**
 * Fetch model health drift with manual refresh only.
 * No auto-refresh due to expensive computation.
 */
export function useModelHealth(options?: { enabled?: boolean }) {
  const { mode } = useTradingMode();

  return useQuery({
    queryKey: dashboardKeys.models(mode || 'OFF'),
    queryFn: () => getModelDriftForActiveModels(mode || 'OFF'),
    staleTime: Infinity,
    gcTime: QUERY_GC_TIME * 2,
    enabled: options?.enabled !== false && mode !== null,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchInterval: false,
    placeholderData: (previousData) => previousData,
  });
}

/**
 * Fetch current market regimes with centralized cache config.
 */
export function useCurrentRegimes(options?: { enabled?: boolean }) {
  const { mode } = useTradingMode();

  return useQuery({
    queryKey: dashboardKeys.regimes(mode || 'OFF'),
    queryFn: () => getCurrentRegimes(ACTIVE_PAIRS, mode || 'OFF'),
    staleTime: MODEL_HEALTH_REFRESH_INTERVAL,
    gcTime: QUERY_GC_TIME,
    enabled: options?.enabled !== false && mode !== null,
    refetchOnWindowFocus: REFETCH_ON_WINDOW_FOCUS,
    placeholderData: (previousData) => previousData,
  });
}

/**
 * Fetch account equity history with range parameter.
 */
export function useEquityHistory(range: EquityRange, options?: { enabled?: boolean }) {
  const { mode } = useTradingMode();

  return useQuery({
    queryKey: dashboardKeys.equity(mode || 'OFF', range),
    queryFn: () => getAccountEquityHistory(range, mode || 'OFF'),
    staleTime: QUERY_STALE_TIME * 2,
    gcTime: QUERY_GC_TIME,
    enabled: options?.enabled !== false && mode !== null,
    refetchOnWindowFocus: REFETCH_ON_WINDOW_FOCUS,
    placeholderData: (previousData) => previousData,
  });
}

/**
 * Fetch regime performance breakdown.
 */
export function useRegimePerformance(options?: { enabled?: boolean }) {
  const { mode } = useTradingMode();

  return useQuery({
    queryKey: dashboardKeys.performance(mode || 'OFF', 'regimes'),
    queryFn: () => getRegimePerformance(mode || 'OFF'),
    staleTime: QUERY_STALE_TIME,
    gcTime: QUERY_GC_TIME,
    enabled: options?.enabled !== false && mode !== null,
    refetchOnWindowFocus: REFETCH_ON_WINDOW_FOCUS,
    placeholderData: (previousData) => previousData,
  });
}

/**
 * Fetch confidence bucket analytics.
 */
export function useConfidenceBuckets(options?: { enabled?: boolean }) {
  const { mode } = useTradingMode();

  return useQuery({
    queryKey: dashboardKeys.performance(mode || 'OFF', 'confidence'),
    queryFn: () => getConfidenceBuckets(mode || 'OFF'),
    staleTime: QUERY_STALE_TIME,
    gcTime: QUERY_GC_TIME,
    enabled: options?.enabled !== false && mode !== null,
    refetchOnWindowFocus: REFETCH_ON_WINDOW_FOCUS,
    placeholderData: (previousData) => previousData,
  });
}

/**
 * Fetch signal history with centralized cache config.
 */
export function useSignalHistory(limit: number = 10, options?: { enabled?: boolean }) {
  const { mode } = useTradingMode();

  return useQuery({
    queryKey: dashboardKeys.signals(mode || 'OFF', limit),
    queryFn: () => getSignalHistory(limit, mode || 'OFF'),
    staleTime: QUERY_STALE_TIME,
    gcTime: QUERY_GC_TIME,
    enabled: options?.enabled !== false && mode !== null,
    refetchOnWindowFocus: REFETCH_ON_WINDOW_FOCUS,
    placeholderData: (previousData) => previousData,
  });
}

/**
 * Hook to manually refetch all dashboard data.
 * Global refresh invalidates dashboard queries only.
 */
export function useRefreshPerformance() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
  };
}
