-- Migration 008: Repair premature checkpoint outcomes and create signal_checkpoints table
-- Date: 2026-06-22
-- Purpose: Fix P0 BUG #1 (premature signal_outcomes insertion by checkpoints)
--          and P0 BUG #2 (48h evaluation cap masking 7-day expiry window)
--
-- PROBLEM:
-- The old _mark_checkpoint_checked() wrote checkpoint rows into signal_outcomes,
-- which immediately removed signals from the pending evaluation queue (so.id IS NOT NULL).
-- This caused premature TIMEOUT classification and permanent exclusion from re-evaluation.
--
-- FIX:
-- 1. Create signal_checkpoints table for monitoring events (separate from outcomes)
-- 2. Identify and delete premature signal_outcomes rows that were NOT final outcomes
-- 3. Migrate checkpoint data from signal_outcomes to signal_checkpoints
-- 4. Signals with deleted rows will re-enter the pending queue for correct re-evaluation

-- ============================================================
-- STEP 1: Create signal_checkpoints table (monitoring events)
-- ============================================================

CREATE TABLE IF NOT EXISTS signal_checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER NOT NULL,
    checkpoint_hours INTEGER NOT NULL,
    outcome_at_checkpoint TEXT NOT NULL,
    exit_price REAL,
    exit_time INTEGER,
    mfe REAL DEFAULT 0,
    mae REAL DEFAULT 0,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(signal_id, checkpoint_hours)
);

CREATE INDEX IF NOT EXISTS idx_signal_checkpoints_signal
ON signal_checkpoints(signal_id);

-- ============================================================
-- STEP 2: Identify premature outcomes
-- ============================================================
-- A signal_outcomes row is PREMATURE (not final) if:
--   - outcome = 'timeout' AND the signal hasn't existed for >= 7 days
--   - outcome IS NULL (checkpoint partial row with only checked_at_Xh columns set)
--   - entry_price IS NULL (legacy trade-based row, not OHLCV-based)
--
-- These rows were created by checkpoint evaluation and blocked re-evaluation.
-- We must delete them so signals return to the pending queue.

-- Create a temporary table to track what we're repairing (for audit)
CREATE TEMP TABLE IF NOT EXISTS _repair_audit (
    signal_id INTEGER PRIMARY KEY,
    old_outcome TEXT,
    old_exit_price REAL,
    old_exit_time INTEGER,
    checked_at_1h INTEGER,
    checked_at_4h INTEGER,
    checked_at_12h INTEGER,
    checked_at_24h INTEGER,
    checked_at_48h INTEGER,
    repair_reason TEXT,
    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Capture premature rows for audit BEFORE deletion
INSERT OR IGNORE INTO _repair_audit (signal_id, old_outcome, old_exit_price, old_exit_time,
    checked_at_1h, checked_at_4h, checked_at_12h, checked_at_24h, checked_at_48h, repair_reason)
SELECT
    so.signal_id,
    so.outcome,
    so.exit_price,
    so.exit_time,
    so.checked_at_1h,
    so.checked_at_4h,
    so.checked_at_12h,
    so.checked_at_24h,
    so.checked_at_48h,
    CASE
        -- NULL outcome: partial checkpoint row (most premature case)
        WHEN so.outcome IS NULL THEN 'premature_null_outcome'
        -- TIMEOUT but signal hasn't expired for 7 days
        WHEN so.outcome = 'timeout'
             AND so.exit_time IS NOT NULL
             AND (so.exit_time - s.timestamp) < (7 * 24 * 60 * 60 * 1000)
        THEN 'premature_timeout_under_7d'
        -- TIMEOUT with no exit_time but signal too young
        WHEN so.outcome = 'timeout'
             AND (strftime('%s','now') * 1000 - s.timestamp) < (7 * 24 * 60 * 60 * 1000)
        THEN 'premature_timeout_signal_too_young'
        -- No entry_price: legacy trade-based row
        WHEN so.entry_price IS NULL THEN 'legacy_trade_row'
        ELSE 'unknown'
    END
FROM signal_outcomes so
JOIN signals s ON so.signal_id = s.id
WHERE
    -- Only repair rows that are NOT legitimate final outcomes
    (so.outcome IS NULL
     OR (so.outcome = 'timeout'
         AND (
             (so.exit_time IS NOT NULL AND (so.exit_time - s.timestamp) < (7 * 24 * 60 * 60 * 1000))
             OR (so.exit_time IS NULL AND (strftime('%s','now') * 1000 - s.timestamp) < (7 * 24 * 60 * 60 * 1000))
         )
     )
     OR so.entry_price IS NULL
    )
    -- Don't touch rows that came from trade aggregation (they have different columns)
    AND so.entry_price IS NOT NULL OR so.outcome IS NULL;

-- ============================================================
-- STEP 3: Migrate checkpoint flags to signal_checkpoints
-- ============================================================
-- For each premature row with checked_at_Xh flags, create checkpoint records

INSERT OR IGNORE INTO signal_checkpoints (signal_id, checkpoint_hours, outcome_at_checkpoint, mfe, mae)
SELECT
    ra.signal_id,
    1,
    'timeout',
    COALESCE(so.max_favorable_excursion, 0),
    COALESCE(so.max_adverse_excursion, 0)
FROM _repair_audit ra
LEFT JOIN signal_outcomes so ON ra.signal_id = so.signal_id
WHERE ra.checked_at_1h = 1;

INSERT OR IGNORE INTO signal_checkpoints (signal_id, checkpoint_hours, outcome_at_checkpoint, mfe, mae)
SELECT
    ra.signal_id,
    4,
    'timeout',
    COALESCE(so.max_favorable_excursion, 0),
    COALESCE(so.max_adverse_excursion, 0)
FROM _repair_audit ra
LEFT JOIN signal_outcomes so ON ra.signal_id = so.signal_id
WHERE ra.checked_at_4h = 1;

INSERT OR IGNORE INTO signal_checkpoints (signal_id, checkpoint_hours, outcome_at_checkpoint, mfe, mae)
SELECT
    ra.signal_id,
    12,
    'timeout',
    COALESCE(so.max_favorable_excursion, 0),
    COALESCE(so.max_adverse_excursion, 0)
FROM _repair_audit ra
LEFT JOIN signal_outcomes so ON ra.signal_id = so.signal_id
WHERE ra.checked_at_12h = 1;

INSERT OR IGNORE INTO signal_checkpoints (signal_id, checkpoint_hours, outcome_at_checkpoint, mfe, mae)
SELECT
    ra.signal_id,
    24,
    'timeout',
    COALESCE(so.max_favorable_excursion, 0),
    COALESCE(so.max_adverse_excursion, 0)
FROM _repair_audit ra
LEFT JOIN signal_outcomes so ON ra.signal_id = so.signal_id
WHERE ra.checked_at_24h = 1;

INSERT OR IGNORE INTO signal_checkpoints (signal_id, checkpoint_hours, outcome_at_checkpoint, mfe, mae)
SELECT
    ra.signal_id,
    48,
    'timeout',
    COALESCE(so.max_favorable_excursion, 0),
    COALESCE(so.max_adverse_excursion, 0)
FROM _repair_audit ra
LEFT JOIN signal_outcomes so ON ra.signal_id = so.signal_id
WHERE ra.checked_at_48h = 1;

-- ============================================================
-- STEP 4: Delete premature rows from signal_outcomes
-- ============================================================
-- After migrating checkpoint data, delete premature rows so signals
-- return to the pending queue for correct re-evaluation.

DELETE FROM signal_outcomes
WHERE signal_id IN (SELECT signal_id FROM _repair_audit);

-- ============================================================
-- STEP 5: Also fix genuinely premature timeouts that had exit_time
-- ============================================================
-- Some signals may have outcome='timeout' with exit_time set to the
-- 48h mark (from the old checkpoint system). These are NOT final.
-- They should be re-evaluated. But we already caught them in step 2
-- because exit_time - timestamp < 7 days.
-- Verify count:
-- SELECT COUNT(*) FROM _repair_audit WHERE repair_reason LIKE 'premature_timeout%';

-- ============================================================
-- CLEANUP
-- ============================================================
-- The _repair_audit temp table is automatically dropped when connection closes.
-- To inspect results before cleanup, run:
-- SELECT repair_reason, COUNT(*) FROM _repair_audit GROUP BY repair_reason;

-- Note: After this migration, the outcome_evaluation_job will re-evaluate
-- all repaired signals using the new two-phase logic (checkpoints as monitoring,
-- final outcome only at 7-day expiry or earlier WIN/LOSS).
