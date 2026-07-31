import pytest
from dataclasses import FrozenInstanceError
import json
from ml_service.research.models import DatasetSnapshot
from ml_service.research.dataset_snapshot import DatasetSnapshotManager

def test_snapshot_creation():
    manager = DatasetSnapshotManager()
    version_id = "DS_1.2.3"
    fingerprint = "a" * 64
    file_path = "/storage/datasets/DS_1.2.3.parquet"
    
    snapshot = manager.create_snapshot(
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
    retrieved = manager.get_snapshot(version_id)
    assert retrieved == snapshot

def test_validation_success():
    manager = DatasetSnapshotManager()
    # Should not raise any error
    manager.create_snapshot(
        dataset_version_id="DS_0.0.1",
        fingerprint="b" * 64,
        file_path="/storage/datasets/valid.parquet",
        created_at="2026-07-31T00:00:00Z"
    )

def test_validation_failure():
    manager = DatasetSnapshotManager()
    
    # Invalid version format
    with pytest.raises(ValueError):
        manager.create_snapshot(
            dataset_version_id="INVALID_VERSION",
            fingerprint="a" * 64,
            file_path="/storage/datasets/test.parquet"
        )
        
    # Invalid fingerprint length
    with pytest.raises(ValueError):
        manager.create_snapshot(
            dataset_version_id="DS_1.0.0",
            fingerprint="abc",
            file_path="/storage/datasets/test.parquet"
        )
        
    # Invalid fingerprint characters
    with pytest.raises(ValueError):
        manager.create_snapshot(
            dataset_version_id="DS_1.0.0",
            fingerprint="g" * 64,
            file_path="/storage/datasets/test.parquet"
        )
        
    # Empty file path
    with pytest.raises(ValueError):
        manager.create_snapshot(
            dataset_version_id="DS_1.0.0",
            fingerprint="a" * 64,
            file_path=""
        )

    # Invalid timestamp
    with pytest.raises(ValueError):
        manager.create_snapshot(
            dataset_version_id="DS_1.0.0",
            fingerprint="a" * 64,
            file_path="/storage/datasets/test.parquet",
            created_at="invalid-date"
        )

def test_immutability():
    manager = DatasetSnapshotManager()
    snapshot = manager.create_snapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="/storage/datasets/test.parquet"
    )
    with pytest.raises(FrozenInstanceError):
        snapshot.is_frozen = False  # type: ignore

def test_deterministic_serialization():
    manager = DatasetSnapshotManager()
    snapshot = manager.create_snapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="/storage/datasets/test.parquet",
        created_at="2026-07-31T00:00:00Z"
    )
    
    serialized = manager.serialize(snapshot)
    data = json.loads(serialized)
    assert data["dataset_version_id"] == "DS_1.0.0"
    assert data["fingerprint"] == "a" * 64
    assert data["file_path"] == "/storage/datasets/test.parquet"
    assert data["is_frozen"] is True
    assert data["created_at"] == "2026-07-31T00:00:00Z"
    
    # Check deterministic sorting of JSON keys
    assert serialized == '{"created_at": "2026-07-31T00:00:00Z", "dataset_version_id": "DS_1.0.0", "file_path": "/storage/datasets/test.parquet", "fingerprint": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "is_frozen": true}'

def test_hash_verification():
    manager = DatasetSnapshotManager()
    
    # Calculate canonical hash from structured data
    metadata = {
        "symbol": "BTCUSDT",
        "precision_check": 1.23456789123,
        "parameters": {
            "a": 10,
            "b": 2.0
        }
    }
    
    expected_hash = manager.calculate_canonical_hash(metadata)
    
    snapshot = manager.create_snapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint=expected_hash,
        file_path="/storage/datasets/test.parquet"
    )
    
    # Verify hash using original dictionary
    assert manager.verify_hash(snapshot, metadata) is True
    
    # Verify hash using identical dictionary with different key ordering
    reordered_metadata = {
        "precision_check": 1.23456789123,
        "symbol": "BTCUSDT",
        "parameters": {
            "b": 2.0,
            "a": 10
        }
    }
    assert manager.verify_hash(snapshot, reordered_metadata) is True
    
    # Verify hash using a direct string match
    assert manager.verify_hash(snapshot, expected_hash) is True
    
    # Verify failure on mismatch
    assert manager.verify_hash(snapshot, "b" * 64) is False
    assert manager.verify_hash(snapshot, {"different": "data"}) is False

def test_nested_immutable_structures():
    # Make sure calculate_canonical_hash handles lists, dicts, floats deterministically
    manager = DatasetSnapshotManager()
    
    data_1 = {
        "float_val": 3.1415926535,
        "nested_list": [1, 2, {"key": 0.5}],
        "nested_dict": {"x": 1.0, "y": 2.0}
    }
    
    data_2 = {
        "nested_dict": {"y": 2.0, "x": 1.0},
        "nested_list": [1, 2, {"key": 0.5}],
        "float_val": 3.1415926535
    }
    
    hash_1 = manager.calculate_canonical_hash(data_1)
    hash_2 = manager.calculate_canonical_hash(data_2)
    assert hash_1 == hash_2
