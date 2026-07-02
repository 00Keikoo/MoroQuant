-- 023_cleanup_dead_columns.sql
-- Schema cleanup: Remove columns with zero data and zero code references
-- Preserves all raw execution state for data lineage integrity

-- CLASSIFICATION AUDIT FINDINGS (36 total columns):
-- ✅ 29 RAW EXECUTION STATE columns (MUST KEEP)
-- ✅ 1 LEGACY OBSERVABILITY column (skip_reason - KEEP for debugging)
-- ✅ 2 ACCEPTABLE DERIVED METRICS (execution_edge, profit_capture_ratio - KEEP)
-- ❌ 4 DEAD COLUMNS (safe to remove - verified zero data, zero references)

-- 1. eqs (Execution Quality Score)
--    - Dead derived metric, never written
--    - Added in migration 021, DROP attempted in 022 but still exists
--    - Always computed dynamically by _calculate_eqs()
--    - Verified: 0 rows with data
ALTER TABLE paper_positions DROP COLUMN eqs;

-- 2. trailing_stop_enabled
--    - Dead column, never written
--    - Redundant with execution_policy column
--    - Verified: 0 rows with data
ALTER TABLE paper_positions DROP COLUMN trailing_stop_enabled;

-- 3. additional_profit_saved
--    - Dead derived metric, never written
--    - Added in migration 022, removed from analytics queries
--    - Verified: 0 rows with data
ALTER TABLE paper_positions DROP COLUMN additional_profit_saved;

-- 4. execution_reason
--    - Dead column, no code references
--    - Never read or written
--    - Verified: 0 rows with data
ALTER TABLE paper_positions DROP COLUMN execution_reason;

-- PRESERVED FOR OBSERVABILITY:
-- - skip_reason: Currently unused but may document future "why didn't we trade?" scenarios
-- - execution_edge: Decision threshold at execution time (computed once at INSERT)
-- - profit_capture_ratio: Performance optimization (computed once at close)

-- Result: 32 columns remain (down from 36)
--   - 29 raw execution state observations
--   - 1 legacy observability column (skip_reason)
--   - 2 acceptable derived metrics (execution_edge, profit_capture_ratio)
--   - 0 dead columns
