# Sprint 2.4A Design Specification: Database Recovery Framework Finalization

**Status**: PROPOSED (Ready for Freeze Review)  
**Role**: Principal Software Architect  
**Engineering Contract ID**: MoroQuant-Sprint-2.4A-Contract-v1.0  
**Target Implementation Agent**: Claude Code  

---

## 1. Executive Summary & Objective

The objective of Sprint 2.4A is to finalize and integrate the Database Recovery & Migration Reconciliation Framework (ADR-023 v1.1) to make it fully production-ready.

This design document outlines the glue components, command-line interfaces (CLI), integration pipelines, and validation procedures required to tie together the existing recovery modules (`SchemaInspector`, `DecisionAnalyzer`, `RecoveryExecutor`, `MigrationRunner`, `RecoveryReporter`) without modifying their existing structural boundaries.

### Core Objectives
1. **Unify Components**: Establish a clear orchestration path that links inspection, decision analysis, user confirmation, transactional execution, and audit reporting.
2. **Implement CLI Interface**: Introduce command-line tools under the `agy` CLI namespace (`agy db inspect`, `agy db recover`) with strict confirmation prompts, safety checks, and logging capabilities.
3. **Establish CI/CD Validation Pipeline**: Create automated workflows to verify migration sequence health and detect database drift before production deployments.
4. **Implement Replay Parity Assertion**: Standardize verification that ensures a database built from scratch sequentially matches the production schema.

---

## 2. System Architecture & Integration Context

The recovery framework comprises five completed core modules. Sprint 2.4A establishes the operational controller that coordinates these modules:

```
[CLI / pipeline Entry]
        |
        v
[RecoveryController]
        |
        +---> [SchemaInspector] ----> Reads SQLite schema metadata ("Schema Truth")
        |
        +---> [DecisionAnalyzer] ---> Compares with Migration Ledger ("Metadata Truth")
        |
        +---> [RecoveryExecutor] ---> coordinates with [MigrationRunner] to modify state safely
        |
        +---> [RecoveryReporter] ---> Writes deterministic audit log file to disk
```

### Existing Components & Boundaries
- **`SchemaInspector`**: Queries `sqlite_master` and `PRAGMA` variables to construct an immutable physical `SchemaSnapshot`.
- **`DecisionAnalyzer`**: Compares `SchemaSnapshot` with `DecisionContext` containing the migrations list, calculating `SchemaDifference` objects, classifications (`RecoveryClassification`), risk levels (`RecoveryRisk`), and recommendations (`RecoveryRecommendation`).
- **`RecoveryExecutor`**: Receives pre-calculated decisions and executes transactions.
- **`MigrationRunner`**: Runs raw SQL scripts, manages table locks, and records database migrations.
- **`RecoveryReporter`**: Compiles `ExecutionSummary` and produces stable JSON output audits.

---

## 3. Remaining Responsibilities

To achieve production readiness, the following orchestration responsibilities must be implemented in the coordination layer (e.g., a `RecoveryController` or `RecoveryOrchestrator` inside `ml_service/migrations/recovery/orchestrator.py`):

1. **Security Token Verification**: Detect `HIGH` and `CRITICAL` risk recovery recommendations and abort execution unless a manual approval token (e.g. environment variable `MQ_CTO_APPROVAL_TOKEN`) is provided.
2. **Transaction Grouping**: Ensure that execution steps for multiple related drift items are grouped atomically when appropriate, or fail-fast when a single action fails.
3. **Execution State Checkpoint**: In the event of a crash during a multi-step recovery sequence, write a checkpoint so the database does not resume in an undefined state.
4. **Operator Attribution**: Extract execution runtime environments (OS User, Hostname, Session ID, and optional git-hash) and feed them to the reporter.

---

## 4. Missing Interfaces

The integration requires the definition of three key interfaces to bind the recovery components to the CLI and the deployment pipelines:

### 4.1 Orchestrator Interface
A new orchestrator class to encapsulate the end-to-end execution of a recovery operation.

```python
class RecoveryOrchestrator:
    """Orchestrates the sequence of inspection, decision analysis, and execution."""
    
    def __init__(self, db_path: str, migrations_dir: str) -> None:
        ...
        
    def run_diagnostics(self) -> Tuple[RecoveryDecision, ...]:
        """Runs inspector and analyzer in a read-only phase.
        
        Returns:
            Tuple of RecoveryDecision objects representing proposed actions.
        """
        ...
        
    def apply_recovery(
        self, 
        decisions: Tuple[RecoveryDecision, ...], 
        operator: str,
        approval_token: Optional[str] = None
    ) -> Tuple[ExecutionSummary, str]:
        """Applies the decisions, executing transactions and saving audit logs.
        
        Raises:
            ApprovalRequiredError: If HIGH/CRITICAL action lacks token.
            RecoveryHaltedError: If a HALT decision is found.
        """
        ...
```

### 4.2 Pipeline Check Hook
An automated command interface for CI/CD gates that returns clean JSON/exit codes:
- **Exit Code 0**: No drift detected, schema matches target state.
- **Exit Code 1**: Metadata drift, missing migration, or unclassified drift detected. Block deployment.
- **Exit Code 2**: Safe schema drift or replay conflict detected. Actionable recovery path available but requires validation.

---

## 5. CLI Integration Points

The command-line suite will be exposed through click command groups in `ml_service/cli/commands.py`.

### 5.1 CLI Commands Specification

#### `agy db inspect`
Inspects database state, showing differences and recommended recovery actions without making changes.
- **Arguments**: None (reads default path from configuration).
- **Options**:
  - `--db-path PATH`: Override SQLite database file.
  - `--format [text|json]`: Toggle stdout output format (default: `text`).
- **Behavior**:
  - Runs `SchemaInspector` to analyze the schema.
  - Returns formatted summary of schema differences.
  - If drift is found, outputs classification, risk level, and recommendation.

#### `agy db recover`
Main execution command for database recovery.
- **Arguments**: None.
- **Options**:
  - `--dry-run`: Output planned recovery actions without executing them (does not write to ledger).
  - `--approve-token TOKEN`: Pass the CTO manual approval token required for `HIGH` and `CRITICAL` actions.
  - `--interactive / --non-interactive`: Enable/disable interactive prompt asking the user to type "I UNDERSTAND" before execution.
- **Behavior**:
  - Executes dry-run diagnostic phase.
  - Displays risk summary and action checklist.
  - Demands confirmation if interactive.
  - Passes payload to `RecoveryExecutor`.
  - Saves audit trail via `RecoveryReporter` and outputs the path to the report.

### 5.2 Operator Safety Prompt Rules
- If the plan contains `HIGH` or `CRITICAL` risk items, the prompt must explicitly print the warning:
  `WARNING: This recovery includes structural changes and potential data loss risk.`
- Force manual entry verification: User must type exactly `I UNDERSTAND` to proceed.
- If in `--non-interactive` mode (such as inside a deploy script), the execution must fail immediately if `HIGH` or `CRITICAL` actions exist unless `--approve-token` matches the configured server-side environment token.

---

## 6. Validation Workflow

Validation hooks must run before any staging or production deployment. The workflow consists of:

```
[Deploy Triggered]
       |
       v
[Run: agy db inspect --format json]
       |
       +---> [No differences?] -------------> Proceed to migrations
       |
       +---> [Low/Medium Drift?] -----------> run recovery -> apply migrations
       |
       +---> [Critical Drift / HALT?] ------> BLOCK DEPLOYMENT & Alert Team
```

### CI/CD Deployment Safety Gate Checklist
- Ensure `inspect` returns non-zero code on any unapplied physical schemas that mismatch the recorded ledger.
- Fail validation if migration checksums mismatch the development branch repository history (detects illegal modification of migration files post-merge).
- Prevent deployment pipeline from running automatic migrations if `schema_migrations` contains gaps (Missing Migration classification).

---

## 7. Replay Verification Workflow

To guarantee continuous integration health, the pipeline must enforce **Mandatory Replay Validation**. A test script `scripts/verify_replay.py` will automate this step on pull requests.

### Verification Formula
$$\text{Fresh SQLite DB} \xrightarrow{\text{Run Migrations 001} \dots \text{HEAD}} \text{Target Schema} \equiv \text{Production Schema Reference Snapshot}$$

### Replay Parity Protocol
1. Create a temporary in-memory or file-based blank SQLite database.
2. Execute all SQL files in the migrations directory in ascending numerical order.
3. Use `SchemaInspector` to capture the `SchemaSnapshot` of the newly constructed target database.
4. Obtain the production reference schema snapshot (stored as a static reference file `docs/schema/production_schema_ref.json`).
5. Execute a structural comparison between the two snapshots using the recovery framework's difference logic.
6. Fail the build if any `SchemaDifference` is detected (e.g. missing columns, mismatched default values, or physical structure divergence).

---

## 8. Documentation & Runbooks

To support operational readiness, the following documents must be updated/created:

### 8.1 Database Troubleshooting Runbook (`docs/operations/database-recovery-runbook.md`)
- **Metadata Drift Recovery Guide**: Detailed recovery steps when `METADATA_DRIFT` is encountered (explaining how to determine if schema elements were dropped manually or if migrations were partially executed).
- **Manual Patch Guidelines**: Clear protocols on when it is safe to apply a `MANUAL_PATCH` recommendation.
- **CTO Token Management**: Instructions for rotating and securing the CTO approval environment token.

### 8.2 ADR Progression
- Update `docs/adr/ADR-023-Database-Recovery-Framework.md` status from `PROPOSED` to `FROZEN` once this sprint passes validation.

---

## 9. Testing Strategy

All integration components must meet strict testing guidelines before final merge.

### 9.1 Unit Testing
- Mock `sqlite_master` schemas to assert CLI command routing for all 8 Recovery Classifications.
- Test `RecoveryOrchestrator` safety validation, verifying that it raises `ApprovalRequiredError` when running `HIGH` risk decisions without approval tokens.

### 9.2 Integration Testing
- E2E tests simulating CLI recovery runs against target SQLite files containing mock drift types.
- Verify that recovery execution results in a database with zero subsequent differences when re-inspected.
- Check that output report JSONs pass JSON schema validations and contain deterministic, sorted keys.

### 9.3 Failure Injection
- Test behavior during mid-transaction failures (e.g., locking conflicts, disk full). Assert that the database rolls back cleanly and leaves no corrupted ledger state.

---

## 10. Definition of Done (DoD)

The sprint will be considered complete when the following checks are met:

- [ ] Orchestrator component is fully integrated and tested under `ml_service/migrations/recovery/`.
- [ ] CLI commands `inspect` and `recover` are registered in the `agy` CLI utility.
- [ ] CTO safety tokens are validated correctly, blocking unauthorized high/critical recoveries.
- [ ] Replay validation script is executed and passes on a blank SQLite instance.
- [ ] Runbooks and documentation updates are written.
- [ ] Test coverage for the integration code is greater than 90%.
- [ ] Code builds cleanly and tests pass.
- [ ] ADR-023 is updated to `FROZEN`.
