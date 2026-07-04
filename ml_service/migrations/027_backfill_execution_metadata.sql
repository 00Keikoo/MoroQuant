-- Migration 027: Backfill Recoverable Execution Metadata from Signals to Paper Positions
--
-- PROBLEM:
-- Migration 025 recreated paper_positions with an incomplete schema, losing columns.
-- Migration 026 restored the schema, but historical rows contain NULL for:
--   - confidence
--   - regime
--   - timeframe
--   - prob_short
--   - prob_neutral
--   - prob_long
--   - execution_edge
--
-- TARGET STATE:
--   - Retrieve original data from signals table matching signal_id where values are NULL in paper_positions.
--   - Never overwrite existing non-NULL populated metadata in paper_positions.
--   - For execution_edge: compute as max(prob_short, prob_neutral, prob_long) - second_max(prob_short, prob_neutral, prob_long)
--     using identical logic found in paper_broker.py (probability edge filter).
--
-- SAFETY & IDEMPOTENCY:
--   - Atomic transaction.
--   - Safe to run multiple times.
--   - Only update affected rows where values are NULL.

-- Note: Because SQLite does not have array sorting functions built-in,
-- we can express the logic for finding the max and second-max value from
-- prob_short, prob_neutral, and prob_long using conditional logic.
-- Since there are exactly 3 values:
-- Max: CASE WHEN A >= B AND A >= C THEN A WHEN B >= A AND B >= C THEN B ELSE C END
-- Second Max: CASE 
--   WHEN A >= B AND A >= C THEN CASE WHEN B >= C THEN B ELSE C END
--   WHEN B >= A AND B >= C THEN CASE WHEN A >= C THEN A ELSE C END
--   ELSE CASE WHEN A >= B THEN A ELSE B END
-- END

UPDATE paper_positions
SET
    confidence = COALESCE(confidence, (
        SELECT s.confidence 
        FROM signals s 
        WHERE s.id = paper_positions.signal_id
    )),
    regime = COALESCE(regime, (
        SELECT s.regime 
        FROM signals s 
        WHERE s.id = paper_positions.signal_id
    )),
    timeframe = COALESCE(timeframe, (
        SELECT s.timeframe 
        FROM signals s 
        WHERE s.id = paper_positions.signal_id
    )),
    prob_short = COALESCE(prob_short, (
        SELECT s.prob_short 
        FROM signals s 
        WHERE s.id = paper_positions.signal_id
    )),
    prob_neutral = COALESCE(prob_neutral, (
        SELECT s.prob_neutral 
        FROM signals s 
        WHERE s.id = paper_positions.signal_id
    )),
    prob_long = COALESCE(prob_long, (
        SELECT s.prob_long 
        FROM signals s 
        WHERE s.id = paper_positions.signal_id
    )),
    execution_edge = COALESCE(execution_edge, (
        SELECT 
            -- Max
            (CASE 
                WHEN s.prob_short >= s.prob_neutral AND s.prob_short >= s.prob_long THEN s.prob_short
                WHEN s.prob_neutral >= s.prob_short AND s.prob_neutral >= s.prob_long THEN s.prob_neutral
                ELSE s.prob_long
             END)
            -
            -- Second Max
            (CASE
                WHEN s.prob_short >= s.prob_neutral AND s.prob_short >= s.prob_long THEN 
                    CASE WHEN s.prob_neutral >= s.prob_long THEN s.prob_neutral ELSE s.prob_long END
                WHEN s.prob_neutral >= s.prob_short AND s.prob_neutral >= s.prob_long THEN 
                    CASE WHEN s.prob_short >= s.prob_long THEN s.prob_short ELSE s.prob_long END
                ELSE 
                    CASE WHEN s.prob_short >= s.prob_neutral THEN s.prob_short ELSE s.prob_neutral END
             END)
        FROM signals s
        WHERE s.id = paper_positions.signal_id
        AND s.prob_short IS NOT NULL 
        AND s.prob_neutral IS NOT NULL 
        AND s.prob_long IS NOT NULL
    ))
WHERE signal_id IS NOT NULL 
  AND (
       confidence IS NULL 
    OR regime IS NULL 
    OR timeframe IS NULL
    OR prob_short IS NULL 
    OR prob_neutral IS NULL 
    OR prob_long IS NULL 
    OR execution_edge IS NULL
  );
