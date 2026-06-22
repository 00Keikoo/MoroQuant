-- Migration: Create signal_reconstruction table for legacy signal performance estimation
-- Date: 2026-06-20
-- Purpose: Store ESTIMATED performance data for legacy signals (pre-price-tracking era)
--          WITHOUT modifying the original signals table

-- IMPORTANT: This table contains ESTIMATED data, not actual performance
-- Reconstructed prices and outcomes are approximations based on:
--   - ATR-based TP/SL calculation
--   - OHLCV forward scanning
--   - Entry price estimation from timestamp candle

CREATE TABLE IF NOT EXISTS signal_reconstruction (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('long', 'short')),
    confidence INTEGER NOT NULL,

    -- Reconstructed price levels (ESTIMATED)
    reconstructed_entry_price REAL NOT NULL,
    reconstructed_take_profit REAL NOT NULL,
    reconstructed_stop_loss REAL NOT NULL,

    -- Outcome tracking (ESTIMATED)
    reconstructed_exit_price REAL,
    reconstructed_exit_time INTEGER,
    reconstructed_outcome TEXT CHECK(reconstructed_outcome IN ('win', 'loss', 'timeout')),

    -- Reconstruction metadata
    reconstruction_method TEXT NOT NULL,  -- e.g., 'atr_multiplier', 'close_price_entry'
    reconstruction_confidence TEXT NOT NULL CHECK(reconstruction_confidence IN ('high', 'medium', 'low')),

    -- Source data for traceability
    atr_used REAL NOT NULL,
    tp_multiplier_used REAL NOT NULL,
    sl_multiplier_used REAL NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (signal_id) REFERENCES signals(id)
);

-- Index for joining with signals
CREATE INDEX IF NOT EXISTS idx_signal_reconstruction_signal_id
ON signal_reconstruction(signal_id);

-- Index for performance queries
CREATE INDEX IF NOT EXISTS idx_signal_reconstruction_symbol_time
ON signal_reconstruction(symbol, timeframe);

-- Index for outcome analysis
CREATE INDEX IF NOT EXISTS idx_signal_reconstruction_outcome
ON signal_reconstruction(reconstructed_outcome);

-- Index for confidence-based filtering
CREATE INDEX IF NOT EXISTS idx_signal_reconstruction_confidence
ON signal_reconstruction(confidence DESC);
