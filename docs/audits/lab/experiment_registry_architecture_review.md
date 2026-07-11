# EXPERIMENT REGISTRY ARCHITECTURE REVIEW

**Date:** 2026-07-11  
**Sprint:** 4.7  
**Component:** MoroQuant Lab - Experiment Registry (Phase 1)  
**Status:** **CONDITIONAL PASS**

---

## 1. Executive Summary

This report presents a production-grade architecture review of the Experiment Registry implemented during Phase 1 of Sprint 4.7. The implementation provides a functional CRUD database, service lifecycle, in-memory analytics engine, and RESTful API endpoints, backed by 26 passing unit tests. 

However, the implementation exhibits significant **architectural drift** from the domain boundaries and design patterns established for the MoroQuant Lab (implied by ADR-017 and general DDD principles). Specifically, files are scattered across legacy directories, domain models contain coupled metrics belonging to other registries (Validation, Calibration, and Models), and the database schema contains restrictive CHECK constraints that prevent supporting the full experiment lifecycle (e.g., Validation, Calibration, Promotion, Paper, Production).

Therefore, the Experiment Registry receives a **CONDITIONAL PASS**. It is functional and correct for a basic run-tracking database, but it must be refactored to conform to MoroQuant Lab's bounded context rules before it is integrated into the core production pipeline.

---

## 2. ADR Compliance & Architecture Drift

### MoroQuant Lab Boundaries
The MoroQuant Lab is intended to be a separate, isolated domain. Instead of encapsulating the Experiment Registry within a dedicated `lab` bounded context, the implementation scatters its code across system-wide folders:
*   [experiment_contract.py](file:///home/zafka/trade-dashboard/ml_service/models/experiment_contract.py) inside `ml_service/models/`
*   [experiment_repository.py](file:///home/zafka/trade-dashboard/ml_service/repositories/experiment_repository.py) inside `ml_service/repositories/`
*   [experiment_service.py](file:///home/zafka/trade-dashboard/ml_service/services/experiment_service.py) inside `ml_service/services/`
*   [experiment_analytics.py](file:///home/zafka/trade-dashboard/ml_service/analytics/experiment_analytics.py) inside `ml_service/analytics/`
*   [experiment_routes.py](file:///home/zafka/trade-dashboard/ml_service/api/experiment_routes.py) inside `ml_service/api/`

### Layer & Domain Ownership
This layout violates the domain boundaries by polluting generic shared directories with specific, research-only constructs. If every submodule (Feature Registry, Dataset Registry, etc.) does this, the generic folders will become unmaintainable. 

### Separation from Analytics & Trading
The analytics calculations are successfully isolated in `experiment_analytics.py` as pure functions, which satisfies the separation of concerns. However, the database model couples trading performance metrics (Sharpe, Sortino, Calmar ratios, Win Rate, Max Drawdown) and calibration metrics (ECE, Brier Score) directly into the core `experiments` table, leaking trading and calibration domain concerns into the experiment registry.

---

## 3. Package Structure Review

### Intended Lab Architecture
The expected layout for MoroQuant Lab modules is:
```
ml_service/
    lab/
        experiments/
            repository.py
            service.py
            analytics.py
            api.py
            types.py
```

### Legacy Package Structure Violations
The implementation instead uses:
```
ml_service/
    models/experiment_contract.py
    repositories/experiment_repository.py
    services/experiment_service.py
    analytics/experiment_analytics.py
    api/experiment_routes.py
```

### Consequences
1.  **High Coupling:** It is difficult to treat the "Lab" as a modular sub-system or extract it into a microservice in the future.
2.  **Naming Collisions:** Generic folder paths increase the chance of namespace collisions.
3.  **Low Cohesion:** Developers must navigate five distinct top-level directories to make changes to a single logical module (Experiments).

---

## 4. Database Review (Schema & Migration)

### Schema Audit (`030_create_experiments.sql`)
1.  **Primary Keys:** The schema uses standard autoincrement `id INTEGER PRIMARY KEY`. While acceptable for local SQLite development, the application relies on UUID strings `run_id` as the logical business key. For future migration to Postgres or distributed setups, `run_id` should serve as the primary key.
2.  **Indexes:** High-quality indexes are defined for query optimization:
    *   `idx_experiments_experiment_id`, `idx_experiments_run_id`, and `idx_experiments_status` are correctly defined.
    *   `idx_experiments_sharpe_ratio` uses a partial index `WHERE status = 'COMPLETED'`, which is highly efficient.
3.  **CHECK Constraints:**
    ```sql
    status TEXT NOT NULL CHECK(status IN ('CREATED', 'RUNNING', 'COMPLETED', 'FAILED'))
    ```
    This constraint is too rigid. It prevents recording mid-lifecycle states (e.g., `TRAINING`, `VALIDATING`, `CALIBRATING`) without a schema migration.
4.  **Normalization & Scalability:**
    *   **Flat Metrics Design:** All loss values and backtest metrics are stored in columns on the same row. This does not scale to multi-epoch logs or step-by-step validation metrics.
    *   **Hyperparameters:** Stored as a raw JSON text field. While functional, it makes database-level filtering based on specific hyperparameter values difficult and slow.

---

## 5. Domain Model Review

### `ExperimentContract` Dataclass
*   **Immutability:** Implemented correctly using `@dataclass(frozen=True)`.
*   **Field Ownership & Coupling:** The contract is cluttered with performance metrics (Sortino, Sharpe, ECE, Brier score) which belong to validation, calibration, or model governance. The core Experiment entity should focus on *inputs* (dataset version, hyperparameters, code state) and execution status.
*   **Missing Extensibility:** The flat design lacks metadata mapping. Storing arbitrary developer-defined metadata is impossible without altering the class definition.
*   **Missing Metadata Fields:** Missing execution context such as Git commit hash, environment variables, Python dependency versions, and execution host.

---

## 6. Repository Review

*   **SQL Isolation:** Exclusively contained within the repository layer.
*   **Transaction Boundaries & Connection Pooling:**
    *   Every query helper calls `get_connection()` and manually opens and closes the connection in a `try/finally` block.
    *   This prevents sharing database transactions across multiple operations or performing unit-of-work patterns in the Service layer.
*   **Parameter Binding:** Secure and properly parameterized using placeholder values (`?`), preventing SQL injection.

---

## 7. Service Review & Lifecycle Support

### Lifecycle States supported by current code:
*   `CREATED`
*   `RUNNING` (via `start_run`)
*   `COMPLETED` (via `complete_run`)
*   `FAILED` (via `fail_run`)

### Unsupported Lifecycle States:
*   `TRAINING`
*   `VALIDATING`
*   `CALIBRATING`
*   `PAPER` (Paper Trading Evaluation)
*   `PROMOTION` (Model Promotion Governance)
*   `PRODUCTION` (Active Live Performance)
*   `ARCHIVED`

### Limitations
By restricting the status values to a simple binary success state (`COMPLETED`/`FAILED`), the service cannot track where in the pipeline an active experiment currently resides. A run could fail during validation, calibration, or training, but it will simply be marked as `FAILED` without context.

---

## 8. Analytics Review

*   **Purity:** Fully compliant. All functions in `experiment_analytics.py` are pure, deterministic, and free of database/IO side effects.
*   **Scalability Limit:** The `calculate_experiment_analytics` function processes list items in Python memory. While fast for small experiments, loading 10,000+ experiment runs via `list_all_runs` to calculate simple aggregate averages will cause high memory usage and latency. Calculations should be offloaded to database aggregates (`AVG()`, `COUNT()`) at the SQL level.

---

## 9. Test Review

*   **Strengths:** Clear separation between unit tests using mock repositories (`test_experiment_service.py`) and database integration tests (`test_experiment_repository.py`).
*   **Gaps:**
    1.  **No API Integration Tests:** No tests exist to verify routes in `experiment_routes.py` with a FastAPI `TestClient`.
    2.  **No Migration Tests:** SQLite schema migrations are untested.
    3.  **No Validation Checking:** Tests do not verify behavior if database checks fail (e.g. inserting an invalid status).

---

## 10. Future Roadmap Review

| Registry / Center | Compatibility Status | Issue / Redesign Requirement |
| :--- | :--- | :--- |
| **Dataset Registry** | **Partial** | Stored as a raw string `dataset_version`. Cannot handle complex lineage or check existence of dataset. |
| **Feature Registry** | **Partial** | Stored as a raw string `feature_version`. Cannot link features to actual data columns. |
| **Validation Center** | **Poor** | Validation metrics are hardcoded inside the experiment table rather than referenced from a validation report entity. |
| **Calibration Center** | **Poor** | ECE and Brier score are hardcoded inside the experiment table. A separate Calibration entity is needed. |
| **Promotion Center** | **Poor** | The status field does not support promotion workflow states (e.g., `PROMOTION_REQUESTED`, `PROMOTED`). |
| **Model Registry** | **Poor** | Hardcoded model fields will overlap and clash with Model Registry contracts. |

---

## 11. Final Risk Assessment & Recommendations

### Strengths
1.  **100% Parameterization:** Zero SQL injection risks in the repository layer.
2.  **Dataclass Purity:** Dataclasses are immutable and correctly represent table schemas.
3.  **Pure Analytics:** Computations are easy to test and isolated from external dependencies.

### Weaknesses & Technical Debt
1.  **Architecture Drift:** Files are scattered in legacy structures, violating MoroQuant Lab domain isolation rules.
2.  **Restrictive Lifecycle:** SQL status constraints block necessary state transitions like Calibration, Validation, and Promotion.
3.  **Inefficient Connection Lifecycle:** Lack of connection pooling or transactional context injection.
4.  **Leaked Domain Concerns:** Aggregation of trade metrics directly into the core experiments table.

### Recommended Changes
1.  **Move to Lab Namespace:** Relocate code files into `ml_service/lab/experiments/` to restore encapsulation.
2.  **Relax Database CHECK Constraint:** Expand the status enum constraint in `030_create_experiments.sql` to support:
    `('CREATED', 'TRAINING', 'VALIDATING', 'CALIBRATING', 'COMPLETED', 'FAILED', 'PROMOTED', 'ARCHIVED')`
3.  **Add Metadata Column:** Replace metric/hyperparameter columns with a generic JSON field or split metrics into a separate `run_metrics` table to prevent table schema pollution.
4.  **Implement Dependency Injection for Database Transactions:** Allow repositories to share a connection context to support transactions across service operations.

---

## 12. Verdict

### **VERDICT: CONDITIONAL PASS**

The core functionality has been verified with tests, but the implementation violates package structure boundaries and blocks future roadmap execution due to restrictive enums and coupled metric storage. The recommended package reorganization and schema adjustments must be completed prior to production deployment.
