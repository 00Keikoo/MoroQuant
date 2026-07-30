# Database Recovery Framework Architecture

This document describes the design and system architecture of the Database Recovery & Migration Reconciliation Framework (ADR-023 v1.1).

---

## 1. Architectural System Diagram

The Recovery Framework isolates diagnostic logic from state-modifying execution. The following block diagram shows the logical relationships between runtime components:

```mermaid
graph TD
    subgraph Client / Pipeline
        CLI["CLI Command (db inspect / db recover)"]
        CICD["CI/CD Safety Gate (Pipeline Hook)"]
    end

    subgraph Coordination Layer
        Orch["RecoveryOrchestrator"]
    end

    subgraph Read-Only Diagnostic Phase
        Inspector["SchemaInspector"]
        Analyzer["DecisionAnalyzer"]
    end

    subgraph Transaction-Safe State Mutation
        Executor["RecoveryExecutor"]
        Runner["MigrationRunner"]
    end

    subgraph Logging & Audit
        Reporter["RecoveryReporter"]
    end

    subgraph Physical State
        DB[("SQLite Database\n(Schema & Metadata)")]
        Disk[("Migrations Directory\n(*.sql files)")]
    end

    CLI --> Orch
    CICD --> Orch
    
    Orch -->|1. Capture Snapshot| Inspector
    Inspector -->|Reads| DB
    
    Orch -->|2. Compare with Context| Analyzer
    Analyzer -.->|Reads available files| Disk
    
    Orch -->|3. Execute Decisions| Executor
    Executor -->|Coordinates Transactions| Runner
    Runner -->|Writes Schema & Ledger| DB
    
    Orch -->|4. Persist Audit| Reporter
    Reporter -->|Writes JSON| Disk
```

---

## 2. Component Responsibilities

| Component | Responsibility | Constraints |
| :--- | :--- | :--- |
| **`RecoveryOrchestrator`** | Coordinates the entire recovery workflow. It constructs the input context, executes diagnostics, triggers validation gates (e.g., approval token checks), runs the execution layer, and invokes the reporter. | Stateless. Contains no database mutations or direct IO. |
| **`SchemaInspector`** | Queries `sqlite_master` and database schemas to reconstruct the physical structure ("Schema Truth") as an immutable `SchemaSnapshot`. | Read-only. Does not query migration files or write to the database. |
| **`DecisionAnalyzer`** | Receives the `SchemaSnapshot` and compares it against the `DecisionContext` (applied ledger and filesystem files) to calculate classifications, risk grades, and recommendations. | Pure function. Completely deterministic and isolated from external dependencies. |
| **`RecoveryExecutor`** | Consumes approved `RecoveryDecision` payloads and executes the corrective actions. Coordinates transactional grouping and fail-fast behaviors. | Side-effect heavy. Modifies database state using short-lived transactions. |
| **`MigrationRunner`** | Underlying engine that parses SQL files, acquires SQLite table locks, applies statement sets, and updates the `schema_migrations` ledger. | Atomic transactions. Rolls back database to original state on any failure. |
| **`RecoveryReporter`** | Gathers execution telemetry, builds the `ExecutionSummary` object, and serializes a deterministic, sorted-key JSON report to the filesystem. | Restricts paths to avoid directory traversal. Writes atomically using a temporary staging file. |

---

## 3. Dependency Graph

The framework relies on strict dependency boundaries. Lower layers must never depend on higher layers.

```mermaid
graph TD
    subgraph UI & CLI
        CLI_cmd["ml_service/cli/commands.py"]
    end

    subgraph Service Coordination
        Orch_py["ml_service/migrations/recovery/orchestrator.py"]
    end

    subgraph Engine & IO
        Exec_py["ml_service/migrations/recovery/executor.py"]
        Insp_py["ml_service/migrations/recovery/schema_inspector.py"]
        Rep_py["ml_service/migrations/recovery/reporter.py"]
        Run_py["ml_service/migrations/recovery/migration_runner.py"]
    end

    subgraph Core Logic
        Anal_py["ml_service/migrations/recovery/decision/analyzer.py"]
    end

    subgraph Domain Models
        Mod_py["ml_service/migrations/recovery/models.py"]
    end

    CLI_cmd --> Orch_py
    Orch_py --> Insp_py
    Orch_py --> Anal_py
    Orch_py --> Exec_py
    Orch_py --> Rep_py
    
    Insp_py --> Mod_py
    Anal_py --> Mod_py
    Exec_py --> Mod_py
    Exec_py --> Run_py
    Rep_py --> Mod_py
    Run_py --> Mod_py
```

---

## 4. Execution Sequence Diagram

The interaction sequence for a complete database recovery run shows the separation of the read-only phase from the execution phase:

```mermaid
sequenceDiagram
    autonumber
    actor Operator
    participant CLI as CLI Layer
    participant Orch as RecoveryOrchestrator
    participant Insp as SchemaInspector
    participant Anal as DecisionAnalyzer
    participant Exec as RecoveryExecutor
    participant DB as SQLite Database
    participant Rep as RecoveryReporter

    Operator->>CLI: agy db recover --approve-token <token>
    CLI->>Orch: run_diagnostics()
    Orch->>Insp: capture_snapshot()
    Insp->>DB: PRAGMA table_info / index_list
    DB-->>Insp: physical structure definitions
    Insp-->>Orch: SchemaSnapshot
    
    Orch->>Orch: Load available files & ledger
    Orch->>Anal: analyze(differences, context)
    Anal-->>Orch: RecoveryDecisions[]
    
    Orch-->>CLI: Decisions & Risk levels
    
    Note over CLI,Operator: Check approvals for HIGH/CRITICAL actions
    alt Risk matches token validation
        CLI->>Orch: apply_recovery(decisions, operator, token)
        Orch->>Exec: execute(decisions)
        
        loop For each decision
            Exec->>DB: BEGIN IMMEDIATE
            Exec->>DB: Execute SQL statements
            Exec->>DB: Record ledger entry
            Exec->>DB: COMMIT
        end
        
        Exec-->>Orch: ExecutionResults[]
        Orch->>Rep: write_report(results, operator)
        Rep->>Rep: Format sorted-key JSON
        Rep-->>Orch: ExecutionSummary, report_path
        Orch-->>CLI: Summary & Report path
        CLI-->>Operator: Display success summary
    else Validation Failed
        CLI-->>Operator: Abort (Approval Required)
    end
```

---

## 5. Lifecycle Phases

The framework operates under three distinct lifecycle pipelines:

### 5.1 Dry-Run Lifecycle (Diagnostics)
1. **Instantiation**: The orchestrator resolves absolute paths to the database and migration assets.
2. **Inspection**: The `SchemaInspector` collects physical metadata (tables, columns, default values, indices).
3. **Ledger Alignment**: The orchestrator scans the filesystem and queries the `schema_migrations` table to build the `DecisionContext`.
4. **Analysis**: The `DecisionAnalyzer` matches differences against the taxonomy, determines risk metrics, and returns decisions.

### 5.2 Apply Lifecycle (State Modification)
1. **Pre-Execution Check**: Verifies that no `HALT` recommendations exist and that the environment is clear.
2. **Approval Verification**: Matches calculated risk grades with user validation prompts and secure tokens.
3. **Stepwise Transactions**: Applies statements grouped by decision.
4. **Ledger Update**: Synchronizes physical schema changes with entries inside `schema_migrations`.
5. **Auditing**: Emits the final execution telemetry to the audit storage log.

### 5.3 Approval Token Lifecycle
The token controls the deployment permissions for high-impact drift remediation:
* **Storage**: Protected environment variable (`MQ_CTO_APPROVAL_TOKEN`) on deployment target servers.
* **Handshake**: Passed from CLI runtime flag `--approve-token` (or local env variable) into `RecoveryOrchestrator.apply_recovery`.
* **Assertion**: If the analyzer labels any decision as `HIGH` or `CRITICAL`, the orchestrator checks that the input token matches the server-side environment value. If it mismatches, it halts immediately with `ApprovalRequiredError`.

---

## 6. Transaction Ownership & Boundaries

```
                    ┌────────────────────────────┐
                    │      RecoveryExecutor      │
                    └─────────────┬──────────────┘
                                  │ Directs loop
                                  v
                    ┌────────────────────────────┐
                    │      MigrationRunner       │
                    └─────────────┬──────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         │ BEGIN IMMEDIATE                                 │
         │   -> Applies corrective DDL statement           │
         │   -> Inserts entry in schema_migrations ledger  │
         │ COMMIT / ROLLBACK on Exception                  │
         └─────────────────────────────────────────────────┘
```

* **Unit of Atomicity**: Every recovery decision has its own isolated transaction boundary. 
* **Rollback Isolation**: A DDL syntax failure or index conflict within a specific recovery step triggers an immediate transaction `ROLLBACK`. This prevents partial states and ensures that only fully successful steps are recorded in the ledger.
* **Database Isolation**: The runner sets `PRAGMA busy_timeout = 5000` and locks tables using immediate-write permissions to prevent deadlocks and block read/write operations by other connections during the short recovery windows.
