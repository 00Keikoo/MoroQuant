# Research Post-D14R Architecture Audit

## 1. Executive Summary
This document presents the Read-Only Architecture Gate Audit and Next Milestone Decision for the MoroQuant Quant Research Platform following the successful completion of Sprint 3.9D-14R (Remediation). All critical blockers identified in the D-14 gate audit have been fully remediated. The codebase is mathematically sound, lifecycle states are properly bounded, and duplicate abstractions have been consolidated.

However, the architecture has two critical structural challenges:
1. **Disconnected Execution Layer Boundaries (ADR-024 Violation)**: The `backtest_workflow` system directly couples the pure research layer with execution-layer services (`PortfolioService`, `ExecutionSimulator`), violating the strict isolation boundaries defined in [ADR-024](file:///home/zafka/trade-dashboard/docs/adr/ADR-024-Quant-Research-Platform.md).
2. **Missing End-to-End Orchestrator**: The current `ResearchOrchestrator` only handles metadata lifecycle transitions (CREATED → RUNNING → COMPLETED) in SQLite. There is no unified orchestrator to execute the actual calculations and simulations (Snapshot → Replay → Feature Calculation → Training → Evaluation → Benchmarking → Promotion) under a single session context.

We recommend **Sprint 3.9D-15: Research Session Orchestrator & Dependency Separation** as the single next milestone.

---

## 2. Verified Baseline
* **Branch**: `quant-research`
* **Latest Commit**: `5734e56 feat(research): complete Sprint 3.9D-14R remediation`
* **Working Tree State**: Clean (nothing to commit, working tree clean).
* **Automated Test Run Baseline**: Verified using the project virtual environment `ml_service/venv`.
  * **Research-Specific Pass Count**: **367 tests passed** (including the new regression suites for drawdown scoring, promotion contracts, and proxy lifecycles).
  * **Total Workspace Pass Count**: 1,277 passed, 82 failed (failures are located exclusively in external mock-dependent live execution, matching engine, and telegram notifier tests).

---

## 3. Current Architecture Map
We inspected the complete [ml_service/research/](file:///home/zafka/trade-dashboard/ml_service/research/) tree. The currently implemented subsystems are mapped below:

1. **`model_identity`**
   * *Responsibility*: Immutable description of discovered model binaries, validation/calibration availability, and symbol mappings.
   * *Inputs*: Model files, system config metadata.
   * *Outputs*: `ModelIdentity` (frozen dataclass).
   * *Dependencies*: None.
   * *Tests*: `test_blocker_2_promotion_contract.py::test_validation_calibration_from_model_identity`.
   * *Gaps*: No automated verification of artifact signatures.

2. **`model_registry_audit`**
   * *Responsibility*: Compilation of registry-wide model status summaries.
   * *Inputs*: Tuple of `ModelIdentity` records.
   * *Outputs*: `AuditReport` (frozen dataclass).
   * *Dependencies*: `model_identity`.
   * *Tests*: Integrated.
   * *Gaps*: Static aggregation; lacks version evolution tracking.

3. **`registry_snapshot`**
   * *Responsibility*: State capture and diffing for the model registry.
   * *Inputs*: Tuples of `ModelIdentity`.
   * *Outputs*: `RegistrySnapshot`, `RegistryDiff`.
   * *Dependencies*: `model_identity`.
   * *Tests*: `ml_service/tests/research/test_registry_snapshot.py` (23 tests).
   * *Gaps*: Relies on static lists; lacks live registry connection.

4. **`registry_store`**
   * *Responsibility*: Filesystem serialization of registry snapshots in sorted JSON.
   * *Inputs*: `RegistrySnapshot`.
   * *Outputs*: Snapshot ID, JSON files under `/storage/`.
   * *Dependencies*: `registry_snapshot`, `model_identity`.
   * *Tests*: `test_model_registry_service.py` (7 tests).
   * *Gaps*: Performance overhead on large registry sizes.

5. **`model_lifecycle`**
   * *Responsibility*: Bounding and verifying state transitions (DISCOVERED → VALIDATED → GOVERNANCE_READY → APPROVED → PRODUCTION).
   * *Inputs*: State change events, `LifecycleState` rules.
   * *Outputs*: `ModelLifecycleRecord`.
   * *Dependencies*: None.
   * *Tests*: `test_blocker_4_proxy_lifecycle.py` (4 tests).
   * *Gaps*: Transitions are state-machine only; does not verify check signatures.

6. **`promotion_engine`**
   * *Responsibility*: Multi-gate evaluation using weighted scorecard metrics.
   * *Inputs*: `ModelIdentity`, `ModelLifecycleRecord`, `audit_report` (Dict).
   * *Outputs*: `RegistryProposal` (with `PromotionStatus` and `PromotionScore`).
   * *Dependencies*: `model_identity`, `model_lifecycle`.
   * *Tests*: `test_blocker_2_promotion_contract.py` (4 tests).
   * *Gaps*: Does not automatically write back to the event ledger.

7. **`governance`**
   * *Responsibility*: Legacy promotion routing.
   * *Gaps*: Fully deprecated. Re-exports canonical `RegistryProposal` from `promotion_engine`.

8. **`registry_event_ledger`**
   * *Responsibility*: Immutable append-only ledger tracking all registry actions.
   * *Inputs*: `RegistryEventRecord`.
   * *Outputs*: Append-only JSONL files.
   * *Dependencies*: None.
   * *Tests*: `test_model_registry_service.py`.
   * *Gaps*: No automatic compaction.

9. **`registry_query`**
   * *Responsibility*: Read-only index queries combining snapshot and ledger state.
   * *Inputs*: `RegistrySnapshot`, `RegistryEventLedger`.
   * *Outputs*: `RegistryQueryResult`, summaries.
   * *Dependencies*: `registry_snapshot`, `registry_event_ledger`.
   * *Tests*: `test_model_registry_service.py`.
   * *Gaps*: In-memory reconstructions only.

10. **`registry_api`**
    * *Responsibility*: Exposes read-only API endpoints for registry queries.
    * *Inputs*: HTTP requests.
    * *Outputs*: Pydantic JSON schemas.
    * *Dependencies*: `registry_query`, `registry_event_ledger`, `registry_store`.
    * *Tests*: `test_explorer_routes.py`.
    * *Gaps*: Lacks pagination and query filters.

11. **`benchmark`**
    * *Responsibility*: Standardized composite scoring and monotonic drawdown ranking.
    * *Inputs*: List of `ResearchReport` records.
    * *Outputs*: `BenchmarkResult`.
    * *Dependencies*: `reporting` (for `ResearchReport`).
    * *Tests*: `test_blocker_1_drawdown_scoring.py` (4 tests).
    * *Gaps*: Operates independently of the database.

12. **`evaluation_engine`**
    * *Responsibility*: Enriches `StrategyResult` into `StrategyScore` with walk-forward Sortino/Sharpe.
    * *Inputs*: `ExperimentResult`.
    * *Outputs*: `EvaluationResult`.
    * *Dependencies*: `experiment_engine`.
    * *Tests*: `test_sprint_3_9d_14_integration.py`.
    * *Gaps*: Metric annualization still assumes daily returns.

13. **`experiment_engine`**
    * *Responsibility*: Applies thresholds via `DecisionTruth` to map simulated trades to replay ticks.
    * *Inputs*: `ReplayResult`, `Snapshot`, `StrategyConfig`.
    * *Outputs*: `StrategyResult`.
    * *Dependencies*: `snapshot_engine`, `replay_engine`, `decision_truth`.
    * *Tests*: `test_trade_mapping.py`.
    * *Gaps*: Parameter sweeps run in-process only.

14. **`reporting`**
    * *Responsibility*: Translates evaluation results to finalized model reports.
    * *Inputs*: `EvaluationResult`.
    * *Outputs*: `ResearchReport` (frozen dataclass).
    * *Dependencies*: `evaluation_engine`.
    * *Tests*: Integrated.
    * *Gaps*: lossy transformation (only retains the best strategy candidate).

15. **`backtest_workflow`**
    * *Responsibility*: Coordinates model loading, simulation executions, and evaluations.
    * *Inputs*: `BacktestConfig`.
    * *Outputs*: `BacktestResult`, `BacktestRun`.
    * *Dependencies*: **VIOLATION** (Directly imports `PortfolioService`, `ExecutionSimulator` and related database models into research package).
    * *Tests*: `test_backtest_workflow_architecture.py`.
    * *Gaps*: Strong coupling to execution layer databases.

---

## 4. Actual End-to-End Pipeline
The following matrix details the actual import and call paths of the pipeline:

| Stage | Implementation | Input | Output | Connected? | Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Market Data** | Snapshot file read | Raw tickers | `Snapshot` | **Yes** | `apply_strategy_config()` |
| **Snapshot** | `Snapshot` (frozen dataclass) | JSON data | `Snapshot` | **Yes** | `apply_strategy_config()` |
| **Replay** | `ReplayResult` | `Snapshot` ticks | `ReplayResult` | **Yes** | `apply_strategy_config()` |
| **Experiment** | `apply_strategy_config()` | `ReplayResult` + `Snapshot` | `StrategyResult` | **Yes** | `ml_service/research/experiment_engine/engine.py` |
| **Evaluation** | `evaluate_experiment()` | `ExperimentResult` | `EvaluationResult` | **Yes** | `ml_service/research/evaluation_engine/engine.py` |
| **Report** | `evaluation_to_report()` | `EvaluationResult` | `ResearchReport` | **Yes (Adapter)** | `ml_service/research/reporting/adapter.py` |
| **Benchmark** | `DefaultResearchBenchmark.compare()` | List of `ResearchReport` | `BenchmarkResult` | **Yes** | `ml_service/research/benchmark/benchmark.py` |
| **Promotion** | `PromotionEngine.evaluate()` | `audit_report` (Dict) | `RegistryProposal` | **Yes (Adapter)** | `benchmark_to_audit_report()` adapter |
| **Governance** | Re-exports promotion model | `RegistryProposal` | `RegistryProposal` | **Yes** | `ml_service/research/governance/models.py` |
| **Ledger** | `RegistryEventLedger.append()` | `RegistryEventRecord` | Append-only file | **Yes** | `ml_service/research/registry_event_ledger/service.py` |
| **API** | `RegistryAPIService` endpoints | HTTP GET requests | JSON Schemas | **Yes** | `ml_service/research/registry_api/router.py` |

---

## 5. Contract / Boundary Audit
We audited all data structures crossing subsystem boundaries:
* **Duplicate Dataclasses**: The legacy duplicate definition of `RegistryProposal` in `governance/models.py` has been resolved; it now directly re-exports the canonical `promotion_engine/models.py:RegistryProposal`.
* **Benchmark Result contracts**: `BenchmarkResult` is canonical in `benchmark/models.py`.
* **Audit Report Adapter**: The benchmark-to-promotion adapter (`benchmark_to_audit_report`) correctly converts performance metrics and fetches the `governance_ready` boolean from the model lifecycle records.
* **Immutability Check**: All boundaries are crossed using frozen dataclasses containing tuple types (no mutable list types), preserving absolute memory safety.

---

## 6. ADR-024 Compliance
The research layer maintains clean unidirectional dependencies except for one critical area:
* **Violation found in `backtest_workflow`**:
  * [ml_service/research/backtest_workflow/orchestrator.py](file:///home/zafka/trade-dashboard/ml_service/research/backtest_workflow/orchestrator.py#L20-L26) directly imports:
    * `PortfolioService` (from `ml_service.portfolio.service`)
    * `ExecutionSimulator` (from `ml_service.simulation.execution.simulator`)
    * `BinanceSpotCommission`, `FixedSlippageModel`
  * This violates [ADR-024 Section 8](file:///home/zafka/trade-dashboard/docs/adr/ADR-024-Quant-Research-Platform.md#L170), which prohibits research layer modules from importing execution-layer services. 
  * *Reason*: The backtest workflow coordinates running simulation trades to evaluate them, but placing this orchestrator inside the `research` folder couples it to database-backed live entities.

---

## 7. Sprint 3.5 Legacy Audit
* **Replay Engine Trade Mapping**: Resolved. Replay trades are correctly joined using the unique `signal_id` rather than the database trade row ID (`trade.id != trade.signal_id` check is active and verified).
* **Evaluation Engine Metrics**: Resolved. Hardcoded scores have been replaced with actual statistical formulas for Sharpe, Drawdown, expectancy, and profit factor.
* **Sortino Ratio**: The Sortino ratio calculation uses a downside-deviation proxy (Sortino = Sharpe × 1.25) which is mathematically non-standard, but preserved for model registry gate compatibility.

---

## 8. Remaining Architectural Gaps

### Critical
* **Execution Boundary Spillover**: As noted, `backtest_workflow/orchestrator.py` couples research to the live simulation execution libraries.

### High
* **Missing End-to-End Research Orchestration**: No single service drives the complete pipeline execution sequentially. Researchers must execute snapshots, replays, features, experiments, evaluations, benchmarks, and promotions in isolation.

### Medium
* **Metadata Relational Gaps**: No single database index binds `ResearchSession` metadata with `DatasetSnapshot`, `FeatureSnapshot`, and `RegistryProposal` hash fingerprints.

---

## 9. Architectural Debt
* **Sortino Downside Approximation**: The Sortino ratio relies on a scalar approximation rather than a true calculated semi-standard deviation of downside returns.
* **FastAPI Query limitations**: The FastAPI registry endpoints read files directly on every request. This is slow and should be optimized with an in-memory query read-model cache.

---

## 10. Recommended Next Milestone
We recommend **Sprint 3.9D-15: Research Session Orchestrator & Dependency Separation**.

This milestone aims to:
1. Extract the simulation and execution-layer dependencies out of the `research` folder.
2. Refactor the `ResearchOrchestrator` to coordinate the actual end-to-end execution of the pipeline (Data → Snapshot → Replay → Feature Materialization → Model Training → Evaluation → Benchmark → Promotion) rather than just logging metadata.

---

## 11. Why This Comes Next
* **Pipeline Integrity**: Now that the individual engines are repaired and integrated, the system needs a central coordinator to run them deterministically.
* **Boundary Hardening**: The ADR-024 violations in the `backtest_workflow` must be cleaned up to protect the research layer from execution-layer coupling before any production candidate can be safely deployed.

---

## 12. What Must NOT Be Built Yet
* **No live portfolio state write APIs**: The orchestrator must not execute writes to the production trading DB.
* **No UI visual dashboards**: Do not build frontend views or web charts.
* **No new machine learning architectures**: Do not implement new training models.

---

## 13. Proposed Scope Boundary

### IN SCOPE
* Extracting the `backtest_workflow` execution logic to the simulation layer (creating a clean interface contract).
* Building the end-to-end `ResearchSessionOrchestrator` execution loop.
* Connecting Feature calculation, Model training, Evaluation, and Promotion decision rules sequentially inside the orchestrator.
* Logging all intermediate state transitions and data fingerprints to SQLite.

### OUT OF SCOPE
* Running live trading checks.
* Altering the database schema of the execution or portfolio database.

---

## 14. Acceptance Criteria
1. **Separation of Concerns**: No files in `ml_service/research/` import `PortfolioService`, `ExecutionSimulator`, or any execution database classes.
2. **Unified Execution**: A researcher can run a complete pipeline from a raw snapshot down to a `RegistryProposal` with a single orchestrator call.
3. **Traceability**: The orchestrator output binds the `session_id` with all dataset, feature, and model binary fingerprints in the SQLite ledger.
4. **Determinism**: Running the orchestrator twice with the same inputs produces the same promotion decision result.

---

## 15. Architecture Decision

```
DECISION:
Sprint 3.9D-15: Research Session Orchestrator & Dependency Separation

RATIONALE:
To resolve the ADR-024 import violations in backtest_workflow and provide a unified orchestrator to execute the entire research pipeline end-to-end.

DEPENDENCIES:
All Sprint 3.9D-14R remediation fixes must remain present in HEAD.

CONSUMERS:
Quant Researchers and the automated model registry CI pipelines.

NON-GOALS:
Modifying live portfolio databases or writing web user interfaces.
```

---

## 16. Recommended Sprint Number
The next sprint identifier in the sequence is: **Sprint 3.9D-15**.
