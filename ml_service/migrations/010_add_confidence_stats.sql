-- Migration 010: Add model_confidence_stats for confidence-bucket analytics
-- Date: 2026-06-22
-- Purpose: Pre-computed win/loss/timeout counts per (symbol, timeframe, confidence_bucket).
--          Auto-maintained by OutcomeEngine._refresh_confidence_stats() on every
--          final outcome save, so confidence-vs-accuracy queries are O(buckets).
--
-- RELATIONSHIP TO model_calibration_stats (migration 007):
-- model_calibration_stats tracks avg_confidence per bucket for ECE computation.
-- model_confidence_stats (this table) tracks full outcome counts (incl. timeouts)
-- per bucket and the resulting actual_win_rate. The two tables serve different
-- analytics purposes and are maintained independently.

CREATE TABLE IF NOT EXISTS model_confidence_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    confidence_bucket TEXT NOT NULL,

    signal_count INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    timeouts INTEGER NOT NULL DEFAULT 0,

    actual_win_rate REAL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(symbol, timeframe, confidence_bucket)
);

CREATE INDEX IF NOT EXISTS idx_confidence_stats_symbol_tf
ON model_confidence_stats(symbol, timeframe);

CREATE INDEX IF NOT EXISTS idx_confidence_stats_bucket
ON model_confidence_stats(confidence_bucket);
