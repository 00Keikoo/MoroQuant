"""Unit tests for Model Registry Service layer."""

import pytest
from datetime import datetime
from ml_service.research.model_registry.model_types import (
    Model,
    ModelVersion,
    ArtifactMetadata,
    EvaluationResult,
    PromotionRecord,
    ModelLifecycleState,
    CompositeFingerprint
)
from ml_service.research.model_registry.service import ModelRegistryService


def test_service_registration_and_retrieval():
    """Verify registration, retrieval, duplicate rejection, and invalid lookup in Service layer."""
    service = ModelRegistryService()
    now = datetime.now()

    # 1. Model family registration
    m = Model(model_id="BTCUSD", name="BTC Trend model", description="desc", created_at=now)
    assert not service.exists("BTCUSD")
    service.register_model(m)
    assert service.exists("BTCUSD")
    
    retrieved_m = service.get_model("BTCUSD")
    assert retrieved_m == m
    assert retrieved_m is not m  # Immutability check via deep copy

    # Duplicate rejection
    with pytest.raises(ValueError):
        service.register_model(m)

    # 2. Version registration
    fp = CompositeFingerprint(value="a" * 64)
    v = ModelVersion(
        model_version_id="BTCUSD_v1.0.0",
        model_id="BTCUSD",
        version="1.0.0",
        lifecycle_state=ModelLifecycleState.DRAFT,
        composite_fingerprint=fp,
        created_at=now
    )
    
    assert not service.exists("BTCUSD", version_id="BTCUSD_v1.0.0")
    service.register_version(v)
    assert service.exists("BTCUSD", version_id="BTCUSD_v1.0.0")
    
    retrieved_v = service.get_version("BTCUSD_v1.0.0")
    assert retrieved_v == v
    assert retrieved_v is not v  # Immutability check

    # Register version for non-existent model throws error
    v_bad = ModelVersion(
        model_version_id="ETHUSD_v1.0.0",
        model_id="ETHUSD",
        version="1.0.0",
        lifecycle_state=ModelLifecycleState.DRAFT,
        composite_fingerprint=fp,
        created_at=now
    )
    with pytest.raises(ValueError):
        service.register_version(v_bad)

    # 3. Artifact registration
    art = ArtifactMetadata(
        model_version_id="BTCUSD_v1.0.0",
        bundle_path="/storage/models/BTCUSD_v1.0.0",
        manifest_checksum="a" * 64,
        size_bytes=4096,
        permissions="444",
        is_frozen=True
    )
    service.register_artifact(art)
    assert service.get_artifact("BTCUSD_v1.0.0") == art

    # 4. Evaluation scorecard registration
    ev = EvaluationResult(
        model_version_id="BTCUSD_v1.0.0",
        sharpe_ratio=1.7,
        max_drawdown=-0.11,
        ece=0.03,
        brier_score=0.17,
        win_rate=0.54,
        profit_factor=1.4,
        sortino_ratio=1.9,
        trade_count=130,
        is_approved=False
    )
    service.register_evaluation(ev)
    assert service.get_evaluation("BTCUSD_v1.0.0") == ev

    # 5. Invalid lookup checks
    assert service.get_model("NON_EXISTENT") is None
    assert service.get_version("NON_EXISTENT") is None
    assert service.get_artifact("NON_EXISTENT") is None
    assert service.get_evaluation("NON_EXISTENT") is None


def test_service_listing_and_ordering():
    """Verify sorting and filtering listings."""
    service = ModelRegistryService()
    now = datetime.now()

    m1 = Model(model_id="ETHUSD", name="ETH", description="desc", created_at=now)
    m2 = Model(model_id="BTCUSD", name="BTC", description="desc", created_at=now)
    service.register_model(m1)
    service.register_model(m2)

    # Listing models should sort by ID
    models = service.list_models()
    assert models[0].model_id == "BTCUSD"
    assert models[1].model_id == "ETHUSD"

    # Register versions to check ordering
    fp1 = CompositeFingerprint(value="a" * 64)
    v1 = ModelVersion(
        model_version_id="BTCUSD_v1.0.0",
        model_id="BTCUSD",
        version="1.0.0",
        lifecycle_state=ModelLifecycleState.DRAFT,
        composite_fingerprint=fp1,
        created_at=now
    )
    fp2 = CompositeFingerprint(value="b" * 64)
    v2 = ModelVersion(
        model_version_id="BTCUSD_v0.9.0",
        model_id="BTCUSD",
        version="0.9.0",
        lifecycle_state=ModelLifecycleState.CANDIDATE,
        composite_fingerprint=fp2,
        created_at=now
    )
    
    service.register_version(v1)
    service.register_version(v2)

    versions = service.get_versions("BTCUSD")
    assert len(versions) == 2
    assert versions[0].version == "0.9.0"
    assert versions[1].version == "1.0.0"

    # Filtered listing
    drafts = service.list_versions(state=ModelLifecycleState.DRAFT)
    assert len(drafts) == 1
    assert drafts[0].model_version_id == "BTCUSD_v1.0.0"


def test_service_promotion_history_and_rollback():
    """Verify append-only promotion records and lifecycle state transitions."""
    service = ModelRegistryService()
    now = datetime.now()

    m = Model(model_id="BTCUSD", name="BTC", description="desc", created_at=now)
    service.register_model(m)

    fp = CompositeFingerprint(value="a" * 64)
    v = ModelVersion(
        model_version_id="BTCUSD_v1.0.0",
        model_id="BTCUSD",
        version="1.0.0",
        lifecycle_state=ModelLifecycleState.DRAFT,
        composite_fingerprint=fp,
        created_at=now
    )
    service.register_version(v)

    # Record first promotion DRAFT -> CANDIDATE
    promo1 = PromotionRecord(
        promotion_id="p-1",
        model_version_id="BTCUSD_v1.0.0",
        previous_state=ModelLifecycleState.DRAFT,
        new_state=ModelLifecycleState.CANDIDATE,
        promoted_by="user1",
        promoted_at=now,
        promotion_reason="Initial validation ready"
    )
    service.record_promotion(promo1)
    
    # State update on version
    assert service.get_version("BTCUSD_v1.0.0").lifecycle_state == ModelLifecycleState.CANDIDATE

    # Record second promotion CANDIDATE -> VALIDATED
    promo2 = PromotionRecord(
        promotion_id="p-2",
        model_version_id="BTCUSD_v1.0.0",
        previous_state=ModelLifecycleState.CANDIDATE,
        new_state=ModelLifecycleState.VALIDATED,
        promoted_by="auditor",
        promoted_at=now,
        promotion_reason="Quality gates passed"
    )
    service.record_promotion(promo2)
    assert service.get_version("BTCUSD_v1.0.0").lifecycle_state == ModelLifecycleState.VALIDATED

    # Verify history
    history = service.get_promotion_history("BTCUSD_v1.0.0")
    assert len(history) == 2
    assert history[0].promotion_id == "p-1"
    assert history[1].promotion_id == "p-2"

    # Append-only check: duplicate ID rejection
    with pytest.raises(ValueError):
        service.record_promotion(promo1)


def test_service_deletion_and_cascade():
    """Verify cascade deletion properties of ModelRegistryService."""
    service = ModelRegistryService()
    now = datetime.now()

    m = Model(model_id="BTCUSD", name="BTC", description="desc", created_at=now)
    service.register_model(m)

    fp = CompositeFingerprint(value="a" * 64)
    v = ModelVersion(
        model_version_id="BTCUSD_v1.0.0",
        model_id="BTCUSD",
        version="1.0.0",
        lifecycle_state=ModelLifecycleState.DRAFT,
        composite_fingerprint=fp,
        created_at=now
    )
    service.register_version(v)

    art = ArtifactMetadata(
        model_version_id="BTCUSD_v1.0.0",
        bundle_path="/storage/models/BTCUSD_v1.0.0",
        manifest_checksum="a" * 64,
        size_bytes=4096,
        permissions="444",
        is_frozen=True
    )
    service.register_artifact(art)

    # 1. Delete version specific
    assert service.exists("BTCUSD", version_id="BTCUSD_v1.0.0")
    assert service.get_artifact("BTCUSD_v1.0.0") is not None
    
    service.delete("BTCUSD", version_id="BTCUSD_v1.0.0")
    
    assert not service.exists("BTCUSD", version_id="BTCUSD_v1.0.0")
    assert service.get_artifact("BTCUSD_v1.0.0") is None

    # 2. Delete parent model cascade
    v2 = ModelVersion(
        model_version_id="BTCUSD_v2.0.0",
        model_id="BTCUSD",
        version="2.0.0",
        lifecycle_state=ModelLifecycleState.DRAFT,
        composite_fingerprint=fp,
        created_at=now
    )
    service.register_version(v2)
    art2 = ArtifactMetadata(
        model_version_id="BTCUSD_v2.0.0",
        bundle_path="/storage/models/BTCUSD_v2.0.0",
        manifest_checksum="a" * 64,
        size_bytes=4096,
        permissions="444",
        is_frozen=True
    )
    service.register_artifact(art2)
    
    assert service.exists("BTCUSD")
    service.delete("BTCUSD")
    assert not service.exists("BTCUSD")
    assert not service.exists("BTCUSD", version_id="BTCUSD_v2.0.0")
    assert service.get_artifact("BTCUSD_v2.0.0") is None

