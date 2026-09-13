-- Migration 034: Create Snapshots Table
-- Phase 3E-2: Snapshot persistence for research pipeline

-- Snapshots: immutable research state captures
CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    snapshot_data TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp
    ON snapshots(timestamp);

CREATE INDEX IF NOT EXISTS idx_snapshots_created_at
    ON snapshots(created_at DESC);
