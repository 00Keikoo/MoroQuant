import pytest
from dataclasses import FrozenInstanceError
from ml_service.research.models import DatasetSnapshot
from ml_service.research.dataset_snapshot import DatasetSnapshotManager
from ml_service.research.dataset_repository import DatasetRepository
from ml_service.research.dataset_service import DatasetService

@pytest.fixture
def service():
    repository = DatasetRepository()
    snapshot_manager = DatasetSnapshotManager()
    return DatasetService(repository, snapshot_manager)

def test_snapshot_creation(service):
    version_id = "DS_1.0.0"
    fingerprint = "a" * 64
    file_path = "/storage/datasets/DS_1.0.0.parquet"
    
    snapshot = service.create_snapshot(
        dataset_version_id=version_id,
        fingerprint=fingerprint,
        file_path=file_path,
        is_frozen=True
    )
    
    assert snapshot.dataset_version_id == version_id
    assert snapshot.fingerprint == fingerprint
    assert snapshot.file_path == file_path
    assert snapshot.is_frozen is True
    assert snapshot.created_at != ""
    
    # Retrieve and verify
    retrieved = service.get_snapshot(version_id)
    assert retrieved == snapshot
    assert service.has_snapshot(version_id) is True

def test_duplicate_rejection(service):
    version_id = "DS_1.0.0"
    fingerprint = "a" * 64
    file_path = "/storage/datasets/DS_1.0.0.parquet"
    
    service.create_snapshot(
        dataset_version_id=version_id,
        fingerprint=fingerprint,
        file_path=file_path
    )
    
    with pytest.raises(ValueError):
        service.create_snapshot(
            dataset_version_id=version_id,
            fingerprint=fingerprint,
            file_path=file_path
        )

def test_retrieval_and_invalid_lookup(service):
    with pytest.raises(KeyError):
        service.get_snapshot("DS_9.9.9")
        
    assert service.has_snapshot("DS_9.9.9") is False

def test_deletion(service):
    version_id = "DS_1.0.0"
    snapshot = service.create_snapshot(
        dataset_version_id=version_id,
        fingerprint="a" * 64,
        file_path="/storage/datasets/DS_1.0.0.parquet"
    )
    
    service.delete_snapshot(version_id)
    assert service.has_snapshot(version_id) is False
    with pytest.raises(KeyError):
        service.get_snapshot(version_id)

def test_deterministic_ordering(service):
    service.create_snapshot("DS_1.0.0", "a" * 64, "/path/1.parquet")
    service.create_snapshot("DS_3.0.0", "c" * 64, "/path/3.parquet")
    service.create_snapshot("DS_2.0.0", "b" * 64, "/path/2.parquet")
    
    snapshots = service.list_snapshots()
    assert len(snapshots) == 3
    assert [s.dataset_version_id for s in snapshots] == ["DS_1.0.0", "DS_2.0.0", "DS_3.0.0"]

def test_immutability_preservation(service):
    snapshot = service.create_snapshot("DS_1.0.0", "a" * 64, "/path/1.parquet")
    with pytest.raises(FrozenInstanceError):
        snapshot.is_frozen = False  # type: ignore

def test_hash_verification_utility(service):
    data = {"symbol": "BTCUSDT", "params": {"lr": 0.01}}
    expected_hash = service.calculate_canonical_hash(data)
    
    snapshot = service.create_snapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint=expected_hash,
        file_path="/path/1.parquet"
    )
    
    assert service.verify_hash(snapshot, data) is True
    assert service.verify_hash(snapshot, "different_data") is False
