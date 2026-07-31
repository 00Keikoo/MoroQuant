import pytest
import hashlib
from dataclasses import FrozenInstanceError
from ml_service.research.models import FeatureSnapshot
from ml_service.research.feature_snapshot import FeatureSnapshotManager
from ml_service.research.feature_repository import FeatureRepository
from ml_service.research.feature_service import FeatureService

@pytest.fixture
def service():
    repository = FeatureRepository()
    snapshot_manager = FeatureSnapshotManager()
    return FeatureService(repository, snapshot_manager)

def test_feature_snapshot_creation(service):
    feature_id = "FDS_1.0.0"
    source_id = "DS_1.0.0"
    fingerprint = "a" * 64
    file_path = "/storage/features/FDS_1.0.0.parquet"
    
    snapshot = service.create_snapshot(
        feature_dataset_id=feature_id,
        source_dataset_id=source_id,
        fingerprint=fingerprint,
        file_path=file_path,
        is_frozen=True
    )
    
    assert snapshot.feature_dataset_id == feature_id
    assert snapshot.source_dataset_id == source_id
    assert snapshot.fingerprint == fingerprint
    assert snapshot.file_path == file_path
    assert snapshot.is_frozen is True
    assert snapshot.created_at != ""
    
    # Retrieve and verify
    retrieved = service.get_snapshot(feature_id)
    assert retrieved == snapshot
    assert service.has_snapshot(feature_id) is True

def test_duplicate_rejection(service):
    feature_id = "FDS_1.0.0"
    source_id = "DS_1.0.0"
    fingerprint = "a" * 64
    file_path = "/storage/features/FDS_1.0.0.parquet"
    
    service.create_snapshot(
        feature_dataset_id=feature_id,
        source_dataset_id=source_id,
        fingerprint=fingerprint,
        file_path=file_path
    )
    
    with pytest.raises(ValueError):
        service.create_snapshot(
            feature_dataset_id=feature_id,
            source_dataset_id=source_id,
            fingerprint=fingerprint,
            file_path=file_path
        )

def test_retrieval_and_invalid_lookup(service):
    with pytest.raises(KeyError):
        service.get_snapshot("FDS_9.9.9")
        
    assert service.has_snapshot("FDS_9.9.9") is False

def test_deletion(service):
    feature_id = "FDS_1.0.0"
    service.create_snapshot(
        feature_dataset_id=feature_id,
        source_dataset_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="/storage/features/FDS_1.0.0.parquet"
    )
    
    service.delete_snapshot(feature_id)
    assert service.has_snapshot(feature_id) is False
    with pytest.raises(KeyError):
        service.get_snapshot(feature_id)

def test_deterministic_ordering(service):
    service.create_snapshot("FDS_1.0.0", "DS_1.0.0", "a" * 64, "/path/1.parquet")
    service.create_snapshot("FDS_3.0.0", "DS_1.0.0", "c" * 64, "/path/3.parquet")
    service.create_snapshot("FDS_2.0.0", "DS_1.0.0", "b" * 64, "/path/2.parquet")
    
    snapshots = service.list_snapshots()
    assert len(snapshots) == 3
    assert [s.feature_dataset_id for s in snapshots] == ["FDS_1.0.0", "FDS_2.0.0", "FDS_3.0.0"]

def test_immutability_preservation(service):
    snapshot = service.create_snapshot("FDS_1.0.0", "DS_1.0.0", "a" * 64, "/path/1.parquet")
    with pytest.raises(FrozenInstanceError):
        snapshot.is_frozen = False  # type: ignore

def test_hash_verification_utility(service):
    data = {"symbol": "BTCUSDT", "features": ["close_sma_10"]}
    json_str = service.canonical_json(data)
    expected_hash = hashlib.sha256(json_str.encode('utf-8')).hexdigest()
    
    snapshot = service.create_snapshot(
        feature_dataset_id="FDS_1.0.0",
        source_dataset_id="DS_1.0.0",
        fingerprint=expected_hash,
        file_path="/path/1.parquet"
    )
    
    assert service.verify_hash(snapshot, data) is True
    assert service.verify_hash(snapshot, "different_data") is False
