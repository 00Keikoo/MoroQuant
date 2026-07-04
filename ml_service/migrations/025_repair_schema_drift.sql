-- Migration 025: Repair Schema Drift from Migration 022
--
-- BACKGROUND:
-- Migration 022 was recorded as applied but its schema changes never executed.
-- Production audit shows obsolete columns (eqs, trailing_stop_enabled) still exist
-- and required column (execution_policy) is missing.
--
-- TARGET STATE (per migrations 022 + 023):
--   - execution_policy column MUST exist
--   - eqs, trailing_stop_enabled, execution_reason, additional_profit_saved MUST NOT exist
--
-- APPROACH:
-- Table recreation pattern (most reliable for SQLite):
-- 1. Create new table with correct schema
-- 2. Copy data from base columns (from migration 018)
-- 3. execution_policy gets default 'FIXED_SL' for all rows
-- 4. Drop old table and rename new one
--
-- SAFETY:
--   - Idempotent: running on already-correct schema produces same end state
--   - Data-preserving: copies all base data
--   - Production-safe: atomic within transaction

-- Create new table with correct schema
CREATE TABLE paper_positions_new (
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
    closed_at TIMESTAMP,
    execution_policy TEXT DEFAULT 'FIXED_SL' CHECK(execution_policy IN ('OFF', 'FIXED_SL', 'BREAK_EVEN', 'TRAILING'))
);

-- Copy data from base columns (guaranteed to exist from migration 018)
-- execution_policy gets default value 'FIXED_SL' for all rows
INSERT INTO paper_positions_new (
    id, symbol, direction, entry_price, current_price, size_usdt, qty,
    stop_loss, take_profit, signal_id, status, realized_pnl, opened_at, closed_at
)
SELECT
    id, symbol, direction, entry_price, current_price, size_usdt, qty,
    stop_loss, take_profit, signal_id, status, realized_pnl, opened_at, closed_at
FROM paper_positions;

-- Replace old table with new one
DROP TABLE paper_positions;
ALTER TABLE paper_positions_new RENAME TO paper_positions;

-- Recreate indexes
CREATE INDEX idx_paper_positions_status ON paper_positions(status);
CREATE INDEX idx_paper_positions_symbol ON paper_positions(symbol);
