# Lab Domain Isolation Audit

**Date**: 2026-07-11  
**Status**: PASS WITH WARNINGS  
**Auditor**: Antigravity

---

## 1. Domain Boundary Inspection

This audit evaluates the isolation of the Experiment Registry inside the MoroQuant Lab subsystem to verify repository, service, API, database ownership, and dependency boundaries.

### 1.1 Repository Boundaries (PASS WITH WARNINGS)
*   **Status**: `ExperimentRepository` has been successfully migrated to [repository.py](file:///home/zafka/trade-dashboard/ml_service/lab/experiments/repository.py).
*   **Assessment**: It cleanly isolates all CRUD queries targeting the `experiments` tables. However, it imports the shared helper `get_connection` from [database.py](file:///home/zafka/trade-dashboard/ml_service/repositories/database.py), coupling it to core connection management.

### 1.2 Service Boundaries (PASS)
*   **Status**: The business logic is isolated in [service.py](file:///home/zafka/trade-dashboard/ml_service/lab/experiments/service.py).
*   **Assessment**: It enforces the state machine (`CREATED` -> `TRAINING` -> `VALIDATING` -> `CALIBRATING` -> `COMPLETED`/`FAILED`). No external components bypass this service layer to mutate state.

### 1.3 API Boundaries (PASS)
*   **Status**: FastAPI routes are defined in [api.py](file:///home/zafka/trade-dashboard/ml_service/lab/experiments/api.py) and registered in `api/main.py` with prefix `/api/lab`.
*   **Assessment**: High isolation. The routes only depend on the lab service layer.

### 1.4 Database Ownership (FAIL)
*   **Status**: The `experiments`, `experiment_configs`, and `experiment_results` tables reside directly in the unified system SQLite database `database.db`.
*   **Assessment**: Shared ownership. Because the Lab shares the exact SQLite database file with OHLCV data, execution analytics, and signal generation, there is no database-level isolation. An unindexed query in the lab could block the sqlite write-lock, slowing down live/paper trading.

### 1.5 Dependency Direction (PASS)
*   **Status**: Checked all imports.
*   **Assessment**: Correct dependency flow. Core systems (e.g., paper trading, scheduler, predictor) do not import anything from the `lab` namespace. The `lab` depends on shared models (`ExperimentContract`) and database connections, but there are no circular dependencies.

---

## 2. Recommendations for Full Isolation

1.  **Isolated Lab Database**: Migrate the experiments schema out of the main `database.db` and into a dedicated `lab.db` database file.
2.  **Move Domain Contract**: Relocate `ExperimentContract` from the shared `ml_service/models/` folder into `ml_service/lab/experiments/types.py` to achieve zero leakage.
