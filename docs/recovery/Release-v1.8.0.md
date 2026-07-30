# Release Notes: MoroQuant Database Recovery Framework (v1.8.0)

This document contains the release details for v1.8.0, introducing the Database Recovery & Migration Reconciliation Framework.

---

## 1. Overview

MoroQuant v1.8.0 delivers the production-ready implementation of **ADR-023 v1.1 (Database Recovery & Migration Reconciliation Framework)**. This release secures database operations, prevents schema drift in production deployments, enforces deterministic migration sequences, and introduces automated diagnostic tools for database administrators.

---

## 2. New Features

* **Schema Inspector**: Out-of-band physical database analysis that reads tables, columns, constraints, and indices directly from SQLite master catalogues.
* **Decision Engine**: Automated analysis that maps physical drift to one of 8 distinct classifications (Metadata Drift, Schema Drift, Replay Conflict, Superseded Migration, Missing Migration, Destructive Migration, Manual Database Modification, and Unknown State).
* **CLI Command Suite**: Introduces the `db` command group to the MoroQuant CLI manager:
  * `agy db inspect`: Diagnostic tool to identify schema drift and metadata holes without writing to the database.
  * `agy db recover`: Repairs schema drift or reconciles migration ledger status using transaction-safe workflows.
* **CTO Safety Gate**: Restricts high-risk structural repairs or data deletion behind environment-defined approval tokens (`MQ_CTO_APPROVAL_TOKEN`), preventing accidental execution by automated deployment scripts.
* **Atomic Step Execution**: Multi-step recovery plans are evaluated step-by-step; failed operations roll back instantly, leaving the database ledger in a consistent state.

---

## 3. System Architecture

The recovery framework comprises:
1. **Coordination Layer**: `RecoveryOrchestrator` binds inspection, analysis, execution, and reporting.
2. **Analysis Layer**: Pure logic compiler (`DecisionAnalyzer`) that categorizes anomalies.
3. **Engine Layer**: `SchemaInspector`, `RecoveryExecutor`, and `MigrationRunner` interact directly with SQLite storage.
4. **Audit Layer**: `RecoveryReporter` persists deterministic, sorted-key JSON summaries to `storage/reports/recovery_audit/` for post-recovery analysis.

---

## 4. Testing & Validation

The framework release is validated by an extensive test suite:
* **Unit & Integration Tests**: 218 test cases checking schema parsing, transaction rollbacks, CLI inputs, and token authorization.
* **Replay Parity Assertion**: Automated tests verify that applying migration files `001` through `032` on an empty SQLite database matches the physical production reference schema.
* **CI/CD Gates**: GitHub Actions pipeline blocks PR merges if a schema mismatch is detected during replay verification.

---

## 5. Breaking Changes

* **Immutable History**: Historical migration scripts (`001` through `032`) are now read-only. Editing existing scripts post-merge is strictly forbidden and triggers pipeline failure due to checksum mismatch.
* **Strict Deployment Gates**: The deployment pipeline now runs `agy db inspect` before applying migrations. Deployments will fail and block automatically if a metadata hole (`MISSING_MIGRATION`) or unclassified drift is detected.

---

## 6. Migration Notes

To configure target servers for v1.8.0:
1. **Generate CTO Approval Token**:
   Generate a secure, random token and set it in the environment variables:
   ```bash
   export MQ_CTO_APPROVAL_TOKEN="your-secure-token-here"
   ```
2. **Deploy Codebase**:
   Pull release v1.8.0 and install package dependencies.
3. **Verify Database Health**:
   Run the inspect command to check for database drift:
   ```bash
   agy db inspect
   ```
4. **Reconcile Existing Drift**:
   If the database has existing schema drift, run the recovery command to align the schema:
   ```bash
   agy db recover --approve-token $MQ_CTO_APPROVAL_TOKEN
   ```

---

## 7. Known Limitations

* **SQLite Specific Dialect**: The physical inspector and DDL parser are optimized for the SQLite engine. While core structures are database-independent, custom constraint parsing relies on SQLite-specific system tables.
* **Lock Retry Bounds**: Under extreme write contention, the recovery lock retry mechanism might time out if write transactions exceed 5000 milliseconds.

---

## 8. Future Roadmap

* **PostgreSQL Engine Integration**: Extend `SchemaInspector` and `MigrationRunner` to support PostgreSQL dialects for scalability.
* **Self-Healing Nodes**: Optional automated repair for low-risk schema drift (e.g. creating missing indices) during container spin-up.
* **Audit Dashboard**: Web visualizer showing migration history and past recovery events.
