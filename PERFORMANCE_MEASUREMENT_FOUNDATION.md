# Performance Measurement Foundation

**Date:** 2026-06-22
**Scope:** Pre-computed outcome performance summaries with auto-update
**Status:** Complete — all 6 validation tests pass

---

## Overview

This document describes the `model_performance_summary` aggregation layer: a pre-computed table of per-`(symbol, timeframe)` performance metrics derived from final outcomes in `signal_outcomes`. The summary is updated incrementally whenever a final outcome is saved, so query-time cost is O(rows in summary) rather than O(rows in signal_outcomes).

This builds directly on the corrected outcome state machine from `OUTCOME_ENGINE_REPAIR.md`. Only final outcomes (WIN / LOSS / TIMEOUT) flow into the summary — checkpoint monitoring events never touch it.

---

## Tasks Delivered

### TASK 1 — Aggregation table

**File:** `ml_service/migrations/009_add_performance_summary.sql`
**Also auto-created by:** `OutcomeEngine._ensure_performance_summary_table()` on init

```sql
CREATE TABLE model_performance_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,

    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    timeouts INTEGER NOT NULL DEFAULT 0,
    total_signals INTEGER NOT NULL DEFAULT 0,

    win_rate REAL,                -- wins / (wins + losses), excludes timeouts
    profit_factor_proxy REAL,     -- gross TP distance / gross SL distance
    avg_holding_hours REAL,       -- mean over resolved (win/loss) signals

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(symbol, timeframe)
);
```

The table is created lazily by the engine on first init, so the migration file is optional for fresh deployments but provided for explicit schema management and auditability.

### TASK 2 — Auto-update

**File:** `ml_service/analytics/outcome_engine.py` → `save_outcome()` + `_refresh_performance_summary()`

Every time a final outcome is saved, `save_outcome()` calls `_refresh_performance_summary(symbol, timeframe)` as its final step. The refresh recomputes the entire `(symbol, timeframe)` summary row from `signal_outcomes` and upserts it.

**Why full recompute per pair (not incremental increment):**
- Robust against corrections (a signal re-saved from timeout → win after late data arrives doesn't double-count).
- Robust against migration repairs that delete premature rows.
- Per-pair scans are cheap (a single symbol/timeframe is a small fraction of the table).
- The summary is always exactly consistent with ground truth in `signal_outcomes`.

**Metric definitions:**

| Field | Definition |
|-------|------------|
| `wins` | Count of `outcome='win'` rows for this pair |
| `losses` | Count of `outcome='loss'` rows for this pair |
| `timeouts` | Count of `outcome='timeout'` rows for this pair |
| `total_signals` | `wins + losses + timeouts` |
| `win_rate` | `wins / (wins + losses)` — **excludes timeouts** from the denominator because a timeout is not a directional prediction; the trade never resolved. |
| `profit_factor_proxy` | `sum(|tp - entry| for wins) / sum(|entry - sl| for losses)` — a structural risk/reward proxy computed from the actual signal prices stored at generation time. This is not a dollar PnL figure. |
| `avg_holding_hours` | Mean of `holding_hours` over resolved signals (win/loss only; timeouts have `holding_hours = NULL`). |

### TASK 3 — SQL utility functions

**File:** `ml_service/analytics/performance_summary.py` (NEW)

Three read-only accessors over the summary table:

| Function | Scope | Returns |
|----------|-------|---------|
| `get_model_performance(symbol, timeframe)` | One pair | `Dict` or `None` |
| `get_symbol_performance(symbol)` | All timeframes for a symbol | `List[Dict]` |
| `get_global_performance()` | All pairs aggregated + per-pair breakdown | `Dict` with `pairs` list |

**Global aggregation details:**
- Counts (`wins`, `losses`, `timeouts`, `total_signals`) are simple sums.
- Global `win_rate` = `sum(wins) / sum(wins + losses)` across all pairs.
- Global `profit_factor_proxy` is recomputed from raw `signal_outcomes` rows (not summed from per-pair proxies) because different symbols have different price scales — summing raw distances and dividing once is the only scale-consistent approach.
- Global `avg_holding_hours` is a resolved-signal-weighted average of per-pair averages.

### TASK 4 — Validation

**File:** `ml_service/tests/test_performance_summary.py` (NEW)

6 tests, all passing:

| Test | Validates |
|------|-----------|
| 1 | Table auto-created on engine init; empty accessors return None |
| 2 | Counters increment correctly; win_rate uses decided-only denominator |
| 3 | profit_factor_proxy and avg_holding_hours compute correctly |
| 4 | Multiple (symbol, timeframe) pairs are tracked independently |
| 5 | get_global_performance aggregates across pairs correctly |
| 6 | Re-saving an outcome (correction) does not double-count |

**Run:**
```bash
cd ml_service && python3 tests/test_performance_summary.py
```

---

## Files Changed

| File | Action | Purpose |
|------|--------|---------|
| `ml_service/migrations/009_add_performance_summary.sql` | NEW | Explicit schema for the summary table |
| `ml_service/analytics/outcome_engine.py` | MODIFIED | Added `_ensure_performance_summary_table()`, `_refresh_performance_summary()`, and auto-update hook in `save_outcome()` |
| `ml_service/analytics/performance_summary.py` | NEW | `get_model_performance()`, `get_symbol_performance()`, `get_global_performance()` |
| `ml_service/tests/test_performance_summary.py` | NEW | 6 validation tests |
| `PERFORMANCE_MEASUREMENT_FOUNDATION.md` | NEW | This document |

---

## What Was NOT Changed

- **No UI / dashboard** — the summary is accessible only via the Python utility functions and the table directly.
- **No retraining** — prediction and training code untouched.
- **No new API endpoints** — utilities are Python-level for now. API routes can be added later as a thin wrapper if needed.
- **Outcome evaluation logic** — unchanged beyond the auto-update hook. The state machine from `OUTCOME_ENGINE_REPAIR.md` is preserved exactly.

---

## Validation Evidence

```
PERFORMANCE MEASUREMENT FOUNDATION - VALIDATION TESTS

TEST 1: model_performance_summary auto-created on init          PASSED
TEST 2: Counters increment on save_outcome (win/loss/timeout)   PASSED
TEST 3: profit_factor_proxy from price distances                PASSED
TEST 4: Multiple (symbol, timeframe) pairs tracked independently PASSED
TEST 5: get_global_performance aggregates across pairs          PASSED
TEST 6: Re-saving an outcome (correction) doesn't double-count  PASSED

RESULTS: 6 passed, 0 failed, 6 total
```

Regression check on the outcome engine repair suite:
```
OUTCOME ENGINE REPAIR - VALIDATION TESTS
RESULTS: 6 passed, 0 failed, 6 total
ALL TESTS PASSED
```
