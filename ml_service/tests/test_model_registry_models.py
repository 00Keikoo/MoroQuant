"""Unit tests for Model Registry Domain models."""

import pytest
from datetime import datetime
from dataclasses import FrozenInstanceError
from ml_service.research.model_registry.model_types import (
    ModelLifecycleState,
    PromotionState,
    ArtifactType,
    CompositeFingerprint,
    Model,
    ModelVersion,
    ArtifactMetadata,
    EvaluationResult,
    PromotionRecord,
    RegistryEvent,
    ModelRegistered,
    CandidateCreated,
    ValidationPassed,
    PromotionCompleted,
    RollbackCompleted,
    Archived
)


def test_composite_fingerprint():
    """Verify validation and calculation of composite fingerprint."""
    valid_hex = "a" * 64
    fingerprint = CompositeFingerprint(value=valid_hex)
    assert fingerprint.value == valid_hex

    with pytest.raises(ValueError):
        CompositeFingerprint(value="too_short")

    with pytest.raises(ValueError):
        CompositeFingerprint(value="z" * 64)

    calculated = CompositeFingerprint.calculate(
        binary_hash="b" * 64,
        hyperparameters={"max_depth": 5, "lr": 0.01},
        dataset_fingerprint="d" * 64,
        feature_fingerprint="f" * 64,
        git_commit="g" * 40,
        environment_info={"python": "3.10"},
        algorithm_version="1.0.0"
    )
    assert len(calculated.value) == 64
    assert calculated.value.isalnum()


def test_model_immutability_and_validation():
    """Verify model immutability, validation, serialization and sorting."""
    now = datetime.now()
    model = Model(
        model_id="BTCUSD_XGBoost",
        name="BTC Trend model",
        description="XGBoost strategy",
        created_at=now
    )

    # Immutability
    with pytest.raises(FrozenInstanceError):
        model.model_id = "change"

    # Validation
    model.validate()

    invalid_model = Model(
        model_id="Invalid Space Id",
        name="Name",
        description="Desc",
        created_at=now
    )
    with pytest.raises(ValueError):
        invalid_model.validate()

    # Serialization
    serialized = model.serialize()
    assert serialized["model_id"] == "BTCUSD_XGBoost"
    assert serialized["created_at"] == now.isoformat()

    # Sorting / Deterministic Ordering
    model_2 = Model(model_id="ETHUSD_XGBoost", name="ETH", description="ETH", created_at=now)
    assert model < model_2


def test_model_version():
    """Verify ModelVersion constraints."""
    now = datetime.now()
    fingerprint = CompositeFingerprint(value="a" * 64)
    
    mv = ModelVersion(
        model_version_id="BTCUSD_v1.0.0",
        model_id="BTCUSD",
        version="1.0.0",
        lifecycle_state=ModelLifecycleState.DRAFT,
        composite_fingerprint=fingerprint,
        created_at=now
    )

    mv.validate()
    
    # Invalid semver version format
    bad_semver = ModelVersion(
        model_version_id="BTCUSD_v1.0",
        model_id="BTCUSD",
        version="1.0",
        lifecycle_state=ModelLifecycleState.DRAFT,
        composite_fingerprint=fingerprint,
        created_at=now
    )
    with pytest.raises(ValueError):
        bad_semver.validate()

    # Mismatched model_version_id
    bad_id = ModelVersion(
        model_version_id="BTCUSD_v2.0.0",
        model_id="BTCUSD",
        version="1.0.0",
        lifecycle_state=ModelLifecycleState.DRAFT,
        composite_fingerprint=fingerprint,
        created_at=now
    )
    with pytest.raises(ValueError):
        bad_id.validate()

    # Ordering
    mv_older = ModelVersion(
        model_version_id="BTCUSD_v0.9.0",
        model_id="BTCUSD",
        version="0.9.0",
        lifecycle_state=ModelLifecycleState.DRAFT,
        composite_fingerprint=fingerprint,
        created_at=now
    )
    assert mv_older < mv


def test_artifact_metadata():
    """Verify ArtifactMetadata constraints."""
    art = ArtifactMetadata(
        model_version_id="BTCUSD_v1.0.0",
        bundle_path="/storage/models/BTCUSD_v1.0.0",
        manifest_checksum="a" * 64,
        size_bytes=1024,
        permissions="444",
        is_frozen=True
    )
    art.validate()

    # Invalid permissions
    bad_perm = ArtifactMetadata(
        model_version_id="BTCUSD_v1.0.0",
        bundle_path="/storage/models/BTCUSD_v1.0.0",
        manifest_checksum="a" * 64,
        size_bytes=1024,
        permissions="999",
        is_frozen=True
    )
    with pytest.raises(ValueError):
        bad_perm.validate()


def test_evaluation_result():
    """Verify EvaluationResult quality gates and bounds."""
    now = datetime.now()
    eval_res = EvaluationResult(
        model_version_id="BTCUSD_v1.0.0",
        sharpe_ratio=1.8,
        max_drawdown=-0.12,
        ece=0.03,
        brier_score=0.18,
        win_rate=0.55,
        profit_factor=1.6,
        sortino_ratio=2.1,
        trade_count=150,
        is_approved=True,
        approved_by="Auditor1",
        approved_at=now
    )
    eval_res.validate()

    # Invalid drawdown positive
    bad_dd = EvaluationResult(
        model_version_id="BTCUSD_v1.0.0",
        sharpe_ratio=1.8,
        max_drawdown=0.05,
        ece=0.03,
        brier_score=0.18,
        win_rate=0.55,
        profit_factor=1.6,
        sortino_ratio=2.1,
        trade_count=150,
        is_approved=False
    )
    with pytest.raises(ValueError):
        bad_dd.validate()


def test_promotion_record():
    """Verify state transitions and PromotionRecord validation."""
    now = datetime.now()
    
    # Valid transition
    rec = PromotionRecord(
        promotion_id="promo-1",
        model_version_id="BTCUSD_v1.0.0",
        previous_state=ModelLifecycleState.DRAFT,
        new_state=ModelLifecycleState.CANDIDATE,
        promoted_by="system",
        promoted_at=now
    )
    rec.validate()

    # Invalid transition (DRAFT -> PRODUCTION)
    bad_rec = PromotionRecord(
        promotion_id="promo-2",
        model_version_id="BTCUSD_v1.0.0",
        previous_state=ModelLifecycleState.DRAFT,
        new_state=ModelLifecycleState.PRODUCTION,
        promoted_by="system",
        promoted_at=now
    )
    with pytest.raises(ValueError):
        bad_rec.validate()


def test_registry_events():
    """Verify serialization and structure of domain events."""
    now = datetime.now()
    event = ModelRegistered(
        event_id="evt-1",
        timestamp=now,
        model_id="BTCUSD",
        symbol="BTCUSD",
        algorithm="xgboost"
    )
    serialized = event.serialize()
    assert serialized["event_id"] == "evt-1"
    assert serialized["event_type"] == "ModelRegistered"
    assert serialized["timestamp"] == now.isoformat()
    assert serialized["model_id"] == "BTCUSD"


def test_equality_and_hashability():
    """Verify hashability of frozen dataclasses."""
    now = datetime.now()
    model1 = Model(model_id="BTCUSD", name="BTC", description="desc", created_at=now)
    model2 = Model(model_id="BTCUSD", name="BTC", description="desc", created_at=now)
    
    assert model1 == model2
    assert hash(model1) == hash(model2)
