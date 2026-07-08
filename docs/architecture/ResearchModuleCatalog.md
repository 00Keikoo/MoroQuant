# Research Module Catalog

This catalog outlines the purpose, interfaces, and dependencies of each research module.

---

## 1. Snapshot Engine
- **Purpose**: Creates immutable system state snapshots.
- **Inputs**: SQLite database connection/path.
- **Outputs**: `Snapshot` data object (serializable to JSON).
- **Dependencies**: `SignalRepository`, `TradeRepository`.
- **Public API**:
  - `capture_snapshot(symbol=None, db_path=None) -> Snapshot`

---

## 2. Replay Engine
- **Purpose**: Reconstructs decisions from snapshot data.
- **Inputs**: `Snapshot` data object, thresholds.
- **Outputs**: `ReplayResult` containing decisions list and parity rates.
- **Dependencies**: `DecisionEngine`, `ExecutionParityChecker`.
- **Public API**:
  - `run_replay(snapshot: Snapshot, threshold_long=0.5, threshold_short=0.5) -> ReplayResult`

---

## 3. Decision Truth Engine
- **Purpose**: Provides single-source-of-truth prediction class and threshold logic.
- **Inputs**: `DecisionContext` containing probabilities.
- **Outputs**: `DecisionResult` containing action (`LONG`, `SHORT`, `HOLD`) and confidence.
- **Dependencies**: None.
- **Public API**:
  - `DecisionEngine.decide(context: DecisionContext) -> DecisionResult`

---

## 4. Execution Parity
- **Purpose**: Replicates production rules (symbol conflict, cooldowns, sizing).
- **Inputs**: `Signal`, `reconstructed_decision`.
- **Outputs**: `ExecutionParityResult` with verdict.
- **Dependencies**: `Snapshot`.
- **Public API**:
  - `ExecutionParityChecker.check_execution(signal, decision) -> ExecutionParityResult`

---

## 5. Experiment Engine & Registry
- **Purpose**: Computes performance metrics for custom strategy thresholds.
- **Inputs**: `ReplayResult`, `Snapshot`, `StrategyConfig`.
- **Outputs**: `StrategyResult`.
- **Dependencies**: `DecisionEngine`.
- **Public API**:
  - `apply_strategy_config(replay_result, snapshot, config) -> StrategyResult`

---

## 6. Evaluation Engine
- **Purpose**: Score and rank strategies.
- **Inputs**: `StrategyResult`, `ExperimentResult`.
- **Outputs**: `StrategyScore`, `EvaluationResult`.
- **Dependencies**: `ExperimentEngine`.
- **Public API**:
  - `compute_strategy_score(result) -> StrategyScore`
  - `evaluate_experiment(experiment_result) -> EvaluationResult`

---

## 7. Research Integrity Layer
- **Purpose**: Guardrail checking data leaks, determinism, and survivorship bias.
- **Inputs**: `Snapshot`, `ReplayResult`, `EvaluationResult`.
- **Outputs**: `IntegrityReport` with risk levels and warnings list.
- **Dependencies**: `SnapshotEngine`, `ReplayEngine`.
- **Public API**:
  - `IntegrityService.generate_integrity_report(...) -> IntegrityReport`

---

## 8. Statistics Toolkit
- **Purpose**: Core math calculations.
- **Inputs**: Returns series (List of floats).
- **Outputs**: `DistributionStats`, `RiskStats`, `QualityStats`.
- **Dependencies**: `numpy`, `scipy`.
- **Public API**:
  - `compute_risk_stats(returns) -> RiskStats`
  - `compute_quality_stats(returns, trade_count) -> QualityStats`

---

## 9. Comparison Engine
- **Purpose**: Paired bootstrap and hypothesis tests.
- **Inputs**: Returns series A and B.
- **Outputs**: `BootstrapResult`, `HypothesisTestResult`.
- **Dependencies**: `scipy.stats`.
- **Public API**:
  - `run_bootstrap_analysis(returns_a, returns_b, ...) -> BootstrapResult`
  - `run_hypothesis_tests(returns_a, returns_b) -> HypothesisTestResult`

---

## 10. Validation Engine
- **Purpose**: Walk-forward and out-of-sample splits.
- **Inputs**: Timestamps list, evaluation function callback.
- **Outputs**: `ValidationReport`.
- **Dependencies**: None.
- **Public API**:
  - `ValidationEngine.validate_experiment(...) -> ValidationReport`
  - `ValidationEngine.validate_with_walk_forward(...) -> ValidationReport`
