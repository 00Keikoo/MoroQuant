-- 019_paper_equity_history.sql
-- Creates the paper_equity_history table for equity snapshots.
-- Populated every 5 minutes by the paper_equity_snapshot_job scheduler job.

CREATE TABLE IF NOT EXISTS paper_equity_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equity REAL NOT NULL,
    balance REAL NOT NULL,
    unrealized_pnl REAL NOT NULL,
    snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_paper_equity_snapshot_time ON paper_equity_history(snapshot_time);
