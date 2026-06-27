-- 015: Deduplicate signals and enforce uniqueness
--
-- Root cause: generate_signal() was called from realtime API paths
-- (exchange_sync, MTF lookup) which persisted duplicate rows. This
-- migration cleans existing duplicates and prevents future ones.
--
-- The unique constraint is on (symbol, timeframe, direction, timestamp)
-- — the natural key for a signal at a given candle.

-- Step 1: Remove duplicates, keeping the earliest row per natural key.
DELETE FROM signals
WHERE id NOT IN (
    SELECT MIN(id)
    FROM signals
    GROUP BY symbol, timeframe, direction, timestamp
);

-- Step 2: Enforce uniqueness going forward.
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_signal
ON signals (symbol, timeframe, direction, timestamp);
