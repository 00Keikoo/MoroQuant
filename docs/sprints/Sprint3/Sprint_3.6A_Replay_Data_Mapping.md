# Sprint 3.6A: Replay Engine Data Mapping Audit

**Date**: 2026-07-07  
**Status**: CRITICAL BUG IDENTIFIED

---

## Problem Statement

The Replay Engine is currently using incorrect trade-signal matching logic, causing all divergence metrics to be invalid.

---

## Current INCORRECT Mapping

**File**: `ml_service/research/replay_engine/replay.py:29`

```python
trade_map = {trade.get('id'): trade for trade in snapshot.trades}
```

**Logic**: Iterate signals → look up by signal_id in trade_map

**Bug**: `trade_map` is keyed by `trade.id`, but lookup uses `signal_id`.

**Result**: All lookups fail. No trades are ever matched to signals.

---

## Correct Data Relationship

### Database Schema

**Signal Table**:
```
signals
  - id (PK)
  - symbol
  - timeframe
  - timestamp
  - direction
  - confidence
  - features_json
  - created_at
```

**Trade Table** (paper_positions):
```
paper_positions
  - id (PK)
  - signal_id (FK → signals.id)    ← THIS IS THE RELATIONSHIP
  - symbol
  - direction
  - entry_price
  - status
  - prob_long
  - prob_short
  - prob_neutral
  - ...
```

### Correct Relationship Flow

```
Signal (id=123)
    ↓
    generates decision
    ↓
Trade (signal_id=123)
```

**Cardinality**: 1 Signal → 0..1 Trade

- A signal may or may not result in a trade execution
- A trade MUST reference the signal that caused it via `signal_id`

---

## Fields Required for Deterministic Replay

### From Signal:
- `id` (signal identifier)
- `symbol`
- `timeframe`
- `timestamp`
- `direction` (original signal direction)
- `confidence`
- **Probability fields** (if available):
  - `prob_long`
  - `prob_short`
  - `prob_neutral`

### From Trade (paper_positions):
- `id` (trade identifier)
- **`signal_id`** ← CRITICAL for matching
- `symbol`
- `direction` (actual executed direction)
- `status`
- `prob_long`, `prob_short`, `prob_neutral`
- `opened_at`
- `closed_at`

### Current Snapshot Capture Status

**File**: `ml_service/research/snapshot_engine/capture.py`

✅ **CORRECT**: Snapshot captures both trades and signals separately  
✅ **CORRECT**: Trade records include `signal_id` field  
✅ **CORRECT**: All required probability fields are captured

**Issue**: Replay logic does not use `signal_id` correctly.

---

## Fix Required

**File**: `ml_service/research/replay_engine/replay.py:29`

**Change**:
```python
# WRONG:
trade_map = {trade.get('id'): trade for trade in snapshot.trades}

# CORRECT:
trade_map = {trade.get('signal_id'): trade for trade in snapshot.trades if trade.get('signal_id') is not None}
```

**Rationale**:
- Map trades by their `signal_id`, not their `id`
- Filter out trades with `signal_id=None` (should not exist, but defensive)
- Lookup becomes: `trade_map.get(signal_id)` → returns the trade that executed for that signal

---

## Impact Analysis

### Before Fix (Current State):
- `trade_map` lookup always returns `None`
- All signals are classified as "not executed" (`executed=False`)
- `matched` is always `False` when signal recommended an action
- `consistency_score` is artificially low (~0%)
- Divergence metrics are meaningless

### After Fix:
- Trades correctly matched to their originating signals
- Signals without trades correctly identified as "not executed"
- `matched` reflects whether replay decision aligns with actual execution
- Metrics become scientifically valid

---

## Validation Method

**Test**: Create snapshot with known signal-trade pairs, run replay, verify:

1. Trade with `signal_id=X` is matched to Signal with `id=X`
2. Signal without corresponding trade shows `executed=False`
3. Same snapshot produces identical replay results (determinism)

---

## Additional Findings

### Survivorship Bias Issue

**Current**: Replay iterates over `snapshot.signals`, which is correct.

**Risk**: If signal capture is incomplete, replay will miss decisions.

**Mitigation**: Snapshot capture uses `limit=10000`, should cover recent history.

### Decision Reconstruction

**Current**: Uses `DecisionEngine` from `decision_truth` layer.

**Status**: ✅ Correct approach - deterministic decision logic is isolated.

**Note**: DecisionEngine returns "LONG", "SHORT", or "HOLD", but Trade.direction is "LONG" or "SHORT". When DecisionEngine returns "HOLD", the correct comparison should treat this as "no execution".

---

## Recommendations

1. **Immediate**: Fix line 29 in `replay.py` (trade mapping bug)
2. **Immediate**: Update comparison logic for "HOLD" decisions
3. **Short-term**: Add test for signal_id=None edge case
4. **Short-term**: Verify snapshot capture includes all signals in time range

---

## Risk Assessment

**Current State**: HIGH RISK - All replay results are invalid  
**After Fix**: LOW RISK - Deterministic replay becomes scientifically valid

**Remaining Limitations**:
- Replay assumes snapshot contains complete signal history
- Replay cannot reconstruct decisions if probability fields are missing
- Replay does not account for market state or account constraints
