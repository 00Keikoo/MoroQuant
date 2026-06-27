-- 016_trading_mode_manager.sql
-- Creates the singleton trading_system_state table for the Trading Mode Manager
-- Mode persists across restarts. Only one row (id=1) ever exists.

CREATE TABLE IF NOT EXISTS trading_system_state (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    trading_mode TEXT NOT NULL DEFAULT 'OFF',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed the singleton row if the table was just created.
INSERT OR IGNORE INTO trading_system_state (id, trading_mode) VALUES (1, 'OFF');
