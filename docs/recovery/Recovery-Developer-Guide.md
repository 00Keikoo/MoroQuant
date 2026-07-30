# Database Recovery Developer Guide

This document is a technical guide for developers who need to extend, modify, or customize the MoroQuant Database Recovery and Reconciliation Framework.

---

## 1. Extension Checkpoints

To add new features or handle custom database drift states, follow these steps across the framework layers:

### 1.1 Step 1: Define the Domain Models (`models.py`)
All core recovery classes reside in `ml_service/migrations/recovery/models.py`. Update these enums and dataclasses first:

* **Adding `DifferenceType`**: Add a new key to the `DifferenceType` enum describing the raw schema anomaly (e.g., `FOREIGN_KEY_MISMATCH = "FOREIGN_KEY_MISMATCH"`).
* **Adding `RecoveryClassification`**: Update the `RecoveryClassification` enum if a new type of drift is identified (e.g., `PARTIAL_APPLIED_MIGRATION = "PARTIAL_APPLIED_MIGRATION"`).
* **Adding `RecoveryRisk`**: If you need a more granular safety level, add it to `RecoveryRisk`.
* **Adding `RecoveryRecommendation`**: Add recommendations to `RecoveryRecommendation` if the framework needs a new mitigation action class.

### 1.2 Step 2: Implement Detection and Analysis
* **Detecting Structural Differences**: Update `SchemaInspector` in `ml_service/migrations/recovery/schema_inspector.py` to inspect the database (e.g. read foreign keys using SQLite `PRAGMA foreign_key_list(table)`) and append a `SchemaDifference` object with your new `DifferenceType`.
* **Determining Decisions**: Update the `DecisionAnalyzer.analyze` method in `ml_service/migrations/recovery/decision/analyzer.py` to maps your new `SchemaDifference` to the corresponding `RecoveryClassification`, `RecoveryRisk`, and `RecoveryRecommendation`.

### 1.3 Step 3: Implement Execution Logic
* **Adding `MigrationRunner` Actions**: Update `MigrationRunner` in `ml_service/migrations/recovery/migration_runner.py` to support applying the SQL commands or recording the metadata ledger changes required for your new recommendation.
* **Adding `RecoveryExecutor` Behavior**: Update the command dispatcher in `RecoveryExecutor.execute` (located in `ml_service/migrations/recovery/executor.py`) to execute your new recommendation type securely within transaction blocks.

### 1.4 Step 4: Update Coordination & Auditing
* **Orchestrator Behavior**: If the new recommendation requires customized verification, token validations, or state checks, add it to `RecoveryOrchestrator` in `ml_service/migrations/recovery/orchestrator.py`.
* **Reporter Output**: The `RecoveryReporter` in `ml_service/migrations/recovery/reporter.py` serializes all models automatically. However, if your new difference contains custom metrics or telemetry dictionary structures, ensure they are serializable and register them in the `.to_dict()` methods of the classes in `models.py`.
* **CLI Integration**: If your custom behavior requires new CLI options (e.g., forcing a specific repair type), add options to `db_inspect` or `db_recover` in `ml_service/cli/commands.py`.

---

## 2. Step-by-Step Code Examples

### 2.1 Extending `models.py`
To add a new constraint type discrepancy:

```python
class DifferenceType(str, Enum):
    # ...
    FOREIGN_KEY_MISMATCH = "FOREIGN_KEY_MISMATCH"
```

### 2.2 Extending `analyzer.py`
Map the difference type to a low-risk bypass or forward-only patch:

```python
if diff.difference_type == DifferenceType.FOREIGN_KEY_MISMATCH:
    return RecoveryDecision(
        difference=diff,
        classification=RecoveryClassification.SCHEMA_DRIFT,
        risk=RecoveryRisk.MEDIUM,
        recommendation=RecoveryRecommendation.FORWARD_MIGRATION,
        rationale=f"Foreign key constraint on {diff.table_name}.{diff.column_name} is mismatched."
    )
```

### 2.3 Extending `executor.py`
Add handler logic inside the execution dispatcher loop:

```python
if decision.recommendation == RecoveryRecommendation.FORWARD_MIGRATION:
    # Run the SQL migration statement via MigrationRunner
    runner.execute_sql_statements((sql_payload,))
```

---

## 3. Dependency Rules

To maintain codebase clean separation and prevent dependency cycles, follow these rules:

1. **Core Immobility**: `models.py` represents the core domain. It must **never** import other files from the recovery framework.
2. **Analysis Purity**: The `DecisionAnalyzer` must be a pure logic class. It receives contexts and structures and outputs decisions. It must **never** perform filesystem IO, database transactions, or import click/cli libraries.
3. **Isolation of State modification**: Only `RecoveryExecutor` and `MigrationRunner` may execute write queries on the database. No DDL operations or ledger insertion logic is allowed in the Orchestrator, Inspector, or Analyzer.
4. **Direction of Imports**:
   * CLI (`commands.py`) -> Orchestrator (`orchestrator.py`)
   * Orchestrator (`orchestrator.py`) -> Inspector, Analyzer, Executor, Reporter
   * Executor (`executor.py`) -> MigrationRunner
   * All components -> Models (`models.py`)
