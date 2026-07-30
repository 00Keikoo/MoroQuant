# Database Recovery CLI Guide

This document describes how to use the Database Recovery command-line utility.

All operations are grouped under the `db` command group of the MoroQuant CLI (`agy`).

---

## 1. CLI Commands & Options

### 1.1 `agy db inspect`
Inspects database state to identify structural drift and metadata gaps. This command is completely read-only and will never modify the database or write files.

**Usage:**
```bash
agy db inspect [OPTIONS]
```

**Options:**
* `--db-path PATH`: Override path to SQLite database (defaults to the path in `config.yaml` or `trading.db`).
* `--migrations-dir PATH`: Override path to migrations folder (defaults to `ml_service/migrations`).
* `--format [text|json]`: Toggle stdout output format (default: `text`).

**Exit Codes:**
* `0`: Database schema matches the target migrations. No drift detected.
* `1`: Operational error (invalid path, connection error, etc.).
* `2`: Drift detected. Schema differs from ledger or filesystem state.

---

### 1.2 `agy db recover`
Reconciles database drift by executing corrective actions or recording metadata states.

**Usage:**
```bash
agy db recover [OPTIONS]
```

**Options:**
* `--db-path PATH`: Override path to SQLite database.
* `--migrations-dir PATH`: Override path to migrations folder.
* `--dry-run`: Display recovery decisions without executing them.
* `--approve-token TOKEN`: CTO validation token required to apply `HIGH` or `CRITICAL` risk operations. Can also be set via the `MQ_CTO_APPROVAL_TOKEN` environment variable.
* `--interactive / --non-interactive`: Force confirmation prompts (default: `--interactive`). In non-interactive mode, the command fails on high/critical actions if the approval token is missing or incorrect.
* `--format [text|json]`: Toggle stdout output format (default: `text`).

**Exit Codes:**
* `0`: Success (either recovery completed successfully, or no recovery was needed).
* `1`: Operational error, syntax error during execution, abort due to lack of confirmation, or invalid approval token.

---

## 2. Command Examples & Outputs

### 2.1 Example: `agy db inspect` (Human Output)
Runs a diagnostic run showing a list of drift mismatches:

```
$ agy db inspect
================================================================================
MOROQUANT DATABASE INSPECTION REPORT
================================================================================
Target Database: trading.db
Status: DRIFT DETECTED

[DRIFT ID: 001]
--------------------------------------------------------------------------------
Table Name:      experiments
Difference Type: MISSING_TABLE
Column Name:     N/A
Classification:  METADATA_DRIFT
Risk Level:      CRITICAL
Recommendation:  HALT
Rationale:       Table 'experiments' exists in target migrations but is missing from the database.
--------------------------------------------------------------------------------

SUMMARY:
- Total Drift Mismatches: 1
- Risk Summary: 1 CRITICAL
- Recommended Action: HALT
================================================================================
```
*Note: This command exits with code `2`.*

---

### 2.2 Example: `agy db inspect --format json` (JSON Output)
Returns structured details suitable for pipeline execution and deployment gate checks:

```json
{
  "status": "DRIFT_DETECTED",
  "summary": {
    "total_drift_items": 1,
    "risk_counts": {
      "LOW": 0,
      "MEDIUM": 0,
      "HIGH": 0,
      "CRITICAL": 1
    }
  },
  "decisions": [
    {
      "difference": {
        "difference_type": "MISSING_TABLE",
        "target_migration": "030_create_experiments.sql",
        "table_name": "experiments",
        "column_name": null,
        "index_name": null,
        "details": {}
      },
      "classification": "METADATA_DRIFT",
      "risk": "CRITICAL",
      "recommended_action": "HALT",
      "rationale": "Table 'experiments' exists in target migrations but is missing from the database.",
      "details": {}
    }
  ]
}
```
*Note: This command exits with code `2`.*

---

### 2.3 Example: `agy db recover --dry-run`
Simulates a recovery operation and prints the proposed plan:

```
$ agy db recover --dry-run
================================================================================
[DRY-RUN] proposed recovery operations
================================================================================
  [001] Recommendation: FORCE_RECORD (Risk: LOW)
        Rationale: Migration 015_dedup_signals_unique_index.sql is not recorded in the ledger, but its unique index already exists physically.
  [002] Recommendation: FORWARD_MIGRATION (Risk: MEDIUM)
        Rationale: Missing column 'initial_balance' in table 'paper_account'.
================================================================================
```
*Note: Exits with code `0`.*

---

### 2.4 Example: `agy db recover` (Interactive Prompt)
Runs recovery interactively. Because there is a `HIGH` or `CRITICAL` risk action, a safety prompt is generated:

```
$ agy db recover
WARNING: This recovery includes structural changes and potential data loss risk.
To proceed, type exactly 'I UNDERSTAND': I UNDERSTAND
================================================================================
MOROQUANT DATABASE RECOVERY EXECUTION SUMMARY
================================================================================
Operator Context: zafka
Audit Report:     /home/zafka/trade-dashboard/storage/reports/recovery_audit/recovery_audit_20260730_131522.json

RESULTS:
- Decision 001: SUCCESS [FORCE_RECORD] -> Migration 015_dedup_signals_unique_index.sql is not recorded in the ledger, but its unique index already exists physically.
- Decision 002: SUCCESS [FORWARD_MIGRATION] -> Missing column 'initial_balance' in table 'paper_account'.

METRICS:
- Total Processed: 2
- Successful:      2
- Failed:          0
- Skipped:         0
- Duration:        34.50 ms
================================================================================
```

---

### 2.5 Example: `agy db recover --approve-token <token>` (Non-Interactive Deployment Pipeline)
Runs recovery automatically in a deployment script. Since `--non-interactive` is passed, the command uses the CTO approval token:

```bash
$ export MQ_CTO_APPROVAL_TOKEN="secret-token-key-1234"
$ agy db recover --non-interactive --approve-token "secret-token-key-1234"
```
```
================================================================================
MOROQUANT DATABASE RECOVERY EXECUTION SUMMARY
================================================================================
Operator Context: runner
Audit Report:     /home/zafka/trade-dashboard/storage/reports/recovery_audit/recovery_audit_20260730_132045.json

RESULTS:
- Decision 001: SUCCESS [MANUAL_PATCH] -> Table repair for execution_decisions requires out-of-band columns realignment.

METRICS:
- Total Processed: 1
- Successful:      1
- Failed:          0
- Skipped:         0
- Duration:        12.12 ms
================================================================================
```

---

### 2.6 Example: `agy db recover --format json`
Returns the execution output as formatted JSON:

```json
{
  "status": "SUCCESS",
  "audit_report": "/home/zafka/trade-dashboard/storage/reports/recovery_audit/recovery_audit_20260730_131522.json",
  "summary": {
    "total_decisions": 1,
    "successful_executions": 1,
    "failed_executions": 0,
    "skipped_executions": 0,
    "total_duration_ms": 15.42,
    "results": [
      {
        "decision": {
          "difference": {
            "difference_type": "MISSING_INDEX",
            "target_migration": "002_add_signal_prices.sql",
            "table_name": "signal_prices",
            "column_name": null,
            "index_name": "idx_signal_prices_timestamp",
            "details": {}
          },
          "classification": "SCHEMA_DRIFT",
          "risk": "LOW",
          "recommended_action": "FORWARD_MIGRATION",
          "rationale": "Missing index idx_signal_prices_timestamp on table signal_prices.",
          "details": {}
        },
        "status": "SUCCESS",
        "duration_ms": 15.42,
        "executed_sql": [
          "CREATE INDEX idx_signal_prices_timestamp ON signal_prices (timestamp);"
        ],
        "rolled_back": false,
        "timestamp": "2026-07-30T13:15:22.412Z",
        "error_message": null
      }
    ]
  }
}
```
