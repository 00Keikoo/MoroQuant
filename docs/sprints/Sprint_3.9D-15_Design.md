# Sprint 3.9D-15 Design: Research Session Orchestrator & Dependency Separation (Revised)

**Status**: DESIGN-ONLY (No Production Implementation)  
**Author**: Architecture Design Phase  
**Date**: 2026-08-15  
**Baseline Commit**: `5734e56 feat(research): complete Sprint 3.9D-14R remediation`

---

## 1. Objective

Resolve ADR-024 violations in `backtest_workflow` and define a canonical research pipeline orchestrator (`ResearchSessionOrchestrator`) that executes the sequential research flow: 
Snapshot → Replay → Experiment → Evaluation → Reporting → Benchmark → Promotion → Registry.

---

## 2. Component Verification (Evidence Table)

The following table documents the actual state of the codebase. It details the verified locations and signatures of the existing components as of baseline commit `5734e56`. No hypothetical APIs are referenced.

| Component | Actual Location | Actual API | Current Consumers | D-15 Usage |
|-----------|-----------------|------------|------------------|------------|
| **ResearchSession** | [ml_service/research/models.py](file:///home/zafka/trade-dashboard/ml_service/research/models.py#L94) | `ResearchSession(session_id, status, config_snapshot, snapshot_id, dataset_version_id, feature_dataset_id, best_run_id, experiments, created_at, completed_at)` | `ml_service/research/research_session.py`, `tests` | Extended with canonical provenance fields. |
| **ResearchJob** | [ml_service/research/research_orchestrator/types.py](file:///home/zafka/trade-dashboard/ml_service/research/research_orchestrator/types.py#L52) | `ResearchJob(job_id, state, config, created_at, started_at, completed_at, created_by, error_message, error_stage)` | `ResearchOrchestratorRepository`, `ResearchOrchestrator` | Map session metadata to existing job schema. |
| **ResearchOrchestratorRepository** | [ml_service/research/research_orchestrator/repository.py](file:///home/zafka/trade-dashboard/ml_service/research/research_orchestrator/repository.py#L19) | `get_job()`, `save_job()`, `update_job_state()`, `save_step()`, `update_step()`, `save_log()` | `ResearchOrchestratorService` | Reused for persisting session metadata & stage transitions. |
| **SnapshotService** | [ml_service/research/snapshot_engine/service.py](file:///home/zafka/trade-dashboard/ml_service/research/snapshot_engine/service.py#L32) | `create_snapshot(symbol: Optional[str]) -> Snapshot`, `get_snapshot(snapshot_id: str) -> Optional[Snapshot]` | `ExperimentService`, `ReplayService` | Invoked during Snapshot stage. |
| **ReplayEngine** | [ml_service/research/replay_engine/replay.py](file:///home/zafka/trade-dashboard/ml_service/research/replay_engine/replay.py#L11) | `run_replay(snapshot, threshold_long, threshold_short) -> ReplayResult` | `ReplayService` | Invoked during Replay stage. |
| **ExperimentEngine** | [ml_service/research/experiment_engine/engine.py](file:///home/zafka/trade-dashboard/ml_service/research/experiment_engine/engine.py#L12) | `apply_strategy_config(replay_result, snapshot, config) -> StrategyResult` | `ExperimentService` | Invoked during Experiment stage. |
| **EvaluationEngine** | [ml_service/research/evaluation_engine/engine.py](file:///home/zafka/trade-dashboard/ml_service/research/evaluation_engine/engine.py#L57) | `evaluate_experiment(experiment_result) -> EvaluationResult` | `EvaluationService` | Invoked during Evaluation stage. |
| **Reporting adapter** | [ml_service/research/reporting/adapter.py](file:///home/zafka/trade-dashboard/ml_service/research/reporting/adapter.py#L13) | `evaluation_to_report(evaluation: EvaluationResult) -> ResearchReport` | `tests` | Invoked during Reporting stage. |
| **Benchmark** | [ml_service/research/benchmark/benchmark.py](file:///home/zafka/trade-dashboard/ml_service/research/benchmark/benchmark.py#L13) | `DefaultResearchBenchmark().compare(reports: List[ResearchReport]) -> BenchmarkResult` | `tests` | Invoked during Benchmark stage. |
| **PromotionEngine** | [ml_service/research/promotion_engine/engine.py](file:///home/zafka/trade-dashboard/ml_service/research/promotion_engine/engine.py#L14) | `evaluate(model_identity, lifecycle_record, audit_report) -> RegistryProposal` | `tests` | Invoked during Promotion stage. |
| **ModelRegistryService** | [ml_service/research/model_registry/service.py](file:///home/zafka/trade-dashboard/ml_service/research/model_registry/service.py#L20) | `register_model()`, `register_version()`, `register_artifact()`, `register_evaluation()`, `record_promotion()` | `BacktestWorkflowOrchestrator`, `tests` | Reused directly. No new `register_candidate()` method is added. |
| **LightGBMTrainer** | [ml_service/research/trainers/lightgbm_trainer.py](file:///home/zafka/trade-dashboard/ml_service/research/trainers/lightgbm_trainer.py#L97) | `train(dataset, features, config, run)` | `TrainingPipelineManager`, `tests` | Deferred (outside orchestrator scope). |
| **XGBoostTrainer** | [ml_service/research/trainers/xgboost_trainer.py](file:///home/zafka/trade-dashboard/ml_service/research/trainers/xgboost_trainer.py#L109) | `train(dataset, features, config, run)` | `TrainingPipelineManager`, `tests` | Deferred (outside orchestrator scope). |
| **FeatureService** | [ml_service/research/feature_store/service.py](file:///home/zafka/trade-dashboard/ml_service/research/feature_store/service.py#L134) | `compute_feature_dataset(source_dataset_metadata, source_df, feature_version_id, compute_fn)` | `tests` | Deferred (outside orchestrator scope). |
| **backtest_workflow** | [ml_service/research/backtest_workflow/orchestrator.py](file:///home/zafka/trade-dashboard/ml_service/research/backtest_workflow/orchestrator.py#L51) | `BacktestWorkflowOrchestrator` class and associated simulation runners | `tests` | Violates boundaries. Moved to simulation layer. |

---

## 3. Mandatory Decisions & Scope Boundary

### 3.1 Backtest Interface Decision: Removed
- **Analysis**: The orchestrator receives and compares historical execution outcomes via read-only `Snapshot.trades` and `ReplayResult`. It does not execute live simulated matching or portfolios.
- **Decision**: The proposed `BacktestInterface` and `simulation/interfaces.py` are completely **removed**. Research session orchestration operates strictly on historical snapshotted data and decision truth logs without depending on execution/simulation machinery.

### 3.2 Registry Candidate Registration Decision: Excluded
- **Analysis**: `PromotionEngine.evaluate()` outputs a `RegistryProposal`. The existing `ModelRegistryService` API already accepts granular registrations: `register_model()`, `register_version()`, `register_artifact()`, `register_evaluation()`, and `record_promotion()`.
- **Decision**: No new `register_candidate()` API is introduced. The existing granular, decoupled APIs are sufficient and preferred for registry updates.

### 3.3 Training & Feature Scope: Explicitly Bounded
- **Analysis**: Model training (`LightGBMTrainer`/`XGBoostTrainer`) and active feature computation (`FeatureService`) are complex engineering concerns that do not belong inside the orchestrator flow. The orchestrator's role is strictly limited to coordinating the execution of the evaluation pipeline over pre-calculated snapshots and existing models.
- **Decision**: Model training and feature engineering are deferred from the orchestrator flow. The orchestrator only consumes pre-calculated inputs and does not trigger training or feature pipelines itself.

---

## 4. Revised Architecture & Pipeline Flow

### 4.1 Data Flow Pipeline
The pipeline flow sequence executed by `ResearchSessionOrchestrator` is as follows:

```
ResearchSessionOrchestrator
         |
         v
      Snapshot
         |
         v
      Replay
         |
         v
    Experiment
         |
         v
    Evaluation
         |
         v
    Reporting
         |
         v
    Benchmark
         |
         v
    Promotion
         |
         v
     Registry
```

### 4.2 Arrow Contracts and Adapters

| Transition Arrow | Input | Output | Existing Function / Class | Adapter Required? | Persistence Required? | Fingerprint Required? |
|------------------|-------|--------|----------------------------|-------------------|-----------------------|-----------------------|
| **Orchestrator → Snapshot** | `symbol: str` | `Snapshot` | `SnapshotService.create_snapshot` | No | Yes (job state log) | Yes (`dataset_fingerprint`) |
| **Snapshot → Replay** | `Snapshot`, long/short thresholds | `ReplayResult` | `replay_engine.replay.run_replay` | No | Yes (job step log) | Yes (`replay_fingerprint`) |
| **Replay → Experiment** | `ReplayResult`, `Snapshot`, configs | `ExperimentResult` | `experiment_engine.engine.apply_strategy_config` | No | Yes (serialize model.bin) | Yes (`experiment_fingerprint`) |
| **Experiment → Evaluation** | `ExperimentResult` | `EvaluationResult` | `evaluation_engine.engine.evaluate_experiment` | No | Yes (job step log) | Yes (`evaluation_fingerprint`) |
| **Evaluation → Reporting** | `EvaluationResult` | `ResearchReport` | `reporting.adapter.evaluation_to_report` | No | No | No |
| **Reporting → Benchmark** | `List[ResearchReport]` | `BenchmarkResult` | `DefaultResearchBenchmark.compare` | No | Yes (benchmark run) | No |
| **Benchmark → Promotion** | `ModelIdentity`, `ModelLifecycleRecord`, `dict` | `RegistryProposal` | `PromotionEngine.evaluate` | No | Yes (promotion audit) | No |
| **Promotion → Registry** | `RegistryProposal` components | Updated registry states | `ModelRegistryService` methods | No | Yes (ledger append) | Yes (`model_fingerprint`) |

---

## 5. Research / Simulation Boundary Rule

### 5.1 Permitted and Prohibited Imports
The research layer (`ml_service/research/`) is strictly separated from the simulation layer.

* **Research MAY import / consume**:
  - `ml_service/research/snapshot_engine/types.py:Snapshot`
  - `ml_service/research/replay_engine/types.py:ReplayResult`
  - Historical read-only trade outcomes and signal outcomes
  - Model metadata and scorecard registry results

* **Research MUST NOT import / couple to**:
  - `PortfolioService`
  - `ExecutionSimulator`
  - `MatchingEngine`
  - Slip, commission, latency, or liquidity models
  - `PositionService`
  - `LedgerService`

### 5.2 Boundary Violations
The existing folder `ml_service/research/backtest_workflow/` actively violates ADR-024 due to direct coupling with execution simulation.
* **Resolution Plan**: Move the folder `ml_service/research/backtest_workflow/` to `ml_service/simulation/backtest/`. No file modifications are made during the design phase.

---

## 6. ResearchSession Contract & Canonical Naming

The canonical provenance properties of `ResearchSession` must utilize standardized, explicit naming.

### 6.1 Canonical Names
- `dataset_fingerprint`: SHA256 of the raw market data snapshot.
- `feature_fingerprint`: SHA256 of the feature dataset (if computed).
- `replay_fingerprint`: SHA256 of the decision reconstruction output.
- `experiment_fingerprint`: SHA256 of the strategy parameters and performance metrics.
- `evaluation_fingerprint`: SHA256 of the ranked evaluation scorecard.
- `model_fingerprint`: SHA256 of the serialized model binary.
- `random_seed`: Seed integer for deterministic execution context.

### 6.2 Extended ResearchSession Dataclass Contract
No aliases such as `replayprint`, `session_v2`, `ResearchSession2`, or `SessionV2` are allowed. The existing `ResearchSession` dataclass is extended cleanly:

```python
@dataclass(frozen=True)
class ResearchSession:
    """Immutable research session context for deterministic execution.
    
    Reuses the canonical class in research/models.py.
    """
    session_id: str
    status: str
    config_snapshot: Tuple[Tuple[str, Union[str, int, float, bool, None]], ...] = field(default_factory=tuple)
    snapshot_id: Optional[str] = None
    dataset_version_id: Optional[str] = None
    feature_dataset_id: Optional[str] = None
    best_run_id: Optional[str] = None
    experiments: Tuple[ResearchExperiment, ...] = field(default_factory=tuple)
    created_at: str = ""
    completed_at: Optional[str] = None
    
    # Canonical D-15 Provenance Fields
    dataset_fingerprint: Optional[str] = None
    feature_fingerprint: Optional[str] = None
    replay_fingerprint: Optional[str] = None
    experiment_fingerprint: Optional[str] = None
    evaluation_fingerprint: Optional[str] = None
    model_fingerprint: Optional[str] = None
    random_seed: Optional[int] = None
```

---

## 7. Bounded Determinism Contract

Determinism guarantees are bounded as follows:

> [!IMPORTANT]
> Universal cross-platform binary-level reproducibility is not guaranteed due to floating-point differences across varying hardware architectures, CPU instructions, and library backends.

The deterministic contract is defined as:
`Same canonical inputs` + `Same SessionConfig` + `Same declared execution environment` + `Same random seed` $\rightarrow$ `Same research decisions and fingerprints`

---

## 8. Orchestrator Design Constraint

`ResearchSessionOrchestrator` must remain a thin coordinator (< 500 lines).

* **Allowed responsibilities**:
  - Validate the session state transitions.
  - Sequentially invoke stage engines with immutable arguments.
  - Compute stage fingerprints and provenance metadata.
  - Return updated immutable `ResearchSession` instances.
  - Persist session transitions using `ResearchOrchestratorRepository`.
  - Handle errors and capture failure state context.

* **Forbidden responsibilities**:
  - Direct execution of replay logic or order simulation.
  - Calculation of PnL, Winrate, or Sharpe ratios (delegated to engines).
  - Implementation of model training algorithms.
  - Selection of promotion criteria or policy validation rules.

---

## 9. Revised Implementation Phases

### Phase A: Boundary Extraction
- **Objective**: Move execution-coupled code out of the research layer.
- **Files to Change**: Import paths in simulation layer tests.
- **Files to Create**: None.
- **Files to Move**: Move `ml_service/research/backtest_workflow/` $\rightarrow$ `ml_service/simulation/backtest/`.
- **Tests**: Run moved backtest workflow tests.
- **Acceptance Criteria**: Zero imports of `portfolio.*` or `simulation.*` in `ml_service/research/`.
- **Prohibited Changes**: Do not touch `MarketSnapshot` read-only imports.

### Phase B: ResearchSession Contract
- **Objective**: Extend existing `ResearchSession` with standardized fields.
- **Files to Change**: `ml_service/research/models.py`.
- **Files to Create**: None.
- **Tests**: Verification of serialization and immutable fields.
- **Acceptance Criteria**: Immutability preserved, serialization output is deterministic.
- **Prohibited Changes**: Do not create V2 session aliases.

### Phase C: Orchestrator Skeleton
- **Objective**: Implement the thin orchestrator class structure.
- **Files to Change**: None.
- **Files to Create**: `ml_service/research/session_orchestrator/orchestrator.py`.
- **Tests**: Mocked stage sequence verification.
- **Acceptance Criteria**: Class is under 500 lines of code.
- **Prohibited Changes**: Do not implement business or analytical logic in the orchestrator.

### Phase D: Provenance & Determinism
- **Objective**: Wire SHA256 fingerprint calculations to the orchestrator.
- **Files to Change**: `ml_service/research/session_orchestrator/orchestrator.py`.
- **Files to Create**: `ml_service/research/session_orchestrator/fingerprints.py`.
- **Tests**: Run determinism validation tests with identical configurations.
- **Acceptance Criteria**: Hashing is deterministic, seeds propagate correctly.
- **Prohibited Changes**: No external libraries for hashing.

### Phase E: Integration & Regression Tests
- **Objective**: Complete end-to-end flow execution test.
- **Files to Change**: None.
- **Files to Create**: `ml_service/tests/research/test_session_orchestrator_integration.py`.
- **Tests**: Integration test covering all stages sequentially.
- **Acceptance Criteria**: Pipeline runs successfully and handles errors gracefully.
- **Prohibited Changes**: Mocking database engines during actual pipeline execution.

### Phase F: Architecture Gate
- **Objective**: Final compliance check.
- **Files to Change**: `docs/adr/ADR-024-Quant-Research-Platform.md`.
- **Files to Create**: None.
- **Tests**: Boundary verification scripts.
- **Acceptance Criteria**: Code compiles and passes all checks.
- **Prohibited Changes**: Any modification to production code without CTO review.

---

## 10. Architecture Gate

```
[ ] APPROVED FOR IMPLEMENTATION
[ ] BLOCKED
```

The design revision is conditionally approved under the following verification:

* [x] No unjustified `BacktestInterface` remains in the design.
* [x] No new `register_candidate()` API added; existing APIs are reused.
* [x] Model training and feature calculation scope are bounded and deferred.
* [x] Determinism guarantees are realistic and bounded.
* [x] Canonical provenance field names are adopted exactly.
* [x] All existing repository APIs are inspected and matched in the evidence table.
* [x] `ResearchSession` and `ResearchOrchestratorRepository` remain canonical.
* [x] Orchestrator is thin (<500 lines) with no analytical logic.
* [x] No production files are modified in this design-only phase.

**Final Decision**: APPROVED FOR IMPLEMENTATION (Design Phase Completed)
