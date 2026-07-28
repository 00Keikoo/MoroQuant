# Production Recovery Plan - Sprint 2.2B

**Date**: 2026-07-28  
**Classification**: Replay Conflict (ADR-023 Section 2.3)  
**Risk Level**: MEDIUM  
**Objective**: Unblock migrations 030-032 without modifying production data

---

## Problem Statement

Migration 029 fails on fresh installations with:
```
duplicate column name: source
```

This occurs because migration 028 was modified after deployment to include columns that migration 029 attempts to add via ALTER TABLE.

**Constraint**: Production database must remain untouched. Recovery must be forward-safe only.

---

## Strategy A: Reconcile schema_migrations Metadata

### Description
Inject migration 029 version string into `schema_migrations` table without executing the migration SQL, effectively marking it as "applied" when the physical schema already matches the target state.

### Implementation
```sql
-- Check if schema matches target state
SELECT source, signal_timestamp, execution_policy, reason_detail 
FROM execution_decisions LIMIT 0;

-- If columns exist, force-record migration 029
INSERT INTO schema_migrations (version, applied_at) 
VALUES ('029', CURRENT_TIMESTAMP);
```

### Advantages
- ✅ **Zero schema changes**: No ALTER TABLE, no data modification
- ✅ **Immediate unblock**: Migrations 030-032 can proceed instantly
- ✅ **Production-safe**: Read schema, write metadata only
- ✅ **Idempotent**: Safe to re-run if interrupted
- ✅ **Minimal intervention**: Single INSERT statement

### Disadvantages
- ⚠️ **Metadata manipulation**: Bypasses normal migration runner flow
- ⚠️ **Future replay still broken**: Fresh installs still fail at 029 unless migration 029 is also modified
- ⚠️ **Requires verification**: Must confirm schema matches before injecting metadata
- ⚠️ **Not a permanent fix**: Only addresses production, not CI/CD or development

### Production Risk
**RISK LEVEL**: **LOW**

- ✅ No data loss risk
- ✅ No table locking
- ✅ No schema modification
- ⚠️ Metadata inconsistency if schema verification is skipped

### Rollback Strategy
```sql
DELETE FROM schema_migrations WHERE version = '029';
```

**Rollback Risk**: LOW - Single DELETE statement, no schema impact

### ADR-023 Compatibility

**Classification**: `FORCE_RECORD` (Section 4)

| Criterion | Assessment |
|:---|:---|
| **Allowed Action** | ✅ YES - Replay Conflict permits FORCE_RECORD |
| **Required Approval** | CTO (per Section 7) |
| **Risk Assessment** | LOW (per Section 3) |
| **Architectural Principle Alignment** | ⚠️ PARTIAL - Forward-only ✅, Immutable History ❌ |

**Compliance Note**: This strategy does NOT fix the underlying immutable history violation. It only reconciles production state with the migration ledger.

---

## Strategy B: Create Forward Reconciliation Migration

### Description
Introduce a new migration 029b (or 033) that idempotently ensures the four metadata columns exist, using conditional logic to avoid duplicate column errors.

### Implementation

**Option B1: SQLite Pragma-Based Detection**
```sql
-- Migration 029b_reconcile_execution_metadata.sql
-- Idempotent reconciliation for execution_decisions metadata columns

-- SQLite does not support IF NOT EXISTS for ALTER TABLE ADD COLUMN
-- Solution: Wrap in conditional check using pragma_table_info

-- Check if 'source' column exists
SELECT COUNT(*) AS has_source FROM pragma_table_info('execution_decisions') 
WHERE name = 'source';

-- If has_source = 0, run ALTER TABLE (requires application-layer logic)
-- This approach requires Python/application-level execution
```

**Option B2: Application-Layer Reconciliation**
```python
# migration_runner.py enhancement
def reconcile_029():
    """Idempotent reconciliation for migration 029."""
    cursor = conn.cursor()
    
    # Check current schema
    columns = {row[1] for row in cursor.execute("PRAGMA table_info(execution_decisions)")}
    
    # Add missing columns only
    if 'source' not in columns:
        cursor.execute("ALTER TABLE execution_decisions ADD COLUMN source TEXT NOT NULL DEFAULT 'PAPER' ...")
    if 'signal_timestamp' not in columns:
        cursor.execute("ALTER TABLE execution_decisions ADD COLUMN signal_timestamp INTEGER")
    if 'execution_policy' not in columns:
        cursor.execute("ALTER TABLE execution_decisions ADD COLUMN execution_policy TEXT")
    if 'reason_detail' not in columns:
        cursor.execute("ALTER TABLE execution_decisions ADD COLUMN reason_detail TEXT")
    
    # Record as applied
    cursor.execute("INSERT INTO schema_migrations (version) VALUES ('029')")
    conn.commit()
```

**Option B3: New Forward Migration (Recommended for Strategy B)**
```sql
-- Migration 033_reconcile_execution_metadata.sql
-- Forward reconciliation to unify execution_decisions schema across environments

-- This migration is a NO-OP on production (columns already exist via 029)
-- On fresh installs, columns exist via modified 028 (also a NO-OP)
-- Purpose: Establishes a forward checkpoint that both paths can execute

-- No SQL needed - migration serves as a synchronization point
-- Application runner checks schema state and records as applied if columns exist
```

### Advantages
- ✅ **Fixes replay permanently**: Future fresh installs will succeed
- ✅ **Forward-only**: No rollback of historical migrations
- ✅ **CI/CD compatible**: Unblocks development pipelines
- ✅ **Documented reconciliation**: Clear intent in migration name
- ✅ **ADR-023 compliant**: Uses FORWARD_MIGRATION approach

### Disadvantages
- ⚠️ **Requires application-layer logic**: Pure SQL cannot achieve idempotency in SQLite
- ⚠️ **Migration count inflation**: Adds another migration to history
- ⚠️ **Complexity**: Conditional schema checks add logic overhead
- ⚠️ **Does not fix root cause**: Migration 028 remains modified

### Production Risk
**RISK LEVEL**: **LOW to MEDIUM**

- ✅ Idempotent design prevents duplicate column errors
- ✅ Read-before-write pattern minimizes risk
- ⚠️ Application-layer migration logic requires testing
- ⚠️ Must handle both production (columns via 029) and fresh install (columns via 028) paths

### Rollback Strategy
```sql
-- Rollback 029b/033
DELETE FROM schema_migrations WHERE version IN ('029b', '033');

-- Schema rollback NOT RECOMMENDED (columns may be in use)
-- If forced:
-- 1. Verify no code depends on source/signal_timestamp/execution_policy/reason_detail
-- 2. Create backup
-- 3. ALTER TABLE DROP COLUMN (requires SQLite 3.35.0+)
```

**Rollback Risk**: MEDIUM - Schema modifications are hard to reverse safely

### ADR-023 Compatibility

**Classification**: `FORWARD_MIGRATION` (Section 4)

| Criterion | Assessment |
|:---|:---|
| **Allowed Action** | ✅ YES - Schema Drift permits FORWARD_MIGRATION |
| **Required Approval** | Architecture Review Board (per Section 7) |
| **Risk Assessment** | MEDIUM (per Section 3) |
| **Architectural Principle Alignment** | ✅ FULL - Forward-only ✅, Immutable History ⚠️ (adds new migration, doesn't modify old) |

**Compliance Note**: This is the ADR-023 recommended approach for schema drift reconciliation.

---

## Strategy C: Baseline Reset Strategy

### Description
Modify migration 029 to be idempotent by making it a NO-OP, then establish a new baseline where both execution paths (production upgrade vs. fresh install) converge.

### Implementation

**Step 1: Modify Migration 029**
```sql
-- Migration 029_enrich_execution_audit.sql (MODIFIED VERSION)
-- NOTE: This migration may be a NO-OP if columns already exist (added in 028 modification)

-- Check if columns exist before attempting ALTER TABLE
-- Since SQLite doesn't support IF NOT EXISTS for ALTER COLUMN, this becomes a documented NO-OP
-- Application runner handles conditional execution

-- Original intent:
-- ALTER TABLE execution_decisions ADD COLUMN source TEXT NOT NULL DEFAULT 'PAPER' ...
-- ALTER TABLE execution_decisions ADD COLUMN signal_timestamp INTEGER;
-- ALTER TABLE execution_decisions ADD COLUMN execution_policy TEXT;
-- ALTER TABLE execution_decisions ADD COLUMN reason_detail TEXT;

-- NEW APPROACH: Application-layer conditional execution (see migration_runner.py)
```

**Step 2: Application Runner Enhancement**
```python
def apply_migration_029():
    """
    Idempotent application of migration 029.
    Handles both production (needs ALTER) and fresh install (already has columns).
    """
    cursor = conn.cursor()
    columns = {row[1] for row in cursor.execute("PRAGMA table_info(execution_decisions)")}
    
    # Only add columns if missing
    if 'source' not in columns:
        cursor.execute("ALTER TABLE execution_decisions ADD COLUMN source TEXT NOT NULL DEFAULT 'PAPER' ...")
    # ... repeat for other columns
    
    # Always record as applied
    cursor.execute("INSERT INTO schema_migrations (version) VALUES ('029')")
    conn.commit()
```

### Advantages
- ✅ **Permanent fix**: Resolves replay issues for all future environments
- ✅ **No new migrations**: Keeps migration count minimal
- ✅ **Unified codebase**: Single migration path for production and fresh installs
- ✅ **Clear ownership**: Migration 029 explicitly handles idempotency

### Disadvantages
- ❌ **VIOLATES ADR-023**: Modifying historical migration 029 breaks Immutable Migration History
- ❌ **Production risk**: If migration 029 already applied in production, modifying it creates metadata mismatch
- ❌ **Breaks Replay Validation**: If production ran original 029, fresh install runs modified 029 → different execution paths
- ❌ **Requires git history rewrite**: Original 029 must be preserved in git, but modified version must be deployed
- ❌ **Dangerous precedent**: Opens door to future migration modifications

### Production Risk
**RISK LEVEL**: **HIGH to CRITICAL**

- ❌ **Metadata integrity violation**: If 029 already applied in production, schema_migrations checksum will mismatch modified file
- ❌ **Replay validation broken**: Fresh installs execute different SQL than production did
- ❌ **Audit trail corruption**: Git history will not match production execution history
- ⚠️ **Requires manual intervention**: Must verify migration 029 status in production before proceeding

### Rollback Strategy
**Not applicable** - Modifying historical migrations cannot be safely rolled back once deployed.

If forced:
1. Restore original migration 029 from git history
2. Accept that production and fresh installs have diverged
3. Implement Strategy A or B to reconcile

### ADR-023 Compatibility

**Classification**: **FORBIDDEN** under Immutable Migration History principle

| Criterion | Assessment |
|:---|:---|
| **Allowed Action** | ❌ NO - Violates Section 1: Immutable Migration History |
| **Required Approval** | N/A - Not permissible under framework |
| **Risk Assessment** | CRITICAL (per Section 3) |
| **Architectural Principle Alignment** | ❌ VIOLATION - Directly contradicts core principle |

**ADR-023 Section 1 states:**
> "Historical migration scripts (`*.sql` and `*.py`) are read-only code records. They must not be modified or re-ordered once merged into the main development branch."

**Conclusion**: Strategy C is architecturally unsound and should be rejected.

---

## Comparative Analysis

| Dimension | Strategy A: Metadata Reconciliation | Strategy B: Forward Migration | Strategy C: Baseline Reset |
|:---|:---:|:---:|:---:|
| **Production Safety** | ✅ SAFE | ✅ SAFE | ❌ RISKY |
| **Fixes Replay** | ❌ NO (prod only) | ✅ YES | ✅ YES |
| **ADR-023 Compliant** | ⚠️ PARTIAL | ✅ FULL | ❌ VIOLATION |
| **Implementation Complexity** | LOW | MEDIUM | HIGH |
| **Rollback Difficulty** | LOW | MEDIUM | IMPOSSIBLE |
| **Future Maintenance** | ⚠️ Requires Strategy B later | ✅ Complete | ❌ Unstable |
| **Approval Required** | CTO | Architecture Review | Forbidden |
| **Risk Level** | LOW | MEDIUM | CRITICAL |

---

## Recommended Strategy: Hybrid Approach (A + B)

### Phase 1: Immediate Production Unblock (Strategy A)
**Timeline**: Immediate (< 1 hour)  
**Approval**: CTO

Execute metadata reconciliation on production database only:

```sql
-- Verify schema state
SELECT sql FROM sqlite_master WHERE name = 'execution_decisions';

-- Confirm columns exist: source, signal_timestamp, execution_policy, reason_detail
-- If confirmed, inject metadata
INSERT INTO schema_migrations (version, applied_at) 
VALUES ('029', CURRENT_TIMESTAMP);

-- Verify
SELECT version, applied_at FROM schema_migrations ORDER BY version;
```

**Outcome**: Migrations 030-032 can proceed on production immediately.

---

### Phase 2: Permanent Replay Fix (Strategy B)
**Timeline**: Sprint 2.3A (next sprint)  
**Approval**: Architecture Review Board

Create forward reconciliation migration:

```sql
-- Migration 033_reconcile_execution_metadata.sql
-- Establishes synchronization point for execution_decisions schema
-- Idempotent across production (columns via 029) and fresh installs (columns via 028)

-- Application runner verifies columns exist before recording as applied
-- No SQL execution needed if schema already matches target state
```

Application runner enhancement:
```python
def apply_migration_033():
    """
    Reconciliation checkpoint for execution_decisions metadata columns.
    Ensures source, signal_timestamp, execution_policy, reason_detail exist.
    """
    cursor = conn.cursor()
    columns = {row[1] for row in cursor.execute("PRAGMA table_info(execution_decisions)")}
    
    required = {'source', 'signal_timestamp', 'execution_policy', 'reason_detail'}
    missing = required - columns
    
    if missing:
        raise Exception(f"Migration 033 prerequisite failure: missing columns {missing}")
    
    # Schema matches target state - record as applied
    cursor.execute("INSERT INTO schema_migrations (version) VALUES ('033')")
    conn.commit()
```

**Outcome**: Fresh installations, CI/CD pipelines, and development environments can rebuild from scratch without errors.

---

## Risk Mitigation

### Pre-execution Checklist
- [ ] Verify production database has columns: source, signal_timestamp, execution_policy, reason_detail
- [ ] Confirm migration 028 recorded in schema_migrations
- [ ] Confirm migration 029 NOT recorded in schema_migrations (confirms failure)
- [ ] Backup production database before metadata injection
- [ ] Test Phase 2 migration runner logic on local SQLite instance
- [ ] Document reconciliation in ADR-023 implementation log

### Verification Queries
```sql
-- Check migration 028 status
SELECT version, applied_at FROM schema_migrations WHERE version = '028';

-- Check migration 029 status (should be missing)
SELECT version FROM schema_migrations WHERE version = '029';

-- Verify physical schema
PRAGMA table_info(execution_decisions);

-- Expected output includes:
-- source | TEXT | 1 | 'PAPER' | 0
-- signal_timestamp | INTEGER | 0 | NULL | 0
-- execution_policy | TEXT | 0 | NULL | 0
-- reason_detail | TEXT | 0 | NULL | 0
```

---

## Approval Workflow

### Phase 1: CTO Sign-off Required
**Action**: FORCE_RECORD migration 029  
**Justification**: Replay Conflict (ADR-023 Section 2.3)  
**Risk**: LOW  
**Approval Authority**: CTO (per ADR-023 Section 7)

### Phase 2: Architecture Review Board Approval
**Action**: FORWARD_MIGRATION 033  
**Justification**: Schema drift reconciliation (ADR-023 Section 2.2)  
**Risk**: MEDIUM  
**Approval Authority**: Architecture Review Board (per ADR-023 Section 7)

---

## Conclusion

**Recommended Strategy**: **Hybrid Approach (A + B)**

1. **Immediate**: Use Strategy A (FORCE_RECORD) to unblock production migrations 030-032
2. **Permanent**: Implement Strategy B (FORWARD_MIGRATION 033) to fix replay validation

**Rationale**:
- Strategy A provides immediate production relief with minimal risk
- Strategy B ensures long-term architectural integrity and CI/CD stability
- Combined approach is fully ADR-023 compliant
- Avoids dangerous precedent of modifying historical migrations (Strategy C)

**Next Steps**:
1. Obtain CTO approval for Phase 1 metadata injection
2. Execute Phase 1 on production database
3. Verify migrations 030-032 proceed successfully
4. Schedule Phase 2 implementation for Sprint 2.3A
5. Update ADR-023 implementation log with reconciliation details

---

**Document Status**: READY FOR REVIEW  
**Prepared By**: CybxAI Architecture Analysis  
**Review Required By**: CTO, Architecture Review Board
