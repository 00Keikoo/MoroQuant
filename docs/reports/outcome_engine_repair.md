# Outcome Engine Repair Report

**Date:** 2026-06-22
**Scope:** Fix P0 bugs identified in [outcome_logic_audit.md](../audits/execution/outcome_logic_audit.md)
**Status:** Complete — all 6 validation tests pass

---

## Summary of Bugs Fixed

### P0 BUG #1: Premature signal_outcomes insertion
**Root cause:** `_mark_checkpoint_checked()` wrote rows into `signal_outcomes` (even with `outcome=NULL` or premature `timeout`). The `get_pending_signals()` query uses `so.id IS NULL` to find pending signals, so any row in `signal_outcomes` — even an incomplete checkpoint row — permanently removed the signal from re-evaluation.

**Fix:** Checkpoints now write to a separate `signal_checkpoints` table. They are monitoring events only. The `signal_outcomes` table is only written to for **final** states: WIN, LOSS, or TIMEOUT (after 7-day expiry). A signal remains in the pending queue until a final outcome is reached.

### P0 BUG #2: 48h evaluation cap
**Root cause:** `evaluate_signal_with_checkpoints()` iterated only through `[1, 4, 12, 24, 48]` hour windows. The maximum window was 48 hours (2 days). The class constant `TIMEOUT_DAYS = 7` was never used in the checkpoint flow. Any TP/SL hit between 48h and 7 days was silently discarded.

**Fix:** Checkpoints remain at `[1, 4, 12, 24, 48]` hours for early WIN/LOSS detection. But after all checkpoints yield timeout, the system performs a **final evaluation** using the full 7-day window (`FINAL_TIMEOUT_DAYS = 7`). TIMEOUT is only assigned after this full scan finds no resolution.

---

## Files Changed

### 1. `ml_service/analytics/outcome_engine.py` (REWRITTEN)

**Key changes:**
- Removed `evaluate_signal_with_checkpoints()` — replaced by `_evaluate_signal_phased()`
- Removed `_mark_checkpoint_checked()` — checkpoints no longer write to `signal_outcomes`
- Added `signal_checkpoints` table creation in `_ensure_checkpoint_table()`
- Added `save_checkpoint()` — writes monitoring events to `signal_checkpoints` (separate table)
- Added `get_checked_checkpoints()` — reads checkpoint history
- Added `_evaluate_signal_phased()` — two-phase evaluation:
  - Phase 1: Checkpoint monitoring (1h/4h/12h/24h/48h) for early WIN/LOSS
  - Phase 2: Final resolution at 7-day expiry
- `get_pending_signals()` unchanged in logic but now guaranteed correct because only final outcomes write to `signal_outcomes`
- `evaluate_pending_outcomes()` simplified — no longer accepts `check_intervals_hours` parameter
- `save_outcome()` documents that it only saves FINAL states
- `SignalOutcome` dataclass documents that `outcome` is always a final state
- Added `CheckpointResult` dataclass for monitoring events
- Added module-level constants: `CHECKPOINT_INTERVALS_HOURS`, `FINAL_TIMEOUT_DAYS`

**State machine:**
```
PENDING ──[TP hit at any checkpoint]──→ WIN (final, saved to signal_outcomes)
PENDING ──[SL hit at any checkpoint]──→ LOSS (final, saved to signal_outcomes)
PENDING ──[TP hit after 48h]────────→ WIN (final, found in 7-day scan)
PENDING ──[SL hit after 48h]────────→ LOSS (final, found in 7-day scan)
PENDING ──[no TP/SL in 7 days]──────→ TIMEOUT (final, saved to signal_outcomes)
PENDING ──[checkpoint timeout]──────→ PENDING (no change, checkpoint recorded in signal_checkpoints)
PENDING ──[not enough time elapsed]──→ PENDING (returns None, no DB write)
```

### 2. `ml_service/migrations/008_repair_premature_outcomes.sql` (NEW)

**Migration steps:**
1. Creates `signal_checkpoints` table for monitoring events
2. Identifies premature `signal_outcomes` rows:
   - `outcome IS NULL` (partial checkpoint row)
   - `outcome = 'timeout'` with signal age < 7 days (premature timeout)
   - `entry_price IS NULL` (legacy trade-based row)
3. Migrates checkpoint flags (`checked_at_Xh`) to `signal_checkpoints` records
4. Deletes premature rows from `signal_outcomes` (signals return to pending queue)
5. Creates temp `_repair_audit` table for verification

**Run with:**
```bash
sqlite3 ml_service/storage/database.db < ml_service/migrations/008_repair_premature_outcomes.sql
```

### 3. `ml_service/scheduler.py` (MODIFIED)

**Changes:**
- Updated `outcome_evaluation_job()` docstring to document two-phase evaluation
- Updated log message to include `still_pending` and `checkpoints_scanned` stats
- Removed reference to deprecated `check_intervals_hours` parameter

### 4. `ml_service/tests/test_outcome_engine_repair.py` (NEW)

**6 validation test cases — ALL PASSING:**

| Test | Scenario | Validates |
|------|----------|-----------|
| 1 | TP hit after 72h | Late winners no longer marked TIMEOUT |
| 2 | SL hit after 60h | Late losses no longer marked TIMEOUT |
| 3 | No TP/SL in 7 days | Correct TIMEOUT only after full expiry |
| 4 | TP hit at 3h | Early WIN finalizes immediately |
| 5 | Checkpoint timeouts only | No signal_outcomes row created |
| 6 | Pending at 6d, timeout at 7d | Signal stays pending until expiry |

**Run with:**
```bash
cd ml_service && python3 tests/test_outcome_engine_repair.py
```

### 5. `OUTCOME_ENGINE_REPAIR.md` (this file)

---

## Data Migration Impact

The migration (008) identifies and repairs existing corrupted rows:

**Categories of repaired rows:**
- `premature_null_outcome`: Rows with `outcome=NULL` created by `_mark_checkpoint_checked()`. These blocked signals from ever being evaluated.
- `premature_timeout_under_7d`: Rows with `outcome='timeout'` assigned before the 7-day window elapsed. Signals that might have been WIN/LOSS between 48h-7d were permanently locked as TIMEOUT.
- `premature_timeout_signal_too_young`: TIMEOUT rows on signals that hadn't existed long enough for any candle data to exist.

After migration, all repaired signals return to the pending queue and will be re-evaluated by the next `outcome_evaluation_job` run using the corrected two-phase logic.

---

## Backward Compatibility

| Component | Impact |
|-----------|--------|
| `signal_outcomes` table | Schema unchanged. Rows now only contain final outcomes. |
| `signal_checkpoints` table | New table. Auto-created by OutcomeEngine on init. |
| `checked_at_Xh` columns | Still exist in signal_outcomes schema (from migration 005). No longer written to. Can be dropped in a future cleanup migration. |
| `get_pending_signals()` | SQL unchanged. Now guaranteed correct because checkpoint events don't write to signal_outcomes. |
| Scheduler API | `evaluate_pending_outcomes()` no longer accepts `check_intervals_hours`. Callers must update. Only caller is `outcome_evaluation_job()` — already updated. |
| Analytics endpoints | `/outcomes/*` endpoints unaffected. They read from signal_outcomes which now has cleaner data. |
| Calibration | `CalibrationTracker` only called for WIN/LOSS final outcomes. Unchanged. |

---

## What Was NOT Changed

- **Prediction logic** — no modifications to `models/predictor.py` or `models/trainer.py`
- **Signal generation** — no changes to signal creation or storage
- **Reconstruction logic** — `analytics/signal_reconstruction.py` untouched
- **Trade aggregation** — `data/outcome_tracking.py` untouched
- **OHLCV ingestion** — data pipeline unchanged

---

## Validation Evidence

```
============================================================
OUTCOME ENGINE REPAIR - VALIDATION TESTS
============================================================
CHECKPOINT_INTERVALS: [1, 4, 12, 24, 48]
FINAL_TIMEOUT_DAYS: 7

TEST 1: TP hit after 72h (was incorrectly TIMEOUT)     PASSED
TEST 2: SL hit after 60h (was incorrectly TIMEOUT)      PASSED
TEST 3: Correct TIMEOUT after 7 days (not premature)     PASSED
TEST 4: Early WIN at checkpoint (should finalize immediately) PASSED
TEST 5: Checkpoint timeouts do NOT create outcome rows  PASSED
TEST 6: Signal stays pending until 7-day final expiry   PASSED

RESULTS: 6 passed, 0 failed, 6 total
ALL TESTS PASSED
```
