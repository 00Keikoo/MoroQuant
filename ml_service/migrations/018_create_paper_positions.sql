-- 018_create_paper_positions.sql
-- Creates paper_positions table for the Paper Broker engine.
-- Tracks open and closed paper positions.

CREATE TABLE IF NOT EXISTS paper_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('LONG', 'SHORT')),
    entry_price REAL NOT NULL,
    current_price REAL,
    size_usdt REAL NOT NULL,
    qty REAL NOT NULL,
    stop_loss REAL,
    take_profit REAL,
    signal_id INTEGER,
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'TP_HIT', 'SL_HIT', 'EXPIRED', 'MANUAL_CLOSE')),
    realized_pnl REAL NOT NULL DEFAULT 0.0,
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP
);

-- Index for fast lookups of open positions.
CREATE INDEX IF NOT EXISTS idx_paper_positions_status ON paper_positions(status);
CREATE INDEX IF NOT EXISTS idx_paper_positions_symbol ON paper_positions(symbol);
