-- 017_create_paper_account.sql
-- Creates the singleton paper_account table for the Paper Broker.
-- Holds balance, equity, and unrealized PnL. Only one row (id=1).

CREATE TABLE IF NOT EXISTS paper_account (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    balance REAL NOT NULL DEFAULT 10000.0,
    equity REAL NOT NULL DEFAULT 10000.0,
    unrealized_pnl REAL NOT NULL DEFAULT 0.0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed singleton account with 10000 USDT starting balance.
INSERT OR IGNORE INTO paper_account (id, balance, equity, unrealized_pnl)
VALUES (1, 10000.0, 10000.0, 0.0);
