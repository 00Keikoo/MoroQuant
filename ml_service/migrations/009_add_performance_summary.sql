-- Migration 009: Add model_performance_summary aggregation table
-- Date: 2026-06-22
-- Purpose: Pre-computed performance summaries per (symbol, timeframe) pair.
--          Auto-updated whenever a final outcome is saved to signal_outcomes.
--          Eliminates expensive full-table scans for dashboard queries.

CREATE TABLE IF NOT EXISTS model_performance_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,

    -- Counts
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    timeouts INTEGER NOT NULL DEFAULT 0,
    total_signals INTEGER NOT NULL DEFAULT 0,

    -- Derived metrics
    win_rate REAL,
    profit_factor_proxy REAL,
    avg_holding_hours REAL,

    -- Bookkeeping
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(symbol, timeframe)
);

CREATE INDEX IF NOT EXISTS idx_perf_summary_symbol
ON model_performance_summary(symbol);

CREATE INDEX IF NOT EXISTS idx_perf_summary_symbol_tf
ON model_performance_summary(symbol, timeframe);
