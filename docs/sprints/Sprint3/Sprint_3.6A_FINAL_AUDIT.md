# Sprint 3.6A Replay Truth Engine Remediation Audit Report

**Audit Date**: 2026-07-07  
**Auditor**: Antigravity AI  
**Status**: ❌ **CRITICAL FAILURES IDENTIFIED (REMEDIATION INCOMPLETE)**

---

## 1. Executive Summary

This audit assesses the Sprint 3.6A Replay Truth Engine remediation. While the core trade-signal matching bug has been structurally patched in the Replay Engine itself, the remediation is **incomplete** and introduces breaking changes that cause test suite failures and metrics mismatches in downstream modules. Additionally, major "hidden execution context" gaps prevent the system from operating as a scientifically valid reproduction engine.

---

## 2. Detailed Focus Area Audit

### 2.1 Trade-Signal Mapping
* **Status**: ⚠️ **Partially Verified (Mock Bug Identified)**
* **Details**:
  - The core mapping logic in [replay.py](file:///home/zafka/trade-dashboard/ml_service/research/replay_engine/replay.py#L31) was successfully corrected to map trades by `signal_id` instead of `trade_id`:
    ```python
    trade_map = {trade.get('signal_id'): trade for trade in snapshot.trades if trade.get('signal_id') is not None}
    ```
  - **Audit Finding**: In [test_decision_truth_integration.py](file:///home/zafka/trade-dashboard/tests/research/test_decision_truth_integration.py#L19) and [verify_decision_truth.py](file:///home/zafka/trade-dashboard/verify_decision_truth.py#L67), the mock trades in test snapshots are defined using `"id": "sig1"` instead of `"signal_id": "sig1"`. Because of this mismatch, the trade-signal mapping silently filters them out, meaning they are never matched to signals during testing. The tests only pass because they fail to assert execution status matching.

### 2.2 Replay Determinism
* **Status**: ✅ **Verified**
* **Details**:
  - The decision process relies on [DecisionEngine.decide](file:///home/zafka/trade-dashboard/ml_service/research/decision_truth/decision_engine.py#L40) which is a pure function.
  - All inputs (`Snapshot`) are immutable during the replay run.
  - Multiple runs on the same snapshot produce identical outputs, which is verified in unit and integration test blocks.

### 2.3 Survivorship Bias Removal
* **Status**: ✅ **Verified**
* **Details**:
  - The Replay Engine iterates over `snapshot.signals` rather than `snapshot.trades`, ensuring all generated decisions are evaluated regardless of execution.
  - **Acceptable Limitation**: Since the snapshot limits signal collection (`limit=10000`), older signals that resulted in trades might be dropped if the timeframe is too large, creating potential historical survivorship bias.

### 2.4 Metrics Correctness & Integration Failures
* **Status**: ❌ **CRITICAL FAIL (Downstream Breaking Change)**
* **Details**:
  - Replay metrics were updated to use `signal_reproduction_rate`, `execution_alignment_rate`, and `divergence_count`.
  - However, removing `consistency_score` from `ReplayResult` broke integration:
    1. **Experiment Engine Crash**: [experiment_engine/engine.py](file:///home/zafka/trade-dashboard/ml_service/research/experiment_engine/engine.py#L69) references `replay_result.consistency_score`, throwing `AttributeError`.
    2. **Integration Test Failures**: Running the integration suite fails 4 tests due to this missing attribute.
    3. **Registry & Storage Incompatibility**: [registry.py](file:///home/zafka/trade-dashboard/ml_service/research/experiment_registry/registry.py#L35) and the SQLite schema in [storage.py](file:///home/zafka/trade-dashboard/ml_service/research/experiment_registry/storage.py#L50) still expect `consistency_score` for experiment history tracking.

### 2.5 Hidden Execution Context Missing
* **Status**: ❌ **CRITICAL FAIL**
* **Details**:
  - **Omitted Repository Fields**: [SignalRepository](file:///home/zafka/trade-dashboard/ml_service/repositories/signal_repository.py#L50) does not select or map `prob_long`, `prob_short`, `prob_neutral`, or `regime` from the database. Consequently, the snapshot contains no probability data, causing all reconstructed decisions to default to `HOLD` (resulting in 100% `HOLD` decisions in verify runs).
  - **Ignored Regime Execution Policy**: The live/paper broker in [paper_broker.py](file:///home/zafka/trade-dashboard/ml_service/trading/paper_broker.py#L250) applies a `regime_execution_policy` which evaluates dynamic database state (`paper_positions` and `regime_blocks`). The Replay Engine cannot reconstruct these blocks/restrictions because this database state is not captured inside the snapshot.

---

## 3. Remediation Action Plan (Recommended)

1. **Restore `consistency_score` Compatibility**: Define `consistency_score` as a property or attribute on `ReplayResult` mapping to `signal_reproduction_rate` to maintain backwards compatibility.
2. **Update SignalRepository Queries**: Modify `SignalRepository` to retrieve probability and regime fields so they are populated in the snapshot.
3. **Fix Mock Data in Integration Tests**: Update test snapshot definitions to use `signal_id` instead of `id` in mock trades.
4. **Expose Execution Policy State**: Capture the state of `regime_blocks` and regime returns in `Snapshot` to allow deterministic execution policy replaying.
