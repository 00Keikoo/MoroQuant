# Database Recovery Test Coverage

This document outlines the testing suite, validation policies, and coverage statistics for the MoroQuant Database Recovery Framework.

---

## 1. Test Suite Summary

The testing framework targets 100% of the recovery components. All tests run in-memory or using isolated temp SQLite instances to guarantee environmental purity.

* **Total Passing Tests**: **218**
* **Test Execution Time**: ~4.3 seconds
* **Code Coverage (Recovery Modules)**: >95%

---

## 2. Component Coverage Details

### 2.1 Recovery Models (`test_recovery_models.py` & `test_recovery_execution_models.py`)
* **Coverage Targets**: Enums, dataclasses, serialization logic (`to_dict`), and immutable constraints.
* **Assertions**: Asserts that `SchemaSnapshot`, `ColumnSchema`, `TableSchema`, and `RecoveryDecision` are frozen dataclasses and cannot be modified after instantiation. Verifies deterministic JSON round-trip stability.

### 2.2 Schema Inspector (`test_schema_inspector.py`)
* **Coverage Targets**: Reading table metadata, column definitions, nullability, indices, and defaults from SQLite system catalogues.
* **Assertions**: Verifies correct parser mapping on edge-case SQLite datatypes. Confirms structural differences are detected between two active connection states.

### 2.3 Decision Analyzer (`test_decision_analyzer.py`)
* **Coverage Targets**: Drift classification matrix, risk determination, and recommended action matching rules.
* **Assertions**: Validates all 8 Recovery Classifications. Asserts that risk levels map appropriately to recommendations (e.g. metadata gaps must map to `HALT` with `CRITICAL` risk).

### 2.4 Migration Runner (`test_migration_runner.py`)
* **Coverage Targets**: DDL statements parsing, transaction management, connection pooling, and record update inside the `schema_migrations` ledger.
* **Assertions**: Verifies that any database execution error causes a full rollback. Confirms lock acquisition retries work correctly and prevent database busy locks.

### 2.5 Recovery Executor (`test_recovery_executor.py`)
* **Coverage Targets**: Execution dispatcher loop, execution duration timing, and transactional error boundaries.
* **Assertions**: Asserts that a failure in step 2 of a multi-step recovery rolls back step 2 cleanly without affecting the completed step 1.

### 2.6 Recovery Reporter (`test_recovery_reporter.py`)
* **Coverage Targets**: Compilation of execution metrics, sorted key JSON serialization, directory path traversal checks.
* **Assertions**: Checks that audit filenames contain UTC dates. Asserts that the reporter throws a `ReporterError` if relative path traversal `..` is present in the output folder path.

### 2.7 Recovery Orchestrator (`test_recovery_orchestrator.py`)
* **Coverage Targets**: Glue coordination of components, context construction, token validation.
* **Assertions**: Verifies that the orchestrator throws `ApprovalRequiredError` when a `HIGH`/`CRITICAL` risk decision is applied without the correct `--approve-token` input.

### 2.8 Recovery CLI (`test_recovery_cli.py`)
* **Coverage Targets**: Click command options, input argument validators, and stdout outputs.
* **Assertions**: Asserts that `db inspect` exits with code `2` when drift is detected. Verifies output matches the JSON schema when `--format json` is requested.

---

## 3. Regression & Verification Suites

### 3.1 Replay Verification (`test_replay_determinism.py` & `test_snapshot_purity.py`)
Ensures that building a database from scratch using all historical migration scripts yields a schema identical to production:

$$\text{Fresh DB} \xrightarrow{001 \dots 032} \text{Target Schema} \equiv \text{Production Schema Snapshot}$$

Tests assert that the structural output comparison results in zero drift differences.

### 3.2 Determinism Verification
Ensures that running inspections or dry-runs repeatedly does not alter database states, modify migration folders, or produce non-deterministic output structures (keys in JSON reports are sorted alphabetically).

---

## 4. Pipeline Integration (CI/CD)

The recovery tests are integrated into the deployment pipeline:
* **Pre-commit Hooks**: Prevent commits containing drift or unverified migration scripts.
* **GitHub Actions**: Runs the replay verification script (`scripts/verify_replay.py`) on every Pull Request. Any PR that introduces schema differences or fails to build version sequence `001-HEAD` from scratch is blocked from merge.
* **VPS Validation**: Before target application deployment on staging/production VPS nodes, `agy db inspect --format json` is run automatically. If it returns exit code `2`, the script suspends the deployment and triggers alarms.
