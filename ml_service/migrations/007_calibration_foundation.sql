-- CALIBRATION MEASUREMENT FOUNDATION
-- Stores calibration statistics for model confidence analysis

CREATE TABLE IF NOT EXISTS model_calibration_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    confidence_bucket TEXT NOT NULL,

    signal_count INTEGER DEFAULT 0,
    win_count INTEGER DEFAULT 0,
    loss_count INTEGER DEFAULT 0,

    avg_confidence REAL,
    actual_win_rate REAL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(symbol, timeframe, confidence_bucket)
);

CREATE INDEX IF NOT EXISTS idx_calibration_symbol_timeframe
ON model_calibration_stats(symbol, timeframe);

CREATE INDEX IF NOT EXISTS idx_calibration_bucket
ON model_calibration_stats(confidence_bucket);

-- ECE (Expected Calibration Error) tracking table
CREATE TABLE IF NOT EXISTS model_calibration_ece (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    timeframe TEXT,
    ece_score REAL NOT NULL,
    max_calibration_error REAL,
    sample_size INTEGER NOT NULL,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ece_calculated
ON model_calibration_ece(calculated_at DESC);
