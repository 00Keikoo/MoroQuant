import pytest
from dataclasses import FrozenInstanceError
import json
import hashlib
from ml_service.research.models import FeatureSnapshot
from ml_service.research.feature_snapshot import FeatureSnapshotManager
from ml_service.research.research_session import make_immutable

def test_feature_snapshot_creation():
    manager = FeatureSnapshotManager()
    feature_id = "FDS_1.2.3"
    source_id = "DS_1.0.0"
    fingerprint = "a" * 64
    file_path = "/storage/features/FDS_1.2.3.parquet"
    
    snapshot = manager.create_snapshot(
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
    retrieved = manager.get_snapshot(feature_id)
    assert retrieved == snapshot

def test_validation_success():
    manager = FeatureSnapshotManager()
    # Should not raise any error
    manager.create_snapshot(
        feature_dataset_id="FDS_0.0.1",
        source_dataset_id="DS_0.0.1",
        fingerprint="b" * 64,
        file_path="/storage/features/valid.parquet",
        created_at="2026-07-31T00:00:00Z"
    )

def test_validation_failure():
    manager = FeatureSnapshotManager()
    
    # Invalid feature version format
    with pytest.raises(ValueError):
        manager.create_snapshot(
            feature_dataset_id="INVALID_VERSION",
            source_dataset_id="DS_1.0.0",
            fingerprint="a" * 64,
            file_path="/storage/features/test.parquet"
        )

    # Invalid source version format
    with pytest.raises(ValueError):
        manager.create_snapshot(
            feature_dataset_id="FDS_1.0.0",
            source_dataset_id="INVALID_VERSION",
            fingerprint="a" * 64,
            file_path="/storage/features/test.parquet"
        )
        
    # Invalid fingerprint length
    with pytest.raises(ValueError):
        manager.create_snapshot(
            feature_dataset_id="FDS_1.0.0",
            source_dataset_id="DS_1.0.0",
            fingerprint="abc",
            file_path="/storage/features/test.parquet"
        )
        
    # Invalid fingerprint characters
    with pytest.raises(ValueError):
        manager.create_snapshot(
            feature_dataset_id="FDS_1.0.0",
            source_dataset_id="DS_1.0.0",
            fingerprint="g" * 64,
            file_path="/storage/features/test.parquet"
        )
        
    # Empty file path
    with pytest.raises(ValueError):
        manager.create_snapshot(
            feature_dataset_id="FDS_1.0.0",
            source_dataset_id="DS_1.0.0",
            fingerprint="a" * 64,
            file_path=""
        )

    # Invalid timestamp
    with pytest.raises(ValueError):
        manager.create_snapshot(
            feature_dataset_id="FDS_1.0.0",
            source_dataset_id="DS_1.0.0",
            fingerprint="a" * 64,
            file_path="/storage/features/test.parquet",
            created_at="invalid-date"
        )

    # Invalid type for is_frozen
    with pytest.raises(ValueError):
        manager.create_snapshot(
            feature_dataset_id="FDS_1.0.0",
            source_dataset_id="DS_1.0.0",
            fingerprint="a" * 64,
            file_path="/storage/features/test.parquet",
            is_frozen="not_a_bool"  # type: ignore
        )

def test_immutability():
    manager = FeatureSnapshotManager()
    snapshot = manager.create_snapshot(
        feature_dataset_id="FDS_1.0.0",
        source_dataset_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="/storage/features/test.parquet"
    )
    with pytest.raises(FrozenInstanceError):
        snapshot.is_frozen = False  # type: ignore

def test_canonical_serialization_and_to_dict():
    manager = FeatureSnapshotManager()
    snapshot = manager.create_snapshot(
        feature_dataset_id="FDS_1.0.0",
        source_dataset_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="/storage/features/test.parquet",
        created_at="2026-07-31T00:00:00Z"
    )
    
    # Test to_dict on manager
    snapshot_dict = manager.to_dict(snapshot)
    assert snapshot_dict["feature_dataset_id"] == "FDS_1.0.0"
    assert snapshot_dict["source_dataset_id"] == "DS_1.0.0"
    assert snapshot_dict["fingerprint"] == "a" * 64
    assert snapshot_dict["file_path"] == "/storage/features/test.parquet"
    assert snapshot_dict["is_frozen"] is True
    assert snapshot_dict["created_at"] == "2026-07-31T00:00:00Z"

    # Test to_dict validation
    with pytest.raises(ValueError):
        manager.to_dict("not_a_snapshot")  # type: ignore
    
    # Test canonical_json
    canonical = manager.canonical_json(snapshot_dict)
    data = json.loads(canonical)
    assert data["feature_dataset_id"] == "FDS_1.0.0"
    assert data["source_dataset_id"] == "DS_1.0.0"
    
    # Check deterministic sorting of JSON keys
    assert canonical == '{"created_at":"2026-07-31T00:00:00Z","feature_dataset_id":"FDS_1.0.0","file_path":"/storage/features/test.parquet","fingerprint":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","is_frozen":true,"source_dataset_id":"DS_1.0.0"}'

def test_hash_verification():
    manager = FeatureSnapshotManager()
    
    metadata = {
        "symbol": "BTCUSDT",
        "precision_check": 1.23456789123,
        "parameters": {
            "a": 10,
            "b": 2.0
        }
    }
    
    # Compute fingerprint using canonical JSON
    json_str = manager.canonical_json(metadata)
    expected_hash = hashlib.sha256(json_str.encode('utf-8')).hexdigest()
    
    snapshot = manager.create_snapshot(
        feature_dataset_id="FDS_1.0.0",
        source_dataset_id="DS_1.0.0",
        fingerprint=expected_hash,
        file_path="/storage/features/test.parquet"
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
    manager = FeatureSnapshotManager()
    
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
    
    # Verify canonical_json handles lists, dicts, floats deterministically
    json_1 = manager.canonical_json(data_1)
    json_2 = manager.canonical_json(data_2)
    assert json_1 == json_2

    # Verify make_immutable usage converts nested dicts/lists to sorted, immutable tuples
    immutable_data = make_immutable(data_1)
    assert isinstance(immutable_data, tuple)

def test_empty_and_default_values():
    manager = FeatureSnapshotManager()
    
    # Default is_frozen is True
    snapshot = manager.create_snapshot(
        feature_dataset_id="FDS_1.0.0",
        source_dataset_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="/storage/features/test.parquet"
    )
    assert snapshot.is_frozen is True
    assert snapshot.created_at is not None

    # Empty dictionary canonical serialization
    empty_canonical = manager.canonical_json({})
    assert empty_canonical == "{}"
