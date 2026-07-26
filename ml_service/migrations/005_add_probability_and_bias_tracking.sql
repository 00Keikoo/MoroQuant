-- Migration 005: Add raw probability storage and bias tracking
-- Purpose: Enable calibration analysis and bias monitoring

-- Add raw probability columns to signals table
ALTER TABLE signals ADD COLUMN prob_short REAL;
ALTER TABLE signals ADD COLUMN prob_neutral REAL;
ALTER TABLE signals ADD COLUMN prob_long REAL;

-- Note: tp_multiplier, sl_multiplier, labeling_method already added in migration 001
-- Skipping duplicate column additions for idempotency

-- Add intermediate outcome checkpoints to signal_outcomes table
ALTER TABLE signal_outcomes ADD COLUMN checked_at_1h INTEGER DEFAULT 0;
ALTER TABLE signal_outcomes ADD COLUMN checked_at_4h INTEGER DEFAULT 0;
ALTER TABLE signal_outcomes ADD COLUMN checked_at_12h INTEGER DEFAULT 0;
ALTER TABLE signal_outcomes ADD COLUMN checked_at_24h INTEGER DEFAULT 0;
ALTER TABLE signal_outcomes ADD COLUMN checked_at_48h INTEGER DEFAULT 0;
ALTER TABLE signal_outcomes ADD COLUMN first_check_hours REAL;

-- Create model bias tracking table
CREATE TABLE IF NOT EXISTS model_bias_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_version TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    long_count INTEGER DEFAULT 0,
    short_count INTEGER DEFAULT 0,
    neutral_count INTEGER DEFAULT 0,
    avg_confidence_long REAL,
    avg_confidence_short REAL,
    avg_confidence_neutral REAL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(model_version, symbol, timeframe)
);

CREATE INDEX IF NOT EXISTS idx_model_bias_model_version
ON model_bias_stats(model_version, last_updated DESC);
