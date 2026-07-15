/**
 * Dashboard Query Keys
 *
 * Hierarchical query key factory for dashboard-specific queries.
 * Global refresh invalidates dashboard queries only, never unrelated caches.
 *
 * Cache dimensions included:
 * - TradingMode (live/paper/replay)
 * - TimeRange (7d/30d/all)
 * - Symbol (EURUSD, etc)
 * - Timeframe (4h, 1d, etc)
 * - Limit (pagination)
 */

export const dashboardKeys = {
  all: ['dashboard'] as const,

  performance: (tradingMode?: string, range?: string) =>
    ['dashboard', 'performance', tradingMode, range] as const,

  positions: (tradingMode?: string) =>
    ['dashboard', 'positions', tradingMode] as const,

  equity: (tradingMode?: string, range?: string) =>
    ['dashboard', 'equity', tradingMode, range] as const,

  models: (tradingMode?: string) =>
    ['dashboard', 'models', tradingMode] as const,

  regimes: (tradingMode?: string, symbol?: string, timeframe?: string) =>
    ['dashboard', 'regimes', tradingMode, symbol, timeframe] as const,

  signals: (tradingMode?: string, limit?: number) =>
    ['dashboard', 'signals', tradingMode, limit] as const,

  execution: (tradingMode?: string, limit?: number) =>
    ['dashboard', 'execution', tradingMode, limit] as const,
} as const;
