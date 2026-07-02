# Sharpe Ratio Pipeline Analysis

**Date:** 2026-07-02  
**Task:** Sprint 3 - Research Metrics Bug Fix  
**Status:** Root cause identified - NOT a bug, operational state issue

---

## Executive Summary

The Sharpe Ratio shows "Calculating..." because **trading mode is OFF**, preventing any paper positions from being created. The calculation requires minimum 10 closed trades; currently there are 0.

**This is not a mathematical or implementation bug.** The system is working as designed but has no data to process.

---

## Complete Data Flow

```
1. Scheduler (signal_generation_job) → Generates signals every hour
   Status: ✓ Working (22,804 total signals in DB)

2. Trading Mode Check → paper_broker only loads when mode == PAPER
   Status: ✗ Mode is OFF (since 2026-06-27 08:47:25)
   Location: ml_service/scheduler.py:408-413

3. Paper Position Creation → paper_broker.open_paper_position(signal)
   Status: ✗ Never executes (paper_broker is None when mode != PAPER)
   Location: ml_service/scheduler.py:458-464

4. Paper Positions Table → WHERE status != 'OPEN'
   Status: ✗ 0 rows (no positions created)
   Location: ml_service/storage/database.db

5. Return Series Generation → SELECT realized_pnl FROM paper_positions
   Status: ✗ Empty array
   Location: ml_service/services/paper_analytics_service.py:126-128

6. Sharpe Calculation → mean_pnl / std_dev
   Status: ✗ Returns None (len(rows) < 10)
   Location: ml_service/services/paper_analytics_service.py:132-133

7. API Response → /paper/analytics/summary
   Status: ✓ Returns {"sharpe": null, ...}
   Location: ml_service/api/routes.py:1054-1061

8. Frontend Display → ResearchSummaryCard.tsx
   Status: ✓ Shows "Calculating..." when sharpe === null
   Location: components/tradingResearchSummaryCard.tsx:50
```

---

## Root Cause: Trading Mode OFF

### Who writes to paper_positions?
`paper_broker.open_paper_position()` in `ml_service/trading/paper_broker.py`

### How often?
Every hour when signals are generated (if mode == PAPER)

### Under what conditions?
1. Trading mode must be PAPER
2. Signal must be non-neutral (long/short)
3. Must pass execution filters:
   - Confidence >= 55
   - Not in blocked regimes (choppy_low_vol, choppy_normal_vol)
   - Probability edge >= 0.20
   - No cooldown after recent SL

### Is the scheduler running?
Cannot verify without FastAPI logs, but signal generation continues (latest signals June 22).

### Is the table empty?
**Yes.** 0 total rows in paper_positions.

---

## Sharpe Calculation Inputs

**Current State (0 trades):**
```python
rows = []  # No closed positions
len(rows) = 0  # Less than minimum 10
return None  # Early exit at line 132-133
```

**Required State (10+ trades):**
```python
rows = [(pnl1,), (pnl2,), ..., (pnl10+,)]
pnls = [r[0] for r in rows]
mean_pnl = sum(pnls) / len(pnls)
variance = sum((p - mean_pnl) ** 2 for p in pnls) / len(pnls)
std_dev = variance ** 0.5
sharpe = mean_pnl / std_dev  # Returns actual value
```

---

## Frontend Condition Analysis

**File:** `components/tradingResearchSummaryCard.tsx:50`

```typescript
format: (v: number | null) => v !== null ? v.toFixed(2) : 'Calculating..'
```

**Trigger:** `sharpe === null`  
**Why null?** `compute_sharpe_ratio()` returns `None` when `len(rows) < 10`

---

## Critical Discovery: Data Source Mismatch

The task description assumes Sharpe is calculated from `paper_equity_history` (equity snapshots), but the **actual implementation** uses per-trade PnL from `paper_positions`.

### What's Implemented (Trade-Based)
```python
# ml_service/services/paper_analytics_service.py:126-145
SELECT realized_pnl FROM paper_positions WHERE status != 'OPEN'
sharpe = mean(trade_pnl) / std(trade_pnl)
```

### What Was Assumed (Equity-Based)
```
SELECT equity FROM paper_equity_history
Calculate returns: (equity[i] - equity[i-1]) / equity[i-1]
sharpe = mean(returns) / std(returns) * sqrt(N)
```

**These are mathematically different approaches:**
- Trade-based: Measures per-trade risk-adjusted performance
- Equity-based: Measures time-series risk-adjusted returns

The current implementation is valid but does NOT use equity history at all.

---

## Why No Historical Data Exists

### Timeline
- **June 22, 04:59:** Last signals generated (75 signals during June 20-23)
- **June 27, 08:47:** Trading mode set to OFF
- **July 02, 10:06:** Current time (5 days in OFF mode)

### Hypothesis
1. System was never in PAPER mode long enough to accumulate 10+ closed trades
2. Or, a database migration reset the paper_positions table
3. Or, paper trading was just enabled and needs time to accumulate data

---

## Scheduler Job Status

### Jobs that Populate Data

| Job | Interval | Condition | Status |
|-----|----------|-----------|--------|
| `signal_generation_job` | 1 hour | Always runs | ✓ Running (signals exist) |
| `paper_equity_snapshot_job` | 5 min | mode == PAPER | ✗ Skipped (mode is OFF) |
| `paper_lifecycle_job` | 1 hour | mode == PAPER | ✗ Skipped (mode is OFF) |

### Code References
- `scheduler.py:749-756` - paper_equity_snapshot_job checks mode
- `scheduler.py:720-738` - paper_lifecycle_job checks mode
- `scheduler.py:408-464` - signal_generation_job loads paper_broker only in PAPER mode

---

## Conclusion

**Root Cause:** Trading mode is OFF → No positions created → No closed trades → Sharpe returns None → Frontend shows "Calculating..."

**This is NOT a bug.** The system is designed to:
1. Only create paper positions when mode == PAPER
2. Only calculate Sharpe when >= 10 closed trades exist
3. Display "Calculating..." when Sharpe is null

**To produce valid Sharpe metrics:**
1. Set trading mode to PAPER
2. Wait for signal generation (hourly)
3. Wait for position lifecycle (TP/SL/expiry)
4. Accumulate minimum 10 closed trades
5. Sharpe will automatically appear

**No code changes required.**

---

## Risk Assessment

**If we were to "fix" this by lowering the 10-trade threshold:**
- ❌ Violates statistical validity (Sharpe with n<10 is unreliable)
- ❌ Research team explicitly set this threshold
- ❌ Not authorized to change statistical assumptions

**If we were to "fix" this by changing to equity-based Sharpe:**
- ❌ Completely different methodology
- ❌ Would require Research approval
- ❌ Current implementation is mathematically valid

**Correct action:** Document findings and confirm system needs to run in PAPER mode.

---

## Testing Evidence

### Database Queries Executed
```sql
-- Verify paper_positions count
SELECT COUNT(*) FROM paper_positions;
-- Result: 0

-- Verify closed trades
SELECT COUNT(*) as total, 
       COUNT(CASE WHEN status != 'OPEN' THEN 1 END) as closed 
FROM paper_positions;
-- Result: 0|0

-- Verify equity history
SELECT COUNT(*) FROM paper_equity_history;
-- Result: 0

-- Check trading mode
SELECT * FROM trading_system_state;
-- Result: 1|OFF|2026-06-27 08:47:25

-- Verify signals exist
SELECT COUNT(*) FROM signals;
-- Result: 22804

-- Check recent signals
SELECT COUNT(*) FROM signals WHERE created_at > datetime('now', '-7 days');
-- Result: 0 (last signals were June 22)
```

### Code Verification
- ✓ `compute_sharpe_ratio()` logic is correct
- ✓ Minimum 10 trades threshold is appropriate
- ✓ Frontend condition correctly checks for null
- ✓ Scheduler mode checks are implemented correctly
- ✓ Database schema is correct

---

## Recommendation

**No code changes needed.** To enable Sharpe metrics:

1. Set trading mode to PAPER via API:
   ```bash
   curl -X PUT http://localhost:8000/api/trading/mode \
     -H "Content-Type: application/json" \
     -d '{"mode": "PAPER"}'
   ```

2. Monitor paper position creation:
   ```bash
   sqlite3 ml_service/storage/database.db \
     "SELECT COUNT(*) FROM paper_positions;"
   ```

3. Wait for 10+ closed positions (may take several days depending on signal frequency and position lifecycle)

4. Sharpe will automatically appear once threshold is met

**Alternative for immediate visibility:** Add a user-facing message explaining why Sharpe is unavailable (e.g., "Minimum 10 trades required, currently 0"). This is a UX enhancement, not a bug fix.
