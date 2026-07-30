# Database Recovery Operations Runbook

This document is the operational guide for database schema maintenance, incident response, and drift recovery.

---

## 1. Diagnostics & Verification Workflow

Before executing any DDL modification or recovery plan on a database instance, run the inspect pipeline to detect issues:

```bash
agy db inspect
```

If drift is detected, check the **Drift ID** and the **Risk Level**:
* **LOW** / **MEDIUM**: Can be recovered using standard dry-run verification and apply commands.
* **HIGH** / **CRITICAL**: Requires CTO approval token validation.
* **HALT**: Stop all deployments immediately.

---

## 2. Standard Incident Scenarios

### 2.1 Metadata Drift
* **Incident Description**: A migration is registered in `schema_migrations` but physical components (tables or columns) are missing.
* **Severity**: CRITICAL
* **Actionable Procedure**:
  1. Determine if the table or columns were dropped accidentally by an administrator.
  2. If the physical tables contain no production data, run:
     ```bash
     agy db recover --approve-token $MQ_CTO_APPROVAL_TOKEN
     ```
  3. If data was lost, restore from the latest nightly database backup in `storage/backups/` before running any recovery commands.

### 2.2 Schema Drift
* **Incident Description**: Schema type, nullability, constraint, or default values differ from target migration files.
* **Severity**: MEDIUM / HIGH
* **Actionable Procedure**:
  1. Generate a forward migration script containing the DDL updates (`ALTER TABLE`).
  2. Add the migration script under `ml_service/migrations` in development.
  3. Deploy the application, allowing the recovery manager to apply the changes as a `FORWARD_MIGRATION`.

### 2.3 Replay Conflict
* **Incident Description**: A migration fails because a statement attempts to add an element (e.g. column, index) that is already present in the database.
* **Severity**: LOW
* **Actionable Procedure**:
  1. Run `agy db inspect` to verify that the physical column/index matches the definition in the migration file exactly.
  2. Run the recovery executor to record the version in the ledger without re-running the SQL statement:
     ```bash
     agy db recover
     ```
     This triggers the `FORCE_RECORD` recommendation to bypass the error.

### 2.4 Manual Database Modification
* **Incident Description**: Ad-hoc tables or columns are added directly to the database outside the migration system.
* **Severity**: MEDIUM
* **Actionable Procedure**:
  1. If the modification is temporary, drop the extra elements using a DBA console.
  2. If the change needs to be preserved, create a standard migration file in the codebase that reflects the current database state, then run `agy db recover` to register it using `FORCE_RECORD`.

### 2.5 Missing Migration (Hole in Sequence)
* **Incident Description**: A migration version is missing in the ledger, but subsequent migrations are already applied.
* **Severity**: CRITICAL
* **Actionable Procedure**:
  1. The deployment pipeline will output `HALT` and block updates.
  2. Review the Git history to identify if a migration file was merged out-of-order.
  3. Re-inject the missing migration version into the physical table manually via SQLite terminal under direct supervision of the CTO, or rebuild the database state if on staging.

### 2.6 Checksum Mismatch
* **Incident Description**: A migration file in the codebase has been modified post-merge, changing its hash compared to the recorded history.
* **Severity**: HIGH
* **Actionable Procedure**:
  1. Revert the migration script contents in the codebase to match the repository main branch.
  2. If the script was modified to fix a production bug, write a new forward-only migration file instead of modifying the existing one.

### 2.7 Database Corruption
* **Incident Description**: SQLite database file is corrupted or unreadable.
* **Severity**: CRITICAL
* **Actionable Procedure**:
  1. Terminate all application processes to release database locks.
  2. Copy the corrupted database file to a safe location.
  3. Attempt SQLite recovery:
     ```bash
     sqlite3 trading.db ".recover" > recovery_script.sql
     sqlite3 trading_recovered.db < recovery_script.sql
     ```
  4. If recovery fails, restore the database from the most recent backup file.

---

## 3. Rollback Policy

> [!IMPORTANT]
> MoroQuant enforces a **Forward-only Migrations** policy (ADR-023). Downward migrations are forbidden.

To roll back a faulty schema structure:
1. Do not edit or delete old migration files.
2. Create a new migration file with an incremental version prefix (e.g., `033_revert_faulty_table.sql`).
3. Write DDL statements in the new migration that revert the changes (e.g. `DROP TABLE`, `ALTER TABLE ... DROP COLUMN`).
4. Commit, push, and run standard migrations to apply the rollback forwards.

---

## 4. Incident Response & Token Management

### 4.1 Token Rotation
The validation token is rotated every quarter or immediately following team departures.
1. Generate a new high-entropy string:
   ```bash
   openssl rand -hex 24
   ```
2. Update the environment variable `MQ_CTO_APPROVAL_TOKEN` on target servers.
3. Update the value inside the secure credential store.

### 4.2 Recovery Verification
After executing any recovery sequence, verify the status of the database:
1. Run `agy db inspect --format json` and check that the response status is `"CLEAN"`.
2. Inspect the latest JSON log in `storage/reports/recovery_audit/` to verify that all executed decisions have the status `"SUCCESS"`.
