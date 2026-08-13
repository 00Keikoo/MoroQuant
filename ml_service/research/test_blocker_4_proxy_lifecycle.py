"""Regression tests for Blocker 4: Proxy Lifecycle State

Verifies that proxy models map to valid LifecycleState enum values and
are properly blocked from entering production crypto lifecycle.

Sprint 3.9D-14R
"""

import pytest
from ml_service.research.promotion_engine.models import PromotionStatus, PromotionScore
from ml_service.research.promotion_engine.policy import PromotionPolicy
from ml_service.research.model_identity.models import ModelIdentity
from ml_service.research.model_lifecycle.models import ModelLifecycleRecord, LifecycleState
from datetime import datetime, UTC


def test_proxy_proposes_valid_lifecycle_state():
    """Verify proxy promotion proposes valid LifecycleState enum value."""
    policy = PromotionPolicy()

    proxy_identity = ModelIdentity(
        artifact_path="/models/proxy_es.pkl",
        symbol="ES",
        timeframe="1h",
        model_type="xgboost",
        asset_class="PROXY",
        feature_count=10,
        feature_fingerprint="abc123",
        trained_at="2024-01-01T00:00:00Z",
        validation_available=True,
        calibration_available=True,
        sample_count=1000,
        lifecycle_status="VALIDATED"
    )

    lifecycle_record = ModelLifecycleRecord(
        artifact_path=proxy_identity.artifact_path,
        symbol=proxy_identity.symbol,
        asset_class=proxy_identity.asset_class,
        current_state=LifecycleState.VALIDATED,
        previous_state=LifecycleState.DISCOVERED,
        reason="test",
        timestamp=datetime.now(UTC).isoformat().replace('+00:00', 'Z')
    )

    # Total = 1.0*0.30 + 1.0*0.20 + 0.4*0.30 + 1.0*0.20 = 0.82
    score = PromotionScore(
        model_id=proxy_identity.artifact_path,
        validation_score=1.0,
        calibration_score=1.0,
        lifecycle_score=0.4,
        governance_score=1.0,
        total_score=0.82
    )

    proposed_state, status, reason_codes = policy.evaluate(
        proxy_identity, lifecycle_record, score
    )

    # Verify proposed_state is a valid LifecycleState enum value
    try:
        parsed_state = LifecycleState(proposed_state)
    except ValueError:
        pytest.fail(f"Proposed state '{proposed_state}' is not a valid LifecycleState enum value")

    assert status == PromotionStatus.APPROVED, "Proxy should be approved with sufficient score"
    assert parsed_state == LifecycleState.GOVERNANCE_READY, (
        "Proxy should map to GOVERNANCE_READY as terminal research state"
    )


def test_proxy_blocked_from_production():
    """Verify proxy models cannot reach PRODUCTION state."""
    policy = PromotionPolicy()

    proxy_identity = ModelIdentity(
        artifact_path="/models/proxy_es.pkl",
        symbol="ES",
        timeframe="1h",
        model_type="xgboost",
        asset_class="PROXY",
        feature_count=10,
        feature_fingerprint="abc123",
        trained_at="2024-01-01T00:00:00Z",
        validation_available=True,
        calibration_available=True,
        sample_count=1000,
        lifecycle_status="PRODUCTION"
    )

    lifecycle_record = ModelLifecycleRecord(
        artifact_path=proxy_identity.artifact_path,
        symbol=proxy_identity.symbol,
        asset_class=proxy_identity.asset_class,
        current_state=LifecycleState.PRODUCTION,
        previous_state=LifecycleState.APPROVED,
        reason="test",
        timestamp=datetime.now(UTC).isoformat().replace('+00:00', 'Z')
    )

    score = PromotionScore(
        model_id=proxy_identity.artifact_path,
        validation_score=1.0,
        calibration_score=1.0,
        lifecycle_score=1.0,
        governance_score=1.0,
        total_score=1.0
    )

    proposed_state, status, reason_codes = policy.evaluate(
        proxy_identity, lifecycle_record, score
    )

    assert status == PromotionStatus.BLOCKED, "Proxy in PRODUCTION must be BLOCKED"
    assert "PROXY_CANNOT_BE_PRODUCTION" in reason_codes, "Must flag production violation"


def test_crypto_can_reach_production():
    """Verify crypto models can reach PRODUCTION (contrast with proxy)."""
    policy = PromotionPolicy()

    crypto_identity = ModelIdentity(
        artifact_path="/models/btcusdt.pkl",
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
        lifecycle_status="APPROVED"
    )

    lifecycle_record = ModelLifecycleRecord(
        artifact_path=crypto_identity.artifact_path,
        symbol=crypto_identity.symbol,
        asset_class=crypto_identity.asset_class,
        current_state=LifecycleState.APPROVED,
        previous_state=LifecycleState.GOVERNANCE_READY,
        reason="test",
        timestamp=datetime.now(UTC).isoformat().replace('+00:00', 'Z')
    )

    score = PromotionScore(
        model_id=crypto_identity.artifact_path,
        validation_score=1.0,
        calibration_score=1.0,
        lifecycle_score=1.0,
        governance_score=1.0,
        total_score=1.0
    )

    proposed_state, status, reason_codes = policy.evaluate(
        crypto_identity, lifecycle_record, score
    )

    assert status == PromotionStatus.APPROVED, "Crypto should be approved for PRODUCTION"

    try:
        parsed_state = LifecycleState(proposed_state)
    except ValueError:
        pytest.fail(f"Proposed state '{proposed_state}' is not a valid LifecycleState")

    assert parsed_state == LifecycleState.PRODUCTION, "Crypto should progress to PRODUCTION"


def test_proxy_governance_ready_terminal():
    """Verify GOVERNANCE_READY is terminal state for proxy models."""
    policy = PromotionPolicy()

    proxy_identity = ModelIdentity(
        artifact_path="/models/proxy_nq.pkl",
        symbol="NQ",
        timeframe="1h",
        model_type="xgboost",
        asset_class="PROXY",
        feature_count=10,
        feature_fingerprint="abc123",
        trained_at="2024-01-01T00:00:00Z",
        validation_available=True,
        calibration_available=True,
        sample_count=1000,
        lifecycle_status="GOVERNANCE_READY"
    )

    lifecycle_record = ModelLifecycleRecord(
        artifact_path=proxy_identity.artifact_path,
        symbol=proxy_identity.symbol,
        asset_class=proxy_identity.asset_class,
        current_state=LifecycleState.GOVERNANCE_READY,
        previous_state=LifecycleState.VALIDATED,
        reason="test",
        timestamp=datetime.now(UTC).isoformat().replace('+00:00', 'Z')
    )

    # Total = 1.0*0.30 + 1.0*0.20 + 0.7*0.30 + 1.0*0.20 = 0.91
    score = PromotionScore(
        model_id=proxy_identity.artifact_path,
        validation_score=1.0,
        calibration_score=1.0,
        lifecycle_score=0.7,
        governance_score=1.0,
        total_score=0.91
    )

    proposed_state, status, reason_codes = policy.evaluate(
        proxy_identity, lifecycle_record, score
    )

    # Should stay at GOVERNANCE_READY, not progress further
    parsed_state = LifecycleState(proposed_state)
    assert parsed_state == LifecycleState.GOVERNANCE_READY, (
        "Proxy at GOVERNANCE_READY should stay there (terminal research state)"
    )
    assert status == PromotionStatus.APPROVED, "Should be approved as research model"
