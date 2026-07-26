-- Migration 029: Enrich Execution Audit Metadata
-- Add source, signal_timestamp, execution_policy, reason_detail to execution_decisions
-- Status: REDUNDANT - These columns already exist in the current schema
-- Keeping this migration as no-op for schema_migrations tracking consistency

-- Note: All target columns already exist in execution_decisions table
-- This migration is intentionally empty to maintain migration number sequence
