import pytest
from dataclasses import FrozenInstanceError

from ml_service.research.models import FeatureSnapshot
from ml_service.research.feature_repository import FeatureRepository


def test_save_and_get():
    repo = FeatureRepository()
    snapshot = FeatureSnapshot(
        feature_dataset_id="FT_1.0.0",
        source_dataset_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="/storage/features/ft1.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:00:00Z",
    )
    
    saved = repo.save(snapshot)
    assert saved == snapshot
    
    retrieved = repo.get("FT_1.0.0")
    assert retrieved == snapshot
    assert retrieved is not snapshot  # deepcopy preservation


def test_duplicate_rejection():
    repo = FeatureRepository()
    snapshot1 = FeatureSnapshot(
        feature_dataset_id="FT_1.0.0",
        source_dataset_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="/storage/features/ft1.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:00:00Z",
    )
    repo.save(snapshot1)
    
    snapshot2 = FeatureSnapshot(
        feature_dataset_id="FT_1.0.0",
        source_dataset_id="DS_2.0.0",
        fingerprint="b" * 64,
        file_path="/storage/features/ft2.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:01:00Z",
    )
    
    with pytest.raises(ValueError):
        repo.save(snapshot2)


def test_exists():
    repo = FeatureRepository()
    snapshot = FeatureSnapshot(
        feature_dataset_id="FT_1.0.0",
        source_dataset_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="/storage/features/ft1.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:00:00Z",
    )
    
    assert not repo.exists("FT_1.0.0")
    repo.save(snapshot)
    assert repo.exists("FT_1.0.0")


def test_delete():
    repo = FeatureRepository()
    snapshot = FeatureSnapshot(
        feature_dataset_id="FT_1.0.0",
        source_dataset_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="/storage/features/ft1.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:00:00Z",
    )
    repo.save(snapshot)
    assert repo.exists("FT_1.0.0")
    
    repo.delete("FT_1.0.0")
    assert not repo.exists("FT_1.0.0")
    
    with pytest.raises(KeyError):
        repo.get("FT_1.0.0")


def test_list_ordering():
    repo = FeatureRepository()
    
    snapshot_b = FeatureSnapshot(
        feature_dataset_id="FT_2.0.0",
        source_dataset_id="DS_2.0.0",
        fingerprint="b" * 64,
        file_path="/storage/features/ft2.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:01:00Z",
    )
    snapshot_c = FeatureSnapshot(
        feature_dataset_id="FT_3.0.0",
        source_dataset_id="DS_3.0.0",
        fingerprint="c" * 64,
        file_path="/storage/features/ft3.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:02:00Z",
    )
    snapshot_a = FeatureSnapshot(
        feature_dataset_id="FT_1.0.0",
        source_dataset_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="/storage/features/ft1.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:00:00Z",
    )
    
    repo.save(snapshot_b)
    repo.save(snapshot_c)
    repo.save(snapshot_a)
    
    snapshots = repo.list()
    assert [s.feature_dataset_id for s in snapshots] == ["FT_1.0.0", "FT_2.0.0", "FT_3.0.0"]


def test_immutable_preservation():
    repo = FeatureRepository()
    snapshot = FeatureSnapshot(
        feature_dataset_id="FT_1.0.0",
        source_dataset_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="/storage/features/ft1.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:00:00Z",
    )
    repo.save(snapshot)
    retrieved = repo.get("FT_1.0.0")
    
    with pytest.raises(FrozenInstanceError):
        retrieved.is_frozen = False  # type: ignore


def test_invalid_lookup():
    repo = FeatureRepository()
    
    with pytest.raises(KeyError):
        repo.get("non_existent_ft")
        
    with pytest.raises(KeyError):
        repo.delete("non_existent_ft")
