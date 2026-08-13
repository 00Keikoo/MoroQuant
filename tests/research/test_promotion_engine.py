"""Tests for Promotion Decision Engine - Sprint 3.9D-8

Verify deterministic promotion decisions, immutable outputs, and ADR-024 compliance.
"""

import pytest
import json
from ml_service.research.promotion_engine import (
    PromotionStatus,
    PromotionScore,
    RegistryProposal,
    PromotionPolicy,
    PromotionEngine,
)
from ml_service.research.promotion_engine.scorer import PromotionScorer
from ml_service.research.model_identity.models import ModelIdentity
from ml_service.research.model_lifecycle.models import ModelLifecycleRecord, LifecycleState


def test_no_database_imports():
    """Verify no database imports in promotion_engine package."""
    import ml_service.research.promotion_engine.engine as engine_mod
    import ml_service.research.promotion_engine.policy as policy_mod
    import ml_service.research.promotion_engine.scorer as scorer_mod
    import ml_service.research.promotion_engine.models as models_mod
    import inspect

    for mod in [engine_mod, policy_mod, scorer_mod, models_mod]:
        source = inspect.getsource(mod)
        forbidden_imports = ["from sqlalchemy", "import sqlalchemy", "from database", "import database"]
        for term in forbidden_imports:
            assert term not in source.lower(), f"Found forbidden database import: {term}"


def test_no_execution_imports():
    """Verify no execution layer imports in promotion_engine package."""
    import ml_service.research.promotion_engine.engine as engine_mod
    import ml_service.research.promotion_engine.policy as policy_mod
    import ml_service.research.promotion_engine.scorer as scorer_mod
    import inspect

    for mod in [engine_mod, policy_mod, scorer_mod]:
        source = inspect.getsource(mod)
        forbidden = ["PortfolioService", "ExecutionSimulator", "ml_service.execution"]
        for term in forbidden:
            assert term not in source, f"Found forbidden execution import: {term}"


def test_promotion_score_immutable():
    """Verify PromotionScore is immutable."""
    score = PromotionScore(
        model_id="test_model",
        validation_score=1.0,
        calibration_score=1.0,
        lifecycle_score=1.0,
        governance_score=1.0,
        total_score=1.0,
    )

    with pytest.raises(AttributeError):
        score.total_score = 0.5


def test_promotion_score_validation():
    """Verify PromotionScore validates inputs."""
    with pytest.raises(ValueError, match="validation_score must be between 0.0 and 1.0"):
        PromotionScore(
            model_id="test",
            validation_score=1.5,
            calibration_score=0.5,
            lifecycle_score=0.5,
            governance_score=0.5,
            total_score=0.7,
        )


def test_promotion_score_weighted_calculation():
    """Verify PromotionScore enforces correct weighted sum."""
    with pytest.raises(ValueError, match="total_score .* does not match weighted sum"):
        PromotionScore(
            model_id="test",
            validation_score=1.0,
            calibration_score=1.0,
            lifecycle_score=1.0,
            governance_score=1.0,
            total_score=0.5,
        )


def test_scorer_deterministic():
    """Verify scorer produces deterministic results."""
    identity = ModelIdentity(
        artifact_path="models/test_model.pkl",
        symbol="BTCUSD",
        timeframe="1h",
        model_type="lightgbm",
        asset_class="CRYPTO",
        feature_count=10,
        feature_fingerprint="abc123",
        trained_at="2026-08-07T12:00:00",
        validation_available=True,
        calibration_available=True,
        sample_count=1000,
        lifecycle_status="VALIDATED",
    )

    lifecycle = ModelLifecycleRecord(
        artifact_path="models/test_model.pkl",
        symbol="BTCUSD",
        asset_class="CRYPTO",
        current_state=LifecycleState.VALIDATED,
        previous_state=LifecycleState.DISCOVERED,
        reason="Validation metrics available",
        timestamp="2026-08-07T12:00:00",
    )

    audit = {"governance_ready": True}

    scorer = PromotionScorer()
    score1 = scorer.calculate_score(identity, lifecycle, audit)
    score2 = scorer.calculate_score(identity, lifecycle, audit)

    assert score1 == score2
    assert score1.total_score == score2.total_score


def test_scorer_correct_weights():
    """Verify scorer applies correct weights (30/20/30/20)."""
    identity = ModelIdentity(
        artifact_path="models/test_model.pkl",
        symbol="BTCUSD",
        timeframe="1h",
        model_type="lightgbm",
        asset_class="CRYPTO",
        feature_count=10,
        feature_fingerprint="abc123",
        trained_at="2026-08-07T12:00:00",
        validation_available=True,
        calibration_available=True,
        sample_count=1000,
        lifecycle_status="VALIDATED",
    )

    lifecycle = ModelLifecycleRecord(
        artifact_path="models/test_model.pkl",
        symbol="BTCUSD",
        asset_class="CRYPTO",
        current_state=LifecycleState.VALIDATED,
        previous_state=LifecycleState.DISCOVERED,
        reason="Validation metrics available",
        timestamp="2026-08-07T12:00:00",
    )

    audit = {"governance_ready": True}

    scorer = PromotionScorer()
    score = scorer.calculate_score(identity, lifecycle, audit)

    expected = 1.0 * 0.30 + 1.0 * 0.20 + 0.4 * 0.30 + 1.0 * 0.20
    assert abs(score.total_score - expected) < 0.001


def test_crypto_validated_to_approved():
    """Verify crypto model can go from VALIDATED to APPROVED."""
    identity = ModelIdentity(
        artifact_path="models/btc_model.pkl",
        symbol="BTCUSD",
        timeframe="1h",
        model_type="lightgbm",
        asset_class="CRYPTO",
        feature_count=10,
        feature_fingerprint="abc123",
        trained_at="2026-08-07T12:00:00",
        validation_available=True,
        calibration_available=True,
        sample_count=1000,
        lifecycle_status="VALIDATED",
    )

    lifecycle = ModelLifecycleRecord(
        artifact_path="models/btc_model.pkl",
        symbol="BTCUSD",
        asset_class="CRYPTO",
        current_state=LifecycleState.VALIDATED,
        previous_state=LifecycleState.DISCOVERED,
        reason="Validation complete",
        timestamp="2026-08-07T12:00:00",
    )

    audit = {"governance_ready": True}

    engine = PromotionEngine()
    proposal = engine.evaluate(identity, lifecycle, audit)

    assert proposal.status == PromotionStatus.APPROVED
    assert proposal.proposed_state == LifecycleState.APPROVED.value
    assert "CRYPTO_VALIDATED_TO_APPROVED" in proposal.reason_codes


def test_crypto_approved_to_production():
    """Verify crypto model can go from APPROVED to PRODUCTION."""
    identity = ModelIdentity(
        artifact_path="models/btc_model.pkl",
        symbol="BTCUSD",
        timeframe="1h",
        model_type="lightgbm",
        asset_class="CRYPTO",
        feature_count=10,
        feature_fingerprint="abc123",
        trained_at="2026-08-07T12:00:00",
        validation_available=True,
        calibration_available=True,
        sample_count=1000,
        lifecycle_status="APPROVED",
    )

    lifecycle = ModelLifecycleRecord(
        artifact_path="models/btc_model.pkl",
        symbol="BTCUSD",
        asset_class="CRYPTO",
        current_state=LifecycleState.APPROVED,
        previous_state=LifecycleState.VALIDATED,
        reason="Approved for production",
        timestamp="2026-08-07T12:00:00",
    )

    audit = {"governance_ready": True}

    engine = PromotionEngine()
    proposal = engine.evaluate(identity, lifecycle, audit)

    assert proposal.status == PromotionStatus.APPROVED
    assert proposal.proposed_state == LifecycleState.PRODUCTION.value
    assert "CRYPTO_APPROVED_TO_PRODUCTION" in proposal.reason_codes


def test_proxy_blocked_from_production():
    """Verify proxy models cannot reach PRODUCTION."""
    identity = ModelIdentity(
        artifact_path="models/proxy_model.pkl",
        symbol="SPY",
        timeframe="1d",
        model_type="lightgbm",
        asset_class="PROXY",
        feature_count=10,
        feature_fingerprint="xyz789",
        trained_at="2026-08-07T12:00:00",
        validation_available=True,
        calibration_available=True,
        sample_count=1000,
        lifecycle_status="APPROVED",
    )

    lifecycle = ModelLifecycleRecord(
        artifact_path="models/proxy_model.pkl",
        symbol="SPY",
        asset_class="PROXY",
        current_state=LifecycleState.APPROVED,
        previous_state=LifecycleState.VALIDATED,
        reason="Approved",
        timestamp="2026-08-07T12:00:00",
    )

    audit = {"governance_ready": True}

    engine = PromotionEngine()
    proposal = engine.evaluate(identity, lifecycle, audit)

    assert proposal.status == PromotionStatus.BLOCKED
    assert proposal.proposed_state == LifecycleState.APPROVED.value
    assert "PROXY_BLOCKED_FROM_PRODUCTION" in proposal.reason_codes


def test_proxy_to_approved_research():
    """Verify proxy models can reach APPROVED_RESEARCH."""
    identity = ModelIdentity(
        artifact_path="models/proxy_model.pkl",
        symbol="SPY",
        timeframe="1d",
        model_type="lightgbm",
        asset_class="PROXY",
        feature_count=10,
        feature_fingerprint="xyz789",
        trained_at="2026-08-07T12:00:00",
        validation_available=True,
        calibration_available=True,
        sample_count=1000,
        lifecycle_status="VALIDATED",
    )

    lifecycle = ModelLifecycleRecord(
        artifact_path="models/proxy_model.pkl",
        symbol="SPY",
        asset_class="PROXY",
        current_state=LifecycleState.VALIDATED,
        previous_state=LifecycleState.DISCOVERED,
        reason="Validated",
        timestamp="2026-08-07T12:00:00",
    )

    audit = {"governance_ready": True}

    engine = PromotionEngine()
    proposal = engine.evaluate(identity, lifecycle, audit)

    assert proposal.status == PromotionStatus.APPROVED
    assert proposal.proposed_state == "GOVERNANCE_READY"
    assert "PROXY_APPROVED_FOR_RESEARCH" in proposal.reason_codes


def test_missing_validation_rejected():
    """Verify models without validation are rejected."""
    identity = ModelIdentity(
        artifact_path="models/incomplete_model.pkl",
        symbol="BTCUSD",
        timeframe="1h",
        model_type="lightgbm",
        asset_class="CRYPTO",
        feature_count=10,
        feature_fingerprint="abc123",
        trained_at="2026-08-07T12:00:00",
        validation_available=False,
        calibration_available=True,
        sample_count=1000,
        lifecycle_status="DISCOVERED",
    )

    lifecycle = ModelLifecycleRecord(
        artifact_path="models/incomplete_model.pkl",
        symbol="BTCUSD",
        asset_class="CRYPTO",
        current_state=LifecycleState.DISCOVERED,
        previous_state=None,
        reason="Initial discovery",
        timestamp="2026-08-07T12:00:00",
    )

    audit = {}

    engine = PromotionEngine()
    proposal = engine.evaluate(identity, lifecycle, audit)

    assert proposal.status == PromotionStatus.REJECTED
    assert "MISSING_VALIDATION" in proposal.reason_codes


def test_missing_calibration_rejected():
    """Verify models without calibration are rejected."""
    identity = ModelIdentity(
        artifact_path="models/incomplete_model.pkl",
        symbol="BTCUSD",
        timeframe="1h",
        model_type="lightgbm",
        asset_class="CRYPTO",
        feature_count=10,
        feature_fingerprint="abc123",
        trained_at="2026-08-07T12:00:00",
        validation_available=True,
        calibration_available=False,
        sample_count=1000,
        lifecycle_status="VALIDATED",
    )

    lifecycle = ModelLifecycleRecord(
        artifact_path="models/incomplete_model.pkl",
        symbol="BTCUSD",
        asset_class="CRYPTO",
        current_state=LifecycleState.VALIDATED,
        previous_state=LifecycleState.DISCOVERED,
        reason="Validation complete",
        timestamp="2026-08-07T12:00:00",
    )

    audit = {}

    engine = PromotionEngine()
    proposal = engine.evaluate(identity, lifecycle, audit)

    assert proposal.status == PromotionStatus.REJECTED
    assert "MISSING_CALIBRATION" in proposal.reason_codes


def test_reason_codes_deterministic():
    """Verify reason codes are deterministic and ordered."""
    identity = ModelIdentity(
        artifact_path="models/test_model.pkl",
        symbol="BTCUSD",
        timeframe="1h",
        model_type="lightgbm",
        asset_class="CRYPTO",
        feature_count=10,
        feature_fingerprint="abc123",
        trained_at="2026-08-07T12:00:00",
        validation_available=True,
        calibration_available=True,
        sample_count=1000,
        lifecycle_status="VALIDATED",
    )

    lifecycle = ModelLifecycleRecord(
        artifact_path="models/test_model.pkl",
        symbol="BTCUSD",
        asset_class="CRYPTO",
        current_state=LifecycleState.VALIDATED,
        previous_state=LifecycleState.DISCOVERED,
        reason="Validated",
        timestamp="2026-08-07T12:00:00",
    )

    audit = {"governance_ready": True}

    engine = PromotionEngine()
    proposal1 = engine.evaluate(identity, lifecycle, audit)
    proposal2 = engine.evaluate(identity, lifecycle, audit)

    assert proposal1.reason_codes == proposal2.reason_codes


def test_registry_proposal_immutable():
    """Verify RegistryProposal is immutable."""
    score = PromotionScore(
        model_id="test",
        validation_score=1.0,
        calibration_score=1.0,
        lifecycle_score=1.0,
        governance_score=1.0,
        total_score=1.0,
    )

    proposal = RegistryProposal(
        model_id="test",
        symbol="BTCUSD",
        asset_class="CRYPTO",
        current_state="VALIDATED",
        proposed_state="APPROVED",
        status=PromotionStatus.APPROVED,
        score=score,
        reason_codes=("TEST",),
    )

    with pytest.raises(AttributeError):
        proposal.status = PromotionStatus.REJECTED


def test_registry_proposal_json_serialization():
    """Verify RegistryProposal supports deterministic JSON serialization."""
    score = PromotionScore(
        model_id="test_model",
        validation_score=1.0,
        calibration_score=0.8,
        lifecycle_score=0.9,
        governance_score=1.0,
        total_score=0.93,
    )

    proposal = RegistryProposal(
        model_id="test_model",
        symbol="BTCUSD",
        asset_class="CRYPTO",
        current_state="VALIDATED",
        proposed_state="APPROVED",
        status=PromotionStatus.APPROVED,
        score=score,
        reason_codes=("CRYPTO_VALIDATED_TO_APPROVED",),
    )

    json_str = proposal.to_json()
    data = json.loads(json_str)

    assert data["model_id"] == "test_model"
    assert data["status"] == "APPROVED"
    assert data["score"]["total_score"] == 0.93

    reconstructed = RegistryProposal.from_dict(data)
    assert reconstructed == proposal


def test_engine_never_mutates_inputs():
    """Verify engine never mutates input objects."""
    identity = ModelIdentity(
        artifact_path="models/test_model.pkl",
        symbol="BTCUSD",
        timeframe="1h",
        model_type="lightgbm",
        asset_class="CRYPTO",
        feature_count=10,
        feature_fingerprint="abc123",
        trained_at="2026-08-07T12:00:00",
        validation_available=True,
        calibration_available=True,
        sample_count=1000,
        lifecycle_status="VALIDATED",
    )

    lifecycle = ModelLifecycleRecord(
        artifact_path="models/test_model.pkl",
        symbol="BTCUSD",
        asset_class="CRYPTO",
        current_state=LifecycleState.VALIDATED,
        previous_state=LifecycleState.DISCOVERED,
        reason="Validated",
        timestamp="2026-08-07T12:00:00",
    )

    audit = {"governance_ready": True}

    identity_before = (identity.artifact_path, identity.validation_available)
    lifecycle_before = (lifecycle.current_state, lifecycle.reason)
    audit_before = dict(audit)

    engine = PromotionEngine()
    engine.evaluate(identity, lifecycle, audit)

    assert (identity.artifact_path, identity.validation_available) == identity_before
    assert (lifecycle.current_state, lifecycle.reason) == lifecycle_before
    assert audit == audit_before
