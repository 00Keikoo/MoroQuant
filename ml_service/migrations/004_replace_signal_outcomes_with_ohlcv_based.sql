-- Migration: Replace signal_outcomes with OHLCV-based ground truth tracking
-- Date: 2026-06-20
-- Purpose: Move from trade-based outcomes to OHLCV-based outcome evaluation
--          This enables tracking every signal's outcome regardless of whether it was traded

-- Drop existing indexes and table
DROP INDEX IF EXISTS idx_signal_outcomes_signal_id;
DROP INDEX IF EXISTS idx_signal_outcomes_symbol_time;
DROP INDEX IF EXISTS idx_signal_outcomes_confidence;

-- Preserve existing trade-based outcomes by renaming table
DROP TABLE IF EXISTS signal_outcomes_trade_legacy;
ALTER TABLE signal_outcomes RENAME TO signal_outcomes_trade_legacy;

-- Create new signal_outcomes table for OHLCV-based ground truth tracking
CREATE TABLE signal_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER NOT NULL UNIQUE,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,

    -- Signal prices (copied from signals table at evaluation time)
    entry_price REAL NOT NULL,
    take_profit REAL NOT NULL,
    stop_loss REAL NOT NULL,

    -- Outcome classification
    outcome TEXT CHECK(outcome IN ('win', 'loss', 'timeout')),

    -- Exit details
    exit_price REAL,
    exit_time INTEGER,

    -- Performance metrics for TP/SL optimization
    max_favorable_excursion REAL,
    max_adverse_excursion REAL,

    -- Duration tracking
    holding_hours REAL,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (signal_id) REFERENCES signals(id)
);

-- Indexes for efficient querying
CREATE INDEX idx_signal_outcomes_signal_id
ON signal_outcomes(signal_id);

CREATE INDEX idx_signal_outcomes_symbol_timeframe
ON signal_outcomes(symbol, timeframe);

CREATE INDEX idx_signal_outcomes_outcome
ON signal_outcomes(outcome);

CREATE INDEX idx_signal_outcomes_pending
ON signal_outcomes(signal_id) WHERE outcome IS NULL;

-- Note: Rollback instructions
-- To restore trade-based outcomes:
-- DROP TABLE signal_outcomes;
-- ALTER TABLE signal_outcomes_trade_legacy RENAME TO signal_outcomes;
