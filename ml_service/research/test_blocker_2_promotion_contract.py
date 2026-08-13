"""Regression tests for Blocker 2: Benchmark → Promotion Contract Mismatch

Verifies that the benchmark_to_audit_report adapter produces the correct
contract fields that PromotionScorer expects, particularly governance_ready.

Sprint 3.9D-14R
"""

import pytest
from ml_service.research.benchmark.models import BenchmarkResult
from ml_service.research.promotion_engine.benchmark_adapter import (
    benchmark_to_audit_report,
    evaluate_with_benchmark
)
from ml_service.research.promotion_engine.engine import PromotionEngine
from ml_service.research.promotion_engine.scorer import PromotionScorer
from ml_service.research.promotion_engine.policy import PromotionPolicy
from ml_service.research.model_identity.models import ModelIdentity
from ml_service.research.model_lifecycle.models import ModelLifecycleRecord, LifecycleState
from datetime import datetime, UTC


def test_adapter_emits_governance_ready():
    """Verify adapter emits governance_ready derived from lifecycle state, not hardcoded."""
    benchmark = BenchmarkResult(
        benchmark_id="test_benchmark",
        compared_experiments=("exp1", "exp2"),
        ranking=("exp1", "exp2"),
        winner="exp1",
        scores=(("exp1", 0.85), ("exp2", 0.75)),
        metrics=(("average_cohort_score", 0.80),)
    )

    # Test with GOVERNANCE_READY lifecycle state
    lifecycle_ready = ModelLifecycleRecord(
        artifact_path="/models/test.pkl",
        symbol="BTCUSDT",
        asset_class="CRYPTO",
        current_state=LifecycleState.GOVERNANCE_READY,
        previous_state=LifecycleState.VALIDATED,
        reason="test",
        timestamp=datetime.now(UTC).isoformat().replace('+00:00', 'Z')
    )

    audit_report_ready = benchmark_to_audit_report(benchmark, lifecycle_ready)

    assert "governance_ready" in audit_report_ready, "audit_report must contain governance_ready"
    assert audit_report_ready["governance_ready"] is True, "governance_ready must be True when lifecycle state is GOVERNANCE_READY"

    # Test with VALIDATED lifecycle state (not governance ready)
    lifecycle_validated = ModelLifecycleRecord(
        artifact_path="/models/test.pkl",
        symbol="BTCUSDT",
        asset_class="CRYPTO",
        current_state=LifecycleState.VALIDATED,
        previous_state=LifecycleState.DISCOVERED,
        reason="test",
        timestamp=datetime.now(UTC).isoformat().replace('+00:00', 'Z')
    )

    audit_report_not_ready = benchmark_to_audit_report(benchmark, lifecycle_validated)

    assert "governance_ready" in audit_report_not_ready, "audit_report must contain governance_ready"
    assert audit_report_not_ready["governance_ready"] is False, "governance_ready must be False when lifecycle state is not GOVERNANCE_READY"

    # Verify synthetic scores are NOT present in either case
    assert "governance_score" not in audit_report_ready, "governance_score should not be in audit_report"
    assert "validation_score" not in audit_report_ready, "validation_score should not be in audit_report"
    assert "calibration_score" not in audit_report_ready, "calibration_score should not be in audit_report"


def test_scorer_reads_governance_ready():
    """Verify PromotionScorer reads governance_ready from audit_report."""
    scorer = PromotionScorer()

    model_identity = ModelIdentity(
        artifact_path="/models/test.pkl",
        symbol="BTCUSDT",
        timeframe="1h",
        model_type="xgboost",
        asset_class="CRYPTO",
        feature_count=10,
        feature_fingerprint="abc123",
        trained_at="2024-01-01T00:00:00Z",
        validation_available=True,
        calibration_available=True,
        sample_count=1000,
        lifecycle_status="VALIDATED"
    )

    lifecycle_record = ModelLifecycleRecord(
        artifact_path=model_identity.artifact_path,
        symbol=model_identity.symbol,
        asset_class=model_identity.asset_class,
        current_state=LifecycleState.VALIDATED,
        previous_state=LifecycleState.DISCOVERED,
        reason="test",
        timestamp=datetime.now(UTC).isoformat().replace('+00:00', 'Z')
    )

    # Test with governance_ready=True
    audit_report_ready = {"governance_ready": True}
    score_ready = scorer.calculate_score(model_identity, lifecycle_record, audit_report_ready)
    assert score_ready.governance_score == 1.0, "governance_score should be 1.0 when governance_ready=True"

    # Test with governance_ready=False
    audit_report_not_ready = {"governance_ready": False}
    score_not_ready = scorer.calculate_score(model_identity, lifecycle_record, audit_report_not_ready)
    assert score_not_ready.governance_score == 0.0, "governance_score should be 0.0 when governance_ready=False"

    # Test with missing governance_ready (defaults to False)
    audit_report_missing = {}
    score_missing = scorer.calculate_score(model_identity, lifecycle_record, audit_report_missing)
    assert score_missing.governance_score == 0.0, "governance_score should default to 0.0 when governance_ready is missing"


def test_end_to_end_promotion_with_governance_ready():
    """Verify end-to-end flow: BenchmarkResult → audit_report → PromotionScorer → promotion decision."""
    benchmark = BenchmarkResult(
        benchmark_id="test_benchmark",
        compared_experiments=("exp1",),
        ranking=("exp1",),
        winner="exp1",
        scores=(("exp1", 0.85),),
        metrics=(("average_cohort_score", 0.85),)
    )

    model_identity = ModelIdentity(
        artifact_path="/models/test_crypto.pkl",
        symbol="BTCUSDT",
        timeframe="1h",
        model_type="xgboost",
        asset_class="CRYPTO",
        feature_count=10,
        feature_fingerprint="abc123",
        trained_at="2024-01-01T00:00:00Z",
        validation_available=True,
        calibration_available=True,
        sample_count=1000,
        lifecycle_status="GOVERNANCE_READY"
    )

    lifecycle_record = ModelLifecycleRecord(
        artifact_path=model_identity.artifact_path,
        symbol=model_identity.symbol,
        asset_class=model_identity.asset_class,
        current_state=LifecycleState.GOVERNANCE_READY,
        previous_state=LifecycleState.VALIDATED,
        reason="test",
        timestamp=datetime.now(UTC).isoformat().replace('+00:00', 'Z')
    )

    engine = PromotionEngine(
        scorer=PromotionScorer(),
        policy=PromotionPolicy()
    )

    proposal = evaluate_with_benchmark(
        engine=engine,
        benchmark=benchmark,
        model_identity=model_identity,
        lifecycle_record=lifecycle_record
    )

    # Verify the candidate passes with proper governance readiness from lifecycle state
    # With validation + calibration + governance_ready + lifecycle GOVERNANCE_READY, total_score should be high enough
    assert proposal.score.total_score >= PromotionPolicy.MINIMUM_SCORE_THRESHOLD, (
        f"Candidate should pass when lifecycle state is GOVERNANCE_READY, "
        f"but total_score={proposal.score.total_score} < {PromotionPolicy.MINIMUM_SCORE_THRESHOLD}"
    )


def test_validation_calibration_from_model_identity():
    """Verify validation/calibration scores come from ModelIdentity, not audit_report."""
    scorer = PromotionScorer()

    # Model with validation but no calibration
    model_partial = ModelIdentity(
        artifact_path="/models/test.pkl",
        symbol="BTCUSDT",
        timeframe="1h",
        model_type="xgboost",
        asset_class="CRYPTO",
        feature_count=10,
        feature_fingerprint="abc123",
        trained_at="2024-01-01T00:00:00Z",
        validation_available=True,
        calibration_available=False,
        sample_count=1000,
        lifecycle_status="VALIDATED"
    )

    lifecycle_record = ModelLifecycleRecord(
        artifact_path=model_partial.artifact_path,
        symbol=model_partial.symbol,
        asset_class=model_partial.asset_class,
        current_state=LifecycleState.VALIDATED,
        previous_state=LifecycleState.DISCOVERED,
        reason="test",
        timestamp=datetime.now(UTC).isoformat().replace('+00:00', 'Z')
    )

    # audit_report only has governance_ready
    audit_report = {"governance_ready": True}

    score = scorer.calculate_score(model_partial, lifecycle_record, audit_report)

    # Verify scores come from ModelIdentity properties, not audit_report
    assert score.validation_score == 1.0, "validation_score should come from model_identity.validation_available"
    assert score.calibration_score == 0.0, "calibration_score should come from model_identity.calibration_available"
    assert score.governance_score == 1.0, "governance_score should come from audit_report.governance_ready"


def test_benchmark_winner_does_not_automatically_become_governance_ready():
    """Regression test: Benchmark winners do NOT automatically become governance-ready.

    This test proves that:
    1. Winning a benchmark does not automatically grant governance readiness
    2. Governance readiness comes from the canonical lifecycle state, not benchmark performance
    3. Promotion behavior remains correct when governance readiness is false vs true

    Sprint 3.9D-14R Blocker 3 fix verification.
    """
    # Create a benchmark result where exp1 is the winner
    benchmark = BenchmarkResult(
        benchmark_id="regression_benchmark",
        compared_experiments=("exp1", "exp2", "exp3"),
        ranking=("exp1", "exp2", "exp3"),
        winner="exp1",
        scores=(("exp1", 0.95), ("exp2", 0.80), ("exp3", 0.70)),
        metrics=(("average_cohort_score", 0.82), ("highest_score", 0.95))
    )

    model_identity = ModelIdentity(
        artifact_path="/models/winner.pkl",
        symbol="BTCUSDT",
        timeframe="1h",
        model_type="xgboost",
        asset_class="CRYPTO",
        feature_count=10,
        feature_fingerprint="abc123",
        trained_at="2024-01-01T00:00:00Z",
        validation_available=True,
        calibration_available=True,
        sample_count=1000,
        lifecycle_status="VALIDATED"
    )

    # Case 1: Model is VALIDATED (has calibration but not governance-ready)
    lifecycle_validated = ModelLifecycleRecord(
        artifact_path=model_identity.artifact_path,
        symbol=model_identity.symbol,
        asset_class=model_identity.asset_class,
        current_state=LifecycleState.VALIDATED,
        previous_state=LifecycleState.DISCOVERED,
        reason="validation complete",
        timestamp=datetime.now(UTC).isoformat().replace('+00:00', 'Z')
    )

    audit_report_validated = benchmark_to_audit_report(benchmark, lifecycle_validated)

    # CRITICAL: Benchmark winner should NOT be governance-ready if lifecycle state is not GOVERNANCE_READY
    assert audit_report_validated["governance_ready"] is False, (
        "Benchmark winner must NOT be automatically governance-ready when lifecycle state is VALIDATED"
    )
    assert audit_report_validated["benchmark_winner"] == "exp1", "Should still record the benchmark winner"
    assert audit_report_validated["benchmark_score"] == 0.95, "Should still record the benchmark score"

    # Case 2: Same model reaches GOVERNANCE_READY lifecycle state
    lifecycle_governance_ready = ModelLifecycleRecord(
        artifact_path=model_identity.artifact_path,
        symbol=model_identity.symbol,
        asset_class=model_identity.asset_class,
        current_state=LifecycleState.GOVERNANCE_READY,
        previous_state=LifecycleState.VALIDATED,
        reason="calibration complete",
        timestamp=datetime.now(UTC).isoformat().replace('+00:00', 'Z')
    )

    audit_report_ready = benchmark_to_audit_report(benchmark, lifecycle_governance_ready)

    # Now governance_ready should be True because lifecycle state advanced
    assert audit_report_ready["governance_ready"] is True, (
        "governance_ready should be True when lifecycle state is GOVERNANCE_READY"
    )

    # Case 3: Verify promotion scoring respects the governance readiness difference
    scorer = PromotionScorer()

    score_not_ready = scorer.calculate_score(model_identity, lifecycle_validated, audit_report_validated)
    score_ready = scorer.calculate_score(model_identity, lifecycle_governance_ready, audit_report_ready)

    # Both have same validation/calibration from ModelIdentity
    assert score_not_ready.validation_score == score_ready.validation_score == 1.0
    assert score_not_ready.calibration_score == score_ready.calibration_score == 1.0

    # Governance score differs based on actual lifecycle state
    assert score_not_ready.governance_score == 0.0, "governance_score should be 0.0 when not governance-ready"
    assert score_ready.governance_score == 1.0, "governance_score should be 1.0 when governance-ready"

    # Total score reflects both governance readiness (20%) and lifecycle state (30%) impact
    # VALIDATED lifecycle → 0.4, GOVERNANCE_READY lifecycle → 0.7, difference = 0.3
    # Governance readiness: False → 0.0, True → 1.0, difference = 1.0
    governance_weight = PromotionScorer.GOVERNANCE_WEIGHT
    lifecycle_weight = PromotionScorer.LIFECYCLE_WEIGHT
    expected_score_diff = (governance_weight * 1.0) + (lifecycle_weight * 0.3)  # 0.20 + 0.09 = 0.29
    actual_score_diff = score_ready.total_score - score_not_ready.total_score

    assert abs(actual_score_diff - expected_score_diff) < 0.001, (
        f"Total score difference should reflect governance (20%) and lifecycle (30%) weight, "
        f"expected={expected_score_diff}, actual={actual_score_diff}"
    )

    # Case 4: Verify promotion decision respects governance readiness
    engine = PromotionEngine()

    proposal_not_ready = engine.evaluate(model_identity, lifecycle_validated, audit_report_validated)
    proposal_ready = engine.evaluate(model_identity, lifecycle_governance_ready, audit_report_ready)

    # Both should have valid proposals but potentially different outcomes
    assert proposal_not_ready.model_id == proposal_ready.model_id == model_identity.artifact_path

    # The governance-ready model should have higher total score
    assert proposal_ready.score.total_score > proposal_not_ready.score.total_score, (
        "Governance-ready model should have higher promotion score"
    )
