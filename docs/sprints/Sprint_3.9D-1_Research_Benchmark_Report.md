# Sprint 3.9D-1 Research Benchmark Foundation Implementation Report

## Objective
Create a deterministic benchmark layer to compare `ResearchReport` outputs via composite scoring, adhering fully to ADR-024 principles.

---

## 1. Compliance Matrix (ADR-024)

| Rule / Requirement | Status | Verification / Design Detail |
| :--- | :---: | :--- |
| **Immutability** | **PASS** | `BenchmarkResult` is implemented as a frozen Python `dataclass`, raising `FrozenInstanceError` on modification attempts. |
| **Deterministic Serialization** | **PASS** | `to_dict` and `to_json` sort dict keys, scores, and metrics alphabetically by key, eliminating platform-dependent output variations. |
| **No DB / Simulation Coupling** | **PASS** | Pure domain layer. No references to SQLite, SQLAlchemy, or the execution/trading engine. Tested via import assertions. |
| **Deterministic Tie-Breaking** | **PASS** | Cohort comparisons with matching composite scores are resolved alphabetically by `experiment_id` to guarantee stable rankings. |

---

## 2. Composite Scoring Weights

The composite scoring system implements the following weights:
* **30% Sharpe Ratio**: Scaled to `[0.0, 1.0]` based on target benchmark `3.0`.
* **20% Sortino Ratio**: Scaled to `[0.0, 1.0]` based on target benchmark `3.0`.
* **20% Profit Factor**: Sigmoid-like scaling `1.0 - 1.0 / PF` for PF > 1.0, 0.0 for PF <= 1.0, and 1.0 for infinite PF.
* **15% Win Rate**: Raw win rate decimal fraction `[0.0, 1.0]`.
* **15% Drawdown Recovery**: Defined as `1.0 - max_drawdown` (giving higher scores for lower drawdowns).

---

## 3. Files Created

1. **`ml_service/research/benchmark/models.py`**
   - Implements the frozen `BenchmarkResult` dataclass.

2. **`ml_service/research/benchmark/interfaces.py`**
   - Declares the abstract `ResearchBenchmark` interface.

3. **`ml_service/research/benchmark/scoring.py`**
   - Implements the isolated absolute scoring function.

4. **`ml_service/research/benchmark/benchmark.py`**
   - Implements the `DefaultResearchBenchmark` compare and rank runner.

5. **`ml_service/research/benchmark/__init__.py`**
   - Exposes public boundaries of the benchmarking package.

6. **`tests/research/test_benchmark.py`**
   - Unit tests covering scoring correctness, ranking correctness under ties, and dependency isolation.

---

## 4. Test Execution Summary

The newly implemented test suite passes 100% cleanly:

```bash
tests/research/test_benchmark.py::test_benchmark_result_immutability PASSED
tests/research/test_benchmark.py::test_scoring_correctness PASSED
tests/research/test_benchmark.py::test_ranking_correctness_and_ties PASSED
tests/research/test_benchmark.py::test_empty_reports_error PASSED
tests/research/test_benchmark.py::test_dependency_isolation PASSED

========================= 5 passed in 0.81s =========================
```
