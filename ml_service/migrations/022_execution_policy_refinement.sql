-- 022_execution_policy_refinement.sql
-- Milestone 5 Refinement: Execution Policy System
-- Remove EQS from persistence, add execution_policy enum

-- Drop EQS column (should be derived, not persisted)
ALTER TABLE paper_positions DROP COLUMN eqs;

-- Add execution_policy column
ALTER TABLE paper_positions ADD COLUMN execution_policy TEXT DEFAULT 'FIXED_SL'
    CHECK(execution_policy IN ('OFF', 'FIXED_SL', 'BREAK_EVEN', 'TRAILING'));

-- Add additional_profit_saved for trailing analytics
ALTER TABLE paper_positions ADD COLUMN additional_profit_saved REAL DEFAULT 0.0;
