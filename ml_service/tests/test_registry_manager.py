"""Unit tests for Registry Manager."""

import pytest
from datetime import datetime
from ml_service.research.model_registry.model_types import (
    Model,
    ModelVersion,
    ArtifactMetadata,
    ModelLifecycleState,
    CompositeFingerprint,
    PromotionRecord
)
from ml_service.research.model_registry.service import ModelRegistryService
from ml_service.research.model_registry.registry_manager import RegistryManager


def test_registry_manager_resolution_and_versions():
    """Verify version resolution, latest version, production, and semantic bumps."""
    service = ModelRegistryService()
    manager = RegistryManager(service)
    now = datetime.now()

    # Prerequisite model family
    m = Model(model_id="BTCUSD", name="BTC", description="desc", created_at=now)
    service.register_model(m)

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
        model_version_id="BTCUSD_v2.0.0",
        model_id="BTCUSD",
        version="2.0.0",
        lifecycle_state=ModelLifecycleState.DRAFT,
        composite_fingerprint=fp2,
        created_at=now
    )
    service.register_version(v1)
    service.register_version(v2)

    # Latest version resolution
    latest = manager.resolve_latest_version("BTCUSD")
    assert latest.version == "2.0.0"

    # Semantic bumps
    assert manager.next_version("BTCUSD", "patch") == "2.0.1"
    assert manager.next_version("BTCUSD", "minor") == "2.1.0"
    assert manager.next_version("BTCUSD", "major") == "3.0.0"

    # Production resolution
    assert manager.resolve_production_version("BTCUSD") is None

    # Promote v2.0.0 step-by-step
    promo1 = PromotionRecord(
        promotion_id="promo-1",
        model_version_id="BTCUSD_v2.0.0",
        previous_state=ModelLifecycleState.DRAFT,
        new_state=ModelLifecycleState.CANDIDATE,
        promoted_by="admin",
        promoted_at=now
    )
    service.record_promotion(promo1)

    promo2 = PromotionRecord(
        promotion_id="promo-2",
        model_version_id="BTCUSD_v2.0.0",
        previous_state=ModelLifecycleState.CANDIDATE,
        new_state=ModelLifecycleState.VALIDATED,
        promoted_by="admin",
        promoted_at=now
    )
    service.record_promotion(promo2)

    promo3 = PromotionRecord(
        promotion_id="promo-3",
        model_version_id="BTCUSD_v2.0.0",
        previous_state=ModelLifecycleState.VALIDATED,
        new_state=ModelLifecycleState.PRODUCTION,
        promoted_by="admin",
        promoted_at=now
    )
    service.record_promotion(promo3)
    
    prod = manager.resolve_production_version("BTCUSD")
    assert prod is not None
    assert prod.model_version_id == "BTCUSD_v2.0.0"



def test_registry_manager_lineage_and_storage():
    """Verify lineage traversal and storage path resolution."""
    service = ModelRegistryService()
    manager = RegistryManager(service)
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

    # Artifact metadata for storage path
    art = ArtifactMetadata(
        model_version_id="BTCUSD_v1.0.0",
        bundle_path="/storage/models/BTCUSD_v1.0.0",
        manifest_checksum="a" * 64,
        size_bytes=1024,
        permissions="444",
        is_frozen=True
    )
    service.register_artifact(art)

    # Storage path resolution
    assert manager.resolve_storage_path("BTCUSD_v1.0.0") == "/storage/models/BTCUSD_v1.0.0"

    # Lineage registration and resolution
    lineage = {
        "snapshot_id": "snap-1",
        "dataset_id": "ds-1",
        "feature_dataset_id": "fds-1",
        "experiment_id": "exp-1",
        "run_id": "run-1"
    }
    manager.register_lineage("BTCUSD_v1.0.0", lineage)
    
    resolved_lineage = manager.resolve_lineage("BTCUSD_v1.0.0")
    assert resolved_lineage == lineage
    assert resolved_lineage is not lineage  # Immutability check


def test_registry_manager_invalid_lookups():
    """Verify invalid lookups are handled correctly."""
    service = ModelRegistryService()
    manager = RegistryManager(service)

    assert manager.resolve_model("NON_EXISTENT") is None
    assert manager.resolve_version("NON_EXISTENT") is None
    assert manager.resolve_latest_version("NON_EXISTENT") is None
    assert manager.resolve_production_version("NON_EXISTENT") is None
    assert manager.resolve_lineage("NON_EXISTENT") is None
    assert manager.resolve_storage_path("NON_EXISTENT") is None

    with pytest.raises(ValueError):
        manager.next_version("NON_EXISTENT", "minor")
