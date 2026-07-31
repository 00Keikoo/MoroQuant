import pytest
from dataclasses import FrozenInstanceError

from ml_service.research.models import DatasetSnapshot
from ml_service.research.dataset_repository import DatasetRepository


def test_save_and_get():
    repo = DatasetRepository()
    snapshot = DatasetSnapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="/storage/datasets/ds1.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:00:00Z",
    )
    
    saved = repo.save(snapshot)
    assert saved == snapshot
    
    retrieved = repo.get("DS_1.0.0")
    assert retrieved == snapshot
    assert retrieved is not snapshot  # deepcopy preservation


def test_duplicate_rejection():
    repo = DatasetRepository()
    snapshot1 = DatasetSnapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="/storage/datasets/ds1.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:00:00Z",
    )
    repo.save(snapshot1)
    
    snapshot2 = DatasetSnapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint="b" * 64,
        file_path="/storage/datasets/ds2.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:01:00Z",
    )
    
    with pytest.raises(ValueError):
        repo.save(snapshot2)


def test_exists():
    repo = DatasetRepository()
    snapshot = DatasetSnapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="/storage/datasets/ds1.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:00:00Z",
    )
    
    assert not repo.exists("DS_1.0.0")
    repo.save(snapshot)
    assert repo.exists("DS_1.0.0")


def test_delete():
    repo = DatasetRepository()
    snapshot = DatasetSnapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="/storage/datasets/ds1.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:00:00Z",
    )
    repo.save(snapshot)
    assert repo.exists("DS_1.0.0")
    
    repo.delete("DS_1.0.0")
    assert not repo.exists("DS_1.0.0")
    
    with pytest.raises(KeyError):
        repo.get("DS_1.0.0")


def test_list_ordering():
    repo = DatasetRepository()
    
    snapshot_b = DatasetSnapshot(
        dataset_version_id="DS_2.0.0",
        fingerprint="b" * 64,
        file_path="/storage/datasets/ds2.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:01:00Z",
    )
    snapshot_c = DatasetSnapshot(
        dataset_version_id="DS_3.0.0",
        fingerprint="c" * 64,
        file_path="/storage/datasets/ds3.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:02:00Z",
    )
    snapshot_a = DatasetSnapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="/storage/datasets/ds1.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:00:00Z",
    )
    
    repo.save(snapshot_b)
    repo.save(snapshot_c)
    repo.save(snapshot_a)
    
    snapshots = repo.list()
    assert [s.dataset_version_id for s in snapshots] == ["DS_1.0.0", "DS_2.0.0", "DS_3.0.0"]


def test_immutable_preservation():
    repo = DatasetRepository()
    snapshot = DatasetSnapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="/storage/datasets/ds1.parquet",
        is_frozen=True,
        created_at="2026-07-31T20:00:00Z",
    )
    repo.save(snapshot)
    retrieved = repo.get("DS_1.0.0")
    
    with pytest.raises(FrozenInstanceError):
        retrieved.is_frozen = False  # type: ignore


def test_invalid_lookup():
    repo = DatasetRepository()
    
    with pytest.raises(KeyError):
        repo.get("non_existent_ds")
        
    with pytest.raises(KeyError):
        repo.delete("non_existent_ds")
