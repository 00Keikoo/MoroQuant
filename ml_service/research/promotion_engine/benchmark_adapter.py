"""Adapter for connecting BenchmarkResult to PromotionEngine.

Pure-functional adapter that converts BenchmarkResult into audit_report format
for consumption by PromotionEngine.

ADR-024 compliant: stateless, deterministic, no side effects.
"""

from typing import Dict, Any

from ml_service.research.benchmark.models import BenchmarkResult
from ml_service.research.promotion_engine.models import RegistryProposal
from ml_service.research.promotion_engine.engine import PromotionEngine
from ml_service.research.model_identity.models import ModelIdentity
from ml_service.research.model_lifecycle.models import ModelLifecycleRecord


def benchmark_to_audit_report(
    benchmark: BenchmarkResult,
    lifecycle_record: ModelLifecycleRecord
) -> Dict[str, Any]:
    """Convert BenchmarkResult to audit_report format.

    Extracts benchmark evidence and formats it for PromotionEngine consumption.
    Governance readiness is derived from the canonical lifecycle state, not benchmark performance.

    Args:
        benchmark: BenchmarkResult from research benchmark
        lifecycle_record: Current lifecycle state (canonical source of governance readiness)

    Returns:
        Dictionary containing benchmark evidence for audit
    """
    from ml_service.research.model_lifecycle.models import LifecycleState

    scores_dict = dict(benchmark.scores)
    metrics_dict = dict(benchmark.metrics)

    governance_ready = lifecycle_record.current_state == LifecycleState.GOVERNANCE_READY

    return {
        "benchmark_id": benchmark.benchmark_id,
        "benchmark_winner": benchmark.winner,
        "benchmark_rank": list(benchmark.ranking).index(benchmark.winner) + 1 if benchmark.winner in benchmark.ranking else -1,
        "benchmark_score": scores_dict.get(benchmark.winner, 0.0),
        "cohort_size": len(benchmark.compared_experiments),
        "cohort_average_score": metrics_dict.get("average_cohort_score", 0.0),
        "cohort_highest_score": metrics_dict.get("highest_score", 0.0),
        "governance_ready": governance_ready
    }


def evaluate_with_benchmark(
    engine: PromotionEngine,
    benchmark: BenchmarkResult,
    model_identity: ModelIdentity,
    lifecycle_record: ModelLifecycleRecord
) -> RegistryProposal:
    """Evaluate model candidate using benchmark evidence.

    Connects BenchmarkResult to PromotionEngine by converting benchmark
    data into audit_report format.

    Args:
        engine: PromotionEngine instance
        benchmark: BenchmarkResult containing experiment rankings
        model_identity: Model identity from scanner
        lifecycle_record: Current lifecycle state

    Returns:
        RegistryProposal with promotion decision
    """
    audit_report = benchmark_to_audit_report(benchmark, lifecycle_record)

    return engine.evaluate(
        model_identity=model_identity,
        lifecycle_record=lifecycle_record,
        audit_report=audit_report
    )
