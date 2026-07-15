/**
 * Dashboard Configuration Constants
 *
 * Centralized configuration for all dashboard timeouts, retry policies, and refresh intervals.
 * Single source of truth for dashboard infrastructure behavior.
 */

// API Timeouts
export const API_TIMEOUT_MS = 30000; // 30 seconds
export const API_TIMEOUT_LONG_MS = 60000; // 60 seconds for expensive operations (model health, drift)

// React Query Configuration
export const QUERY_STALE_TIME = 30000; // 30 seconds - data is considered fresh
export const QUERY_GC_TIME = 300000; // 5 minutes - unused data in cache
export const QUERY_CACHE_TIME = 300000; // 5 minutes - cache retention

// Retry Configuration
export const NETWORK_RETRY_COUNT = 3;
export const DEFAULT_RETRY_COUNT = 2;
export const MAX_BACKOFF_MS = 10000; // 10 seconds max exponential backoff

// Auto Refresh Intervals
export const AUTO_REFRESH_INTERVAL = 60000; // 1 minute - global dashboard refresh
export const EQUITY_REFRESH_INTERVAL = 30000; // 30 seconds - equity curve refresh
export const POSITIONS_REFRESH_INTERVAL = 15000; // 15 seconds - positions refresh
export const MODEL_HEALTH_REFRESH_INTERVAL = 300000; // 5 minutes - model health (expensive)

// Refresh Behavior
export const REFRESH_IN_BACKGROUND = true; // Keep old data while fetching new
export const REFETCH_ON_WINDOW_FOCUS = false; // Disable automatic refetch on focus
export const REFETCH_ON_RECONNECT = true; // Refetch when network reconnects

// Error Handling
export const ENABLE_ERROR_TOAST = false; // Disable global error toasts (widgets handle locally)
export const RETRY_DELAY_MS = 1000; // Base retry delay

// Development
export const DEBUG_QUERIES = false; // Enable React Query DevTools logging
