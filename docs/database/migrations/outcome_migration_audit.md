# Outcome Migration Audit Report

## Part 1: Migration Audit

### Legitimate Outcomes Safety Analysis
Legitimate outcomes (`win` and `loss`) **cannot** be accidentally deleted by the migration. 

### Precedence Bug Analysis
There is a logic parsing bug in the `WHERE` clause of the migration script (`008_repair_premature_outcomes.sql` lines 96-106):
```sql
WHERE
    (so.outcome IS NULL
     OR (so.outcome = 'timeout'
         AND (
             (so.exit_time IS NOT NULL AND (so.exit_time - s.timestamp) < (7 * 24 * 60 * 60 * 1000))
             OR (so.exit_time IS NULL AND (strftime('%s','now') * 1000 - s.timestamp) < (7 * 24 * 60 * 60 * 1000))
         )
     )
     OR so.entry_price IS NULL
    )
    AND so.entry_price IS NOT NULL OR so.outcome IS NULL;
```

Because `AND` has higher precedence than `OR` in SQLite, this expression is evaluated as:
```sql
(
  (
    so.outcome IS NULL 
    OR (so.outcome = 'timeout' AND ( ... )) 
    OR so.entry_price IS NULL
  ) 
  AND so.entry_price IS NOT NULL
) 
OR (so.outcome IS NULL)
```

### Impact of Precedence Logic on Row Deletion
1. **Legitimate `win` and `loss` Outcomes (`so.outcome IN ('win', 'loss')`):**
   - For these rows, `so.outcome IS NULL` is `FALSE`.
   - `so.outcome = 'timeout'` is `FALSE`.
   - If `so.entry_price` is not null, `so.entry_price IS NULL` is `FALSE`.
   - Therefore, the left side of the `AND` is `FALSE`, making the entire first expression `FALSE`.
   - Since `so.outcome IS NULL` is also `FALSE`, the entire condition is `FALSE`. 
   - **Result:** Legitimate outcomes are completely safe from deletion.

2. **Legacy Trade Rows (`so.entry_price IS NULL`):**
   - If `so.entry_price IS NULL` is `TRUE` and `so.outcome` is not null (e.g. `'win'` or `'loss'`):
     - The first block `(so.outcome IS NULL OR ... OR so.entry_price IS NULL)` is `TRUE`.
     - However, the `AND so.entry_price IS NOT NULL` evaluates to `FALSE` (since it is null).
     - The `OR so.outcome IS NULL` evaluates to `FALSE` (since it is `'win'` or `'loss'`).
     - **Result:** The condition evaluates to `FALSE`. Legacy trade rows with non-null outcomes will **not** be repaired or deleted, contrary to the commented intent.

---

## Part 2: False Positive Risk

### Audit of `premature_timeout_under_7d` Logic
Valid timeouts could be falsely identified as premature and deleted under the following conditions:

1. **System Clock Discrepancy (Timezone/NTP Drift):**
   - The query uses `strftime('%s','now') * 1000` to fetch the current system time in milliseconds.
   - If the system executing the migration has a clock that is significantly behind (e.g., timezone mismatch, NTP drift, or container clock synchronization failure), a signal that is actually older than 7 days may appear to be less than 7 days old.
   - **Result:** The valid timeout will be categorized as `premature_timeout_signal_too_young` and deleted.

2. **Database Restores / Historical Migrations:**
   - If historical DB snapshots are restored and migrated on a local instance where "now" is set to a historical time, or if the database contains signals created in a future-dated configuration (testing), valid older timeouts could be caught and removed.

---

## Part 3: Rollback Safety

### Reversibility Assessment
The migration is **not reversible** in its current form. 
- It creates `_repair_audit` as a `TEMP TABLE`.
- Temporary tables are stored in memory or temp storage and are automatically destroyed when the database connection closes.
- Once the migration run completes and the sqlite3 process exits, the audit trail of deleted `signal_outcomes` is lost forever.

### Proposed Rollback Strategy
To make the migration reversible, implement a persistent backup table instead of a temporary table:

1. **Modify Step 2 to use a persistent backup table:**
   ```sql
   CREATE TABLE IF NOT EXISTS backup_signal_outcomes_008 (
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
   ```

2. **Rollback SQL Script (`008_rollback_repair.sql`):**
   ```sql
   -- Restore deleted rows to signal_outcomes
   INSERT OR IGNORE INTO signal_outcomes (
       signal_id, symbol, timeframe, entry_price, take_profit, stop_loss,
       outcome, exit_price, exit_time, checked_at_1h, checked_at_4h,
       checked_at_12h, checked_at_24h, checked_at_48h
   )
   SELECT 
       b.signal_id, s.symbol, s.timeframe, s.entry_price, s.take_profit, s.stop_loss,
       b.old_outcome, b.old_exit_price, b.old_exit_time, b.checked_at_1h, b.checked_at_4h,
       b.checked_at_12h, b.checked_at_24h, b.checked_at_48h
   FROM backup_signal_outcomes_008 b
   JOIN signals s ON b.signal_id = s.id;

   -- Clean up new tables and backup
   DROP TABLE IF EXISTS signal_checkpoints;
   DROP TABLE IF EXISTS backup_signal_outcomes_008;
   ```

---

## Part 4: Post-Migration Validation

The following SQL verification queries must be run after the migration to ensure data integrity:

### 1. No Orphan Checkpoints
Verify that all migrated checkpoints correspond to existing signals:
```sql
SELECT COUNT(*) AS orphan_checkpoint_count
FROM signal_checkpoints sc
LEFT JOIN signals s ON sc.signal_id = s.id
WHERE s.id IS NULL;
```
*Expected Result:* `0`

### 2. No Duplicate Outcomes
Verify that no signal has duplicate outcomes:
```sql
SELECT COUNT(signal_id) - COUNT(DISTINCT signal_id) AS duplicate_outcome_count
FROM signal_outcomes;
```
*Expected Result:* `0`

### 3. Pending Queue Restoration Check
Verify that all signals flagged for repair that should be pending (non-neutral directions and non-null entry prices) have successfully returned to the pending queue:
```sql
SELECT COUNT(*) AS signals_failed_to_return_to_queue
FROM _repair_audit ra
JOIN signals s ON ra.signal_id = s.id
LEFT JOIN signal_outcomes so ON ra.signal_id = so.signal_id
WHERE s.entry_price IS NOT NULL
  AND s.direction != 'neutral'
  AND so.id IS NOT NULL;
```
*Expected Result:* `0` (This confirms every repaired signal now has no row in `signal_outcomes` and is correctly selected by `get_pending_signals()`).
