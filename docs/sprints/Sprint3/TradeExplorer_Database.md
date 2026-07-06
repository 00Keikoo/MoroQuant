# Trade Explorer - Database Schema Requirements

**Sprint 3, Task 3.1**  
**Date:** 2026-07-06  
**Status:** Design Phase

## Executive Summary

Trade Explorer MVP uses **existing schema** with no modifications. All required data exists in `paper_positions`, `paper_account`, `paper_equity_history`, and `signals` tables.

**Schema Changes Required:** None for MVP  
**Optional Enhancements:** Documented for future phases

---

## Current Schema

### paper_positions

**Purpose:** Core table tracking all paper trading positions (open and closed)

```sql
CREATE TABLE IF NOT EXISTS "paper_positions" (
    -- Core Position Data
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('LONG', 'SHORT')),
    entry_price REAL NOT NULL,
    current_price REAL,
    size_usdt REAL NOT NULL,
    qty REAL NOT NULL,
    stop_loss REAL,
    take_profit REAL,
    signal_id INTEGER,
    status TEXT NOT NULL DEFAULT 'OPEN' 
        CHECK(status IN ('OPEN', 'TP_HIT', 'SL_HIT', 'EXPIRED', 'MANUAL_CLOSE')),
    realized_pnl REAL NOT NULL DEFAULT 0.0,
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,

    -- Signal Attribution (Migration 020)
    confidence INTEGER,
    regime TEXT,
    timeframe TEXT,
    prob_short REAL,
    prob_neutral REAL,
    prob_long REAL,
    execution_edge REAL,
    skip_reason TEXT,

    -- Execution Intelligence (Migration 021)
    mae REAL DEFAULT 0.0,
    mfe REAL DEFAULT 0.0,
    mae_timestamp TIMESTAMP,
    mfe_timestamp TIMESTAMP,
    profit_capture_ratio REAL,
    final_exit_reason TEXT,
    trailing_stop_activated INTEGER DEFAULT 0,
    sl_move_count INTEGER DEFAULT 0,
    break_even_triggered INTEGER DEFAULT 0,

    -- Execution Policy (Migration 022)
    execution_policy TEXT DEFAULT 'FIXED_SL' 
        CHECK(execution_policy IN ('OFF', 'FIXED_SL', 'BREAK_EVEN', 'TRAILING'))
);

-- Existing Indexes
CREATE INDEX idx_paper_positions_status ON paper_positions(status);
CREATE INDEX idx_paper_positions_symbol ON paper_positions(symbol);
```

**Trade Explorer Usage:**
- ✅ All core trade data available
- ✅ Execution intelligence metrics (MAE, MFE, PCR)
- ✅ Signal attribution fields
- ✅ Execution policy tracking
- ✅ Sufficient for MVP with no changes

---

### signals

**Purpose:** ML signal metadata for attribution

```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    direction TEXT NOT NULL,
    confidence INTEGER,
    regime TEXT,
    features_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    signal_status TEXT DEFAULT 'ACTIVE',
    status_updated_at TIMESTAMP
);
```

**Trade Explorer Usage:**
- ✅ JOIN via `paper_positions.signal_id`
- ✅ Provides additional signal context
- ✅ No changes required

---

### paper_account

**Purpose:** Singleton account balance/equity snapshot

```sql
CREATE TABLE IF NOT EXISTS paper_account (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    balance REAL NOT NULL DEFAULT 10000.0,
    equity REAL NOT NULL DEFAULT 10000.0,
    unrealized_pnl REAL NOT NULL DEFAULT 0.0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Trade Explorer Usage:**
- ✅ Used for account context (not per-trade)
- ✅ No changes required

---

### paper_equity_history

**Purpose:** Time-series equity snapshots (5-minute intervals)

```sql
CREATE TABLE IF NOT EXISTS paper_equity_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equity REAL NOT NULL,
    balance REAL NOT NULL,
    unrealized_pnl REAL NOT NULL,
    snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_paper_equity_snapshot_time 
    ON paper_equity_history(snapshot_time);
```

**Trade Explorer Usage:**
- ✅ Equity curve integration
- ⚠️ 5-minute granularity (not per-trade)
- ✅ Sufficient for MVP

---

## Derived Metrics (Computed at Query Time)

Trade Explorer computes these metrics from existing data (no schema changes):

### Execution Quality Score (EQS)

```sql
-- Computed in application layer or SQL
CASE 
    WHEN size_usdt > 0 THEN
        50 + 
        COALESCE((profit_capture_ratio * 30), 0) +
        CASE WHEN mae < -0.02 
            THEN (ABS(mae) * -100) 
            ELSE 10 END +
        CASE status
            WHEN 'TP_HIT' THEN 20
            WHEN 'SL_HIT' THEN 5
            ELSE 10 END
    ELSE 0
END as eqs
```

**Source Data:** `mae`, `mfe`, `profit_capture_ratio`, `status`, `size_usdt`

---

### Execution Classification

```sql
-- Computed in application layer
CASE
    WHEN mfe > 0.02 AND profit_capture_ratio > 0.5 
        THEN 'MODEL_CORRECT_EXECUTION_CORRECT'
    WHEN mfe > 0.02 AND profit_capture_ratio <= 0.5 
        THEN 'MODEL_CORRECT_EXECUTION_WEAK'
    WHEN mfe <= 0.02 AND realized_pnl >= 0 
        THEN 'MODEL_WEAK_EXECUTION_CORRECT'
    WHEN mfe <= 0.02 AND realized_pnl < 0 
        THEN 'MODEL_WEAK_EXECUTION_WEAK'
    ELSE 'UNKNOWN'
END as execution_classification
```

**Source Data:** `mfe`, `profit_capture_ratio`, `realized_pnl`

---

### Duration

```sql
-- Duration in hours
CAST((julianday(closed_at) - julianday(opened_at)) * 24 AS REAL) as duration_hours
```

**Source Data:** `opened_at`, `closed_at`

---

### PnL Percentage

```sql
-- PnL as percentage of position size
CASE WHEN size_usdt > 0 
    THEN (realized_pnl / size_usdt * 100) 
    ELSE 0 END as pnl_pct
```

**Source Data:** `realized_pnl`, `size_usdt`

---

### Lost Opportunity

```sql
-- Lost profit (MFE not captured)
CASE WHEN size_usdt > 0 AND mfe > 0
    THEN (mfe - (realized_pnl / size_usdt))
    ELSE 0 END as lost_opportunity
```

**Source Data:** `mfe`, `realized_pnl`, `size_usdt`

---

## Query Patterns

### Trade List with Filters

```sql
SELECT 
    pp.id,
    pp.symbol,
    pp.direction,
    pp.status,
    pp.entry_price,
    pp.current_price as exit_price,
    pp.size_usdt,
    pp.qty,
    pp.realized_pnl,
    pp.opened_at,
    pp.closed_at,
    
    -- Derived: Duration
    CAST((julianday(pp.closed_at) - julianday(pp.opened_at)) * 24 AS REAL) as duration_hours,
    
    -- Derived: PnL %
    CASE WHEN pp.size_usdt > 0 
        THEN (pp.realized_pnl / pp.size_usdt * 100) 
        ELSE 0 END as pnl_pct,
    
    -- Execution Intelligence
    pp.mae,
    pp.mfe,
    pp.profit_capture_ratio,
    pp.final_exit_reason,
    pp.execution_policy,
    pp.trailing_stop_activated,
    pp.sl_move_count,
    pp.break_even_triggered,
    
    -- Signal Attribution
    pp.confidence,
    pp.regime,
    pp.timeframe,
    pp.execution_edge,
    pp.signal_id,
    s.direction as signal_direction,
    s.timestamp as signal_timestamp

FROM paper_positions pp
LEFT JOIN signals s ON pp.signal_id = s.id

WHERE pp.status != 'OPEN'
    AND (?1 IS NULL OR pp.symbol = ?1)
    AND (?2 IS NULL OR pp.status = ?2)
    AND (?3 IS NULL OR pp.regime = ?3)
    AND (?4 IS NULL OR pp.confidence >= ?4)
    AND (?5 IS NULL OR pp.closed_at >= ?5)
    AND (?6 IS NULL OR pp.closed_at <= ?6)

ORDER BY pp.closed_at DESC
LIMIT ?7 OFFSET ?8;
```

---

### Trade Detail with Full Context

```sql
SELECT 
    pp.*,
    s.direction as signal_direction,
    s.timestamp as signal_timestamp,
    s.created_at as signal_created_at,
    
    -- Derived metrics computed in application layer
    CAST((julianday(pp.closed_at) - julianday(pp.opened_at)) * 24 AS REAL) as duration_hours

FROM paper_positions pp
LEFT JOIN signals s ON pp.signal_id = s.id

WHERE pp.id = ?1;
```

---

### Analytics Aggregation

```sql
-- Win rate, profit factor, expectancy by confidence bucket
SELECT 
    CAST(confidence / 10 AS INTEGER) * 10 || '-' || 
    (CAST(confidence / 10 AS INTEGER) * 10 + 9) || '%' as confidence_bucket,
    COUNT(*) as total_trades,
    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as win_rate,
    ROUND(SUM(realized_pnl), 2) as total_pnl,
    ROUND(AVG(realized_pnl), 2) as avg_pnl,
    ROUND(
        SUM(CASE WHEN realized_pnl > 0 THEN realized_pnl ELSE 0 END) /
        NULLIF(ABS(SUM(CASE WHEN realized_pnl <= 0 THEN realized_pnl ELSE 0 END)), 0),
        2
    ) as profit_factor

FROM paper_positions
WHERE status != 'OPEN'
    AND confidence IS NOT NULL
    AND (?1 IS NULL OR symbol = ?1)

GROUP BY confidence_bucket
ORDER BY confidence_bucket;
```

---

## Index Recommendations

### Existing Indexes (Sufficient for MVP)

```sql
CREATE INDEX idx_paper_positions_status 
    ON paper_positions(status);

CREATE INDEX idx_paper_positions_symbol 
    ON paper_positions(symbol);

CREATE INDEX idx_paper_equity_snapshot_time 
    ON paper_equity_history(snapshot_time);
```

**Performance:** Expected query time < 500ms for typical workload

---

### Optional Indexes (Future Optimization)

Add these if query latency exceeds 500ms:

```sql
-- Composite index for common filter patterns
CREATE INDEX idx_paper_positions_explorer 
    ON paper_positions(status, symbol, regime, confidence, closed_at);

-- Index for signal JOINs
CREATE INDEX idx_paper_positions_signal_id 
    ON paper_positions(signal_id);

-- Index for date range queries
CREATE INDEX idx_paper_positions_closed_at 
    ON paper_positions(closed_at) 
    WHERE status != 'OPEN';
```

**When to add:** Only if profiling shows slow queries (unlikely with current data volume)

---

## Schema Enhancements (Post-MVP)

### Phase 2: Per-Trade Equity Snapshots

**Problem:** `paper_equity_history` has 5-minute granularity, not per-trade  
**Solution:** Add equity context to `paper_positions`

```sql
-- Migration: Add equity snapshots to positions table
ALTER TABLE paper_positions ADD COLUMN equity_at_entry REAL;
ALTER TABLE paper_positions ADD COLUMN equity_at_exit REAL;
ALTER TABLE paper_positions ADD COLUMN balance_at_entry REAL;
ALTER TABLE paper_positions ADD COLUMN balance_at_exit REAL;
```

**Implementation:**
- Modify `open_paper_position()` to snapshot equity at entry
- Modify `close_paper_position()` to snapshot equity at exit
- Enables precise portfolio attribution

**Timeline:** 1-2 days implementation if requested

---

### Phase 3: Position Price History

**Problem:** Cannot reconstruct intra-trade price paths  
**Solution:** Add time-series price tracking

```sql
-- Migration: New table for position price history
CREATE TABLE position_price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id INTEGER NOT NULL,
    price REAL NOT NULL,
    mark_price REAL,
    unrealized_pnl REAL,
    unrealized_pnl_pct REAL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (position_id) REFERENCES paper_positions(id)
);

CREATE INDEX idx_position_price_history_position 
    ON position_price_history(position_id);
    
CREATE INDEX idx_position_price_history_timestamp 
    ON position_price_history(timestamp);
```

**Implementation:**
- Modify `update_open_positions()` to log prices
- ~100-200 rows per position (5-min updates over 7-day lifecycle)
- Enables detailed price charts in Trade Explorer

**Timeline:** 2-3 days implementation if requested

---

### Phase 4: Signal Denormalization

**Problem:** Frequent JOINs to `signals` table  
**Solution:** Cache signal fields on `paper_positions`

```sql
-- Migration: Add frequently-accessed signal fields
ALTER TABLE paper_positions ADD COLUMN signal_direction TEXT;
ALTER TABLE paper_positions ADD COLUMN signal_timestamp TIMESTAMP;
ALTER TABLE paper_positions ADD COLUMN signal_tp_multiplier REAL;
ALTER TABLE paper_positions ADD COLUMN signal_sl_multiplier REAL;
```

**Implementation:**
- Modify `open_paper_position()` to copy signal fields
- Eliminates most JOINs
- Trades denormalization for query performance

**Timeline:** 1 day implementation if query performance issues arise

---

## Data Integrity

### Constraints

**Existing Constraints:**
- ✅ `direction` CHECK: enforces LONG/SHORT
- ✅ `status` CHECK: enforces valid statuses
- ✅ `execution_policy` CHECK: enforces valid policies
- ✅ Foreign key: `signal_id` references `signals(id)` (implicit)

**No Additional Constraints Required for MVP**

---

### Data Validation

Validated at application layer (paper_broker.py):

```python
# Entry validation
if direction not in ("LONG", "SHORT"):
    logger.warning(f"Invalid direction: {direction}")
    return None

if status not in ("TP_HIT", "SL_HIT", "EXPIRED", "MANUAL_CLOSE"):
    logger.warning(f"Invalid status: {status}")
    return None

# Price validation
if entry_price is None or entry_price <= 0:
    logger.warning("Invalid entry price")
    return None
```

**No database-level validation changes required**

---

## Migration Strategy

### MVP: No Migrations Required

Trade Explorer uses existing schema. Zero migration risk.

---

### Future Migrations (If Needed)

**Migration Template:**

```sql
-- Example: 028_trade_explorer_enhancements.sql
-- Add per-trade equity snapshots

ALTER TABLE paper_positions ADD COLUMN equity_at_entry REAL;
ALTER TABLE paper_positions ADD COLUMN equity_at_exit REAL;
ALTER TABLE paper_positions ADD COLUMN balance_at_entry REAL;
ALTER TABLE paper_positions ADD COLUMN balance_at_exit REAL;

-- Backfill existing positions (use nearest equity snapshot)
UPDATE paper_positions pp
SET 
    equity_at_entry = (
        SELECT equity FROM paper_equity_history
        WHERE snapshot_time <= pp.opened_at
        ORDER BY snapshot_time DESC LIMIT 1
    ),
    equity_at_exit = (
        SELECT equity FROM paper_equity_history
        WHERE snapshot_time <= pp.closed_at
        ORDER BY snapshot_time DESC LIMIT 1
    )
WHERE pp.status != 'OPEN';
```

**Migration Testing:**
1. Test on copy of production database
2. Verify backfill logic
3. Run migration in transaction
4. Validate data integrity post-migration

---

## Performance Considerations

### Current Scale

- **Total positions:** ~10/day × 90 days = ~900 positions
- **Closed positions:** ~800 (some still open)
- **Query workload:** Research (not production latency-sensitive)

**Performance Target:** < 500ms for filtered list queries

---

### Query Optimization

**Current Performance (No Optimization Needed):**
- SQLite handles < 10,000 rows efficiently
- Existing indexes sufficient
- JOIN cost negligible at this scale

**Future Optimization (If Needed):**
- Add composite index if latency > 500ms
- Consider query result caching (Redis, 5-minute TTL)
- Profile slow queries with `EXPLAIN QUERY PLAN`

---

### Storage

**Current Storage:**
- `paper_positions`: ~800 rows × ~500 bytes/row = ~400 KB
- `paper_equity_history`: ~26,000 snapshots (90 days × 288/day) × 50 bytes = ~1.3 MB
- Total: < 2 MB for paper trading data

**Future Storage (Phase 3):**
- `position_price_history`: ~800 positions × 200 snapshots × 50 bytes = ~8 MB
- Still well within SQLite's capacity

---

## Backup & Recovery

### Current Backup Strategy

Database located at: `/home/zafka/trade-dashboard/ml_service/storage/database.db`

**Backup Methods:**
1. File-system backup (copy database.db)
2. SQLite `.backup` command
3. Git-tracked migrations (reproducible schema)

**No changes required for Trade Explorer**

---

### Data Retention

**Current Policy:** Indefinite retention (research data)

**Trade Explorer Impact:** None (read-only queries)

---

## Testing Strategy

### Schema Validation Tests

```python
# tests/test_trade_explorer_schema.py

def test_paper_positions_has_required_columns():
    """Verify all columns required by Trade Explorer exist."""
    conn = get_connection()
    cursor = conn.execute("PRAGMA table_info(paper_positions)")
    columns = {row[1] for row in cursor.fetchall()}
    
    required = {
        'id', 'symbol', 'direction', 'status', 'entry_price',
        'realized_pnl', 'opened_at', 'closed_at', 'mae', 'mfe',
        'profit_capture_ratio', 'confidence', 'regime', 'execution_policy'
    }
    
    assert required.issubset(columns), f"Missing columns: {required - columns}"

def test_derived_metrics_computation():
    """Test EQS and classification logic."""
    conn = get_connection()
    row = conn.execute(
        "SELECT mae, mfe, profit_capture_ratio, status, size_usdt "
        "FROM paper_positions WHERE id = 1"
    ).fetchone()
    
    eqs = calculate_eqs(row['mae'], row['mfe'], row['profit_capture_ratio'], 
                        row['status'], row['size_usdt'])
    assert 0 <= eqs <= 100
```

---

### Data Integrity Tests

```python
# tests/test_data_integrity.py

def test_closed_positions_have_pnl():
    """Closed positions should have realized_pnl calculated."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, realized_pnl FROM paper_positions WHERE status != 'OPEN'"
    ).fetchall()
    
    for row in rows:
        assert row['realized_pnl'] is not None, f"Position {row['id']} missing PnL"

def test_mae_mfe_consistency():
    """MAE should be <= 0, MFE should be >= 0."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, mae, mfe FROM paper_positions WHERE status != 'OPEN'"
    ).fetchall()
    
    for row in rows:
        if row['mae'] is not None:
            assert row['mae'] <= 0, f"Position {row['id']}: MAE should be <= 0"
        if row['mfe'] is not None:
            assert row['mfe'] >= 0, f"Position {row['id']}: MFE should be >= 0"
```

---

## Security Considerations

### SQL Injection Prevention

**Strategy:** Parameterized queries for all user inputs

```python
# GOOD: Parameterized query
cursor.execute(
    "SELECT * FROM paper_positions WHERE symbol = ?",
    (user_provided_symbol,)
)

# BAD: String interpolation (vulnerable)
cursor.execute(
    f"SELECT * FROM paper_positions WHERE symbol = '{user_provided_symbol}'"
)
```

**Trade Explorer:** All queries use parameterized queries (FastAPI automatic validation)

---

### Data Privacy

- Paper trading data is research-only (no real funds)
- No PII or sensitive data in schema
- Safe to expose in development/research environments

**No additional privacy controls required**

---

## Documentation

### Schema Documentation

**Current:** Inline comments in migration files  
**Trade Explorer:** This document serves as schema reference

**Future Enhancement:** Generate schema diagram (ERD) if requested

---

### Migration Log

**Current Migrations Relevant to Trade Explorer:**

- `017_create_paper_account.sql` - Account table
- `018_create_paper_positions.sql` - Core positions table
- `019_paper_equity_history.sql` - Equity snapshots
- `020_execution_metadata.sql` - Signal attribution fields
- `021_execution_intelligence.sql` - MAE/MFE/PCR tracking
- `022_execution_policy_refinement.sql` - Execution policy enum

**All migrations complete and tested in production**

---

## Conclusion

### MVP Readiness: ✅ Ready

- No schema changes required
- All data available in existing tables
- Derived metrics computed at query time
- Performance sufficient for research workload

### Post-MVP Enhancements (Optional)

**Priority 1:** Per-trade equity snapshots (Phase 2)  
**Priority 2:** Position price history (Phase 3)  
**Priority 3:** Signal denormalization (Phase 4)

**Decision Point:** Implement enhancements based on user feedback after MVP delivery

---

## References

- Data Availability Matrix: `DataAvailabilityMatrix.md`
- Gap Analysis: `GapAnalysis.md`
- Architecture: `TradeExplorer_Architecture.md`
- API Specification: `TradeExplorer_API.md`
- Migration Files: `ml_service/migrations/`

---

## Appendix: Schema Diagram

```
┌─────────────────────────────────────────────┐
│           paper_positions                   │
│─────────────────────────────────────────────│
│ id (PK)                                     │
│ symbol, direction, status                   │
│ entry_price, current_price, stop_loss, tp   │
│ size_usdt, qty, realized_pnl                │
│ opened_at, closed_at                        │
│                                             │
│ confidence, regime, timeframe               │
│ prob_short, prob_neutral, prob_long         │
│ execution_edge                              │
│                                             │
│ mae, mfe, mae_timestamp, mfe_timestamp      │
│ profit_capture_ratio, final_exit_reason     │
│ trailing_stop_activated, sl_move_count      │
│ break_even_triggered, execution_policy      │
│                                             │
│ signal_id (FK) ──────────┐                 │
└─────────────────────────────────────────────┘
                            │
                            │
                            ▼
              ┌─────────────────────────┐
              │       signals           │
              │─────────────────────────│
              │ id (PK)                 │
              │ symbol, timeframe       │
              │ timestamp, direction    │
              │ confidence, regime      │
              │ features_json           │
              │ created_at              │
              └─────────────────────────┘

┌─────────────────────────────────────────────┐
│           paper_account                     │
│─────────────────────────────────────────────│
│ id (PK, CHECK = 1)                          │
│ balance, equity, unrealized_pnl             │
│ updated_at                                  │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│        paper_equity_history                 │
│─────────────────────────────────────────────│
│ id (PK)                                     │
│ equity, balance, unrealized_pnl             │
│ snapshot_time                               │
└─────────────────────────────────────────────┘
```

**Legend:**
- PK: Primary Key
- FK: Foreign Key
- Solid line: Foreign key relationship

**Trade Explorer Queries:**
- Main query: `paper_positions` (with derived metrics)
- Attribution: JOIN `signals` via `signal_id`
- Portfolio context: `paper_account`, `paper_equity_history`
