-- Migration 029: Enrich Execution Audit Metadata
-- Add source, signal_timestamp, execution_policy, reason_detail to execution_decisions

ALTER TABLE execution_decisions ADD COLUMN source TEXT NOT NULL DEFAULT 'PAPER' CHECK(source IN ('PAPER', 'LIVE', 'BACKTEST', 'RESEARCH'));
ALTER TABLE execution_decisions ADD COLUMN signal_timestamp INTEGER;
ALTER TABLE execution_decisions ADD COLUMN execution_policy TEXT;
ALTER TABLE execution_decisions ADD COLUMN reason_detail TEXT;
