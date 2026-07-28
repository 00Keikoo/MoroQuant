# Migration History Analysis - Sprint 2.2B Root Cause

**Date**: 2026-07-28  
**Classification**: Replay Conflict (ADR-023 Section 2.3)  
**Risk Level**: MEDIUM  
**Affected Migrations**: 028, 029, 030-032 (blocked)

---

## Executive Summary

Migration 028 was modified after its initial introduction, creating a divergence between production schema state and fresh installation replay. This violates the **Immutable Migration History** principle (ADR-023 Section 1) and causes a Replay Conflict that blocks migrations 030-032.

---

## Timeline of Inconsistency

### Initial State (Commit 4845728)
**Date**: 2026-07-10 23:11:21 +0700  
**Commit**: `4845728` - "feat: add execution decisions audit system"  

Migration 028 was introduced with the following schema:

```sql
CREATE TABLE IF NOT EXISTS execution_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    direction TEXT,
    decision TEXT NOT NULL CHECK(decision IN ('ACCEPTED', 'REJECTED')),
    reason TEXT,
    signal_id INTEGER,
    position_id INTEGER,
    confidence INTEGER,
    regime TEXT,
    timeframe TEXT,
    prob_short REAL,
    prob_neutral REAL,
    prob_long REAL,
    execution_edge REAL,
    signal_price REAL,
    execution_price REAL,
    slippage_pct REAL,
    execution_latency_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- NO source, signal_timestamp, execution_policy, reason_detail
    ...
);
```

**Production Impact**: If migration 028 was executed on production at this point, the physical schema would NOT contain the four metadata columns.

---

### Modified State (Commit 6508fe4)
**Date**: 2026-07-10 23:23:11 +0700 (12 minutes later)  
**Commit**: `6508fe4` - "feat: enrich execution audit metadata"  

**VIOLATION**: Migration 028 was modified to include four additional columns:

```sql
-- Source and metadata
source TEXT NOT NULL DEFAULT 'PAPER' CHECK(source IN ('PAPER', 'LIVE', 'BACKTEST', 'RESEARCH')),
signal_timestamp INTEGER,
execution_policy TEXT,
reason_detail TEXT,
```

**SIMULTANEOUSLY**, Migration 029 was introduced to add these same columns via ALTER TABLE:

```sql
ALTER TABLE execution_decisions ADD COLUMN source TEXT NOT NULL DEFAULT 'PAPER' ...
ALTER TABLE execution_decisions ADD COLUMN signal_timestamp INTEGER;
ALTER TABLE execution_decisions ADD COLUMN execution_policy TEXT;
ALTER TABLE execution_decisions ADD COLUMN reason_detail TEXT;
```

---

## Why Replay Fails

### Scenario 1: Production Database (Likely State)
If migration 028 was executed on production BEFORE commit 6508fe4:

1. ✅ Migration 028 runs successfully (original version, no metadata columns)
2. ✅ Migration 029 runs successfully (adds 4 columns via ALTER TABLE)
3. ✅ Final schema matches expected state

**Result**: Production schema is correct, migrations 030-032 can proceed.

---

### Scenario 2: Fresh Installation or Replay
If migrations are replayed from scratch using current codebase:

1. ✅ Migration 028 runs successfully (modified version WITH metadata columns)
2. ❌ Migration 029 FAILS: `duplicate column name: source`
   - ALTER TABLE attempts to add columns that already exist
3. ❌ Migrations 030-032 are blocked due to failure
4. ❌ `schema_migrations` table is inconsistent (028 recorded, 029 missing)

**Result**: Replay validation fails, violates ADR-023 Replayability principle.

---

## Schema State Divergence

| Database State | Migration 028 State | Migration 029 State | Columns Present | Can Run 030-032? |
|:---|:---|:---|:---|:---|
| **Production** | Original (no metadata) | ALTER adds 4 columns | Via 029 ALTER | ✅ YES |
| **Fresh Install** | Modified (with metadata) | FAILS on duplicate | Via 028 CREATE | ❌ NO |
| **CI/CD Pipeline** | Modified (with metadata) | FAILS on duplicate | Via 028 CREATE | ❌ NO |

---

## ADR-023 Classification

**Category**: **2.3 Replay Conflict**

> A migration runner execution fails because a statement tries to add an element (e.g., column, table) that already exists.

**Detection Criteria**: ✅ Confirmed
- SQLite exception: "duplicate column name: source"
- Target definition matches existing schema structure
- Upstream migration (028) was modified post-deployment

**Allowed Actions**: `FORCE_RECORD`, `SAFE_SKIP`  
**Forbidden Actions**: Editing active transactions, ignoring failure without documentation

---

## Historical Migration Modification Evidence

```bash
$ git log --oneline ml_service/migrations/028_create_execution_decisions.sql
6508fe4 feat: enrich execution audit metadata    # MODIFIED 028
4845728 feat: add execution decisions audit system  # CREATED 028
```

Git diff excerpt from commit 6508fe4:

```diff
diff --git a/ml_service/migrations/028_create_execution_decisions.sql
@@ -31,6 +31,12 @@ CREATE TABLE IF NOT EXISTS execution_decisions (
     slippage_pct REAL,
     execution_latency_ms INTEGER,
 
+    -- Source and metadata
+    source TEXT NOT NULL DEFAULT 'PAPER' CHECK(...),
+    signal_timestamp INTEGER,
+    execution_policy TEXT,
+    reason_detail TEXT,
+
     -- Audit timestamp
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
```

**Conclusion**: Migration 028 is NOT immutable, violating core architectural principle.

---

## Impact Assessment

### Blocked Capabilities
- ❌ Migration 030: Create experiments table
- ❌ Migration 031: Remediate experiments architecture
- ❌ Migration 032: Add initial_balance to paper_account
- ❌ Fresh installation pipeline (CI/CD)
- ❌ Development environment setup from scratch
- ❌ ADR-023 Replay Validation compliance

### Operational Risk
- **Production**: Likely UNAFFECTED (if 028 ran before modification)
- **Development**: BLOCKED on fresh installs
- **CI/CD**: BLOCKED on integration tests
- **Future Deployments**: BLOCKED until reconciliation

---

## Conclusion

The root cause is a violation of the **Immutable Migration History** principle. Migration 028 was modified 12 minutes after its initial commit, creating a divergence where:

- Production schema evolved through TWO migrations (028 original → 029 ALTER)
- Fresh installations attempt to apply the same schema through ONE migration (028 modified)

This creates a Replay Conflict where migration 029 fails on fresh installs with duplicate column errors, blocking all subsequent migrations (030-032).

**Forward remediation is required** to reconcile the metadata ledger (`schema_migrations`) with the physical schema state without modifying historical migration files.
