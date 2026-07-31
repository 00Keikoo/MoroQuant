"""Unit tests for Model Registry Repository layer."""

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
from ml_service.research.model_registry.repository import (
    ModelRegistryRepository,
    ArtifactRepository,
    PromotionHistoryRepository
)


def test_model_registry_repository_models():
    """Verify Model operations in ModelRegistryRepository."""
    repo = ModelRegistryRepository()
    now = datetime.now()
    
    m = Model(model_id="BTCUSD", name="BTC model", description="desc", created_at=now)
    
    # save / get / exists
    assert not repo.model_exists("BTCUSD")
    repo.save_model(m)
    assert repo.model_exists("BTCUSD")
    
    retrieved = repo.get_model("BTCUSD")
    assert retrieved == m
    
    # Immutability preservation (Deep Copy)
    assert retrieved is not m
    
    # Duplicate rejection
    with pytest.raises(ValueError):
        repo.save_model(m)
        
    # Invalid lookup
    assert repo.get_model("NON_EXISTENT") is None
    
    # Delete model
    repo.delete_model("BTCUSD")
    assert not repo.model_exists("BTCUSD")
    assert repo.get_model("BTCUSD") is None


def test_model_registry_repository_versions():
    """Verify ModelVersion operations in ModelRegistryRepository."""
    repo = ModelRegistryRepository()
    now = datetime.now()
    
    # Prerequisite Model
    m = Model(model_id="BTCUSD", name="BTC", description="desc", created_at=now)
    repo.save_model(m)
    
    fp = CompositeFingerprint(value="a" * 64)
    v1 = ModelVersion(
        model_version_id="BTCUSD_v1.0.0",
        model_id="BTCUSD",
        version="1.0.0",
        lifecycle_state=ModelLifecycleState.DRAFT,
        composite_fingerprint=fp,
        created_at=now
    )
    
    # Save & get
    assert not repo.version_exists("BTCUSD_v1.0.0")
    repo.save_version(v1)
    assert repo.version_exists("BTCUSD_v1.0.0")
    
    # Duplicate ID rejection
    with pytest.raises(ValueError):
        repo.save_version(v1)
        
    # CompositeFingerprint uniqueness validation
    fp2 = CompositeFingerprint(value="a" * 64)  # Duplicate fingerprint value
    v2 = ModelVersion(
        model_version_id="BTCUSD_v2.0.0",
        model_id="BTCUSD",
        version="2.0.0",
        lifecycle_state=ModelLifecycleState.DRAFT,
        composite_fingerprint=fp2,
        created_at=now
    )
    with pytest.raises(ValueError) as exc:
        repo.save_version(v2)
    assert "composite fingerprint" in str(exc.value)

    # State update
    repo.update_version_state("BTCUSD_v1.0.0", ModelLifecycleState.VALIDATED)
    updated = repo.get_version("BTCUSD_v1.0.0")
    assert updated.lifecycle_state == ModelLifecycleState.VALIDATED
    
    # Filtering / Listing & Deterministic sorting
    fp_new = CompositeFingerprint(value="b" * 64)
    v_older = ModelVersion(
        model_version_id="BTCUSD_v0.9.0",
        model_id="BTCUSD",
        version="0.9.0",
        lifecycle_state=ModelLifecycleState.VALIDATED,
        composite_fingerprint=fp_new,
        created_at=now
    )
    repo.save_version(v_older)
    
    versions = repo.list_versions_by_model("BTCUSD")
    assert len(versions) == 2
    # Sorted: 0.9.0 then 1.0.0
    assert versions[0].version == "0.9.0"
    assert versions[1].version == "1.0.0"
    
    validated_versions = repo.list_versions_by_state(ModelLifecycleState.VALIDATED)
    assert len(validated_versions) == 2


def test_model_registry_repository_evaluations():
    """Verify EvaluationResult operations."""
    repo = ModelRegistryRepository()
    now = datetime.now()
    
    m = Model(model_id="BTCUSD", name="BTC", description="desc", created_at=now)
    repo.save_model(m)
    
    fp = CompositeFingerprint(value="a" * 64)
    v = ModelVersion(
        model_version_id="BTCUSD_v1.0.0",
        model_id="BTCUSD",
        version="1.0.0",
        lifecycle_state=ModelLifecycleState.DRAFT,
        composite_fingerprint=fp,
        created_at=now
    )
    repo.save_version(v)
    
    ev = EvaluationResult(
        model_version_id="BTCUSD_v1.0.0",
        sharpe_ratio=1.8,
        max_drawdown=-0.10,
        ece=0.02,
        brier_score=0.15,
        win_rate=0.55,
        profit_factor=1.5,
        sortino_ratio=2.0,
        trade_count=120,
        is_approved=False
    )
    
    assert not repo.evaluation_exists("BTCUSD_v1.0.0")
    repo.save_evaluation(ev)
    assert repo.evaluation_exists("BTCUSD_v1.0.0")
    
    retrieved = repo.get_evaluation("BTCUSD_v1.0.0")
    assert retrieved.sharpe_ratio == 1.8
    
    # Save evaluation for non-existent model version throws error
    ev_bad = EvaluationResult(
        model_version_id="NON_EXISTENT",
        sharpe_ratio=1.8,
        max_drawdown=-0.10,
        ece=0.02,
        brier_score=0.15,
        win_rate=0.55,
        profit_factor=1.5,
        sortino_ratio=2.0,
        trade_count=120,
        is_approved=False
    )
    with pytest.raises(ValueError):
        repo.save_evaluation(ev_bad)


def test_artifact_repository():
    """Verify ArtifactRepository operations."""
    repo = ArtifactRepository()
    
    art = ArtifactMetadata(
        model_version_id="BTCUSD_v1.0.0",
        bundle_path="/storage/models/BTCUSD_v1.0.0",
        manifest_checksum="a" * 64,
        size_bytes=2048,
        permissions="444",
        is_frozen=True
    )
    
    assert not repo.artifact_exists("BTCUSD_v1.0.0")
    repo.save_artifact(art)
    assert repo.artifact_exists("BTCUSD_v1.0.0")
    
    retrieved = repo.get_artifact("BTCUSD_v1.0.0")
    assert retrieved == art
    
    # Duplicate save rejection
    with pytest.raises(ValueError):
        repo.save_artifact(art)
        
    # Delete
    repo.delete_artifact("BTCUSD_v1.0.0")
    assert not repo.artifact_exists("BTCUSD_v1.0.0")


def test_promotion_history_repository():
    """Verify append-only behavior of PromotionHistoryRepository."""
    repo = PromotionHistoryRepository()
    now = datetime.now()
    
    rec = PromotionRecord(
        promotion_id="promo-1",
        model_version_id="BTCUSD_v1.0.0",
        previous_state=ModelLifecycleState.DRAFT,
        new_state=ModelLifecycleState.CANDIDATE,
        promoted_by="user1",
        promoted_at=now
    )
    
    repo.save_promotion_record(rec)
    
    # Duplicate ID rejection (append-only cannot overwrite)
    with pytest.raises(ValueError):
        repo.save_promotion_record(rec)
        
    records = repo.list_records_by_version("BTCUSD_v1.0.0")
    assert len(records) == 1
    assert records[0] == rec
