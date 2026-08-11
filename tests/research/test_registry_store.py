"""
Tests for Registry Store
Sprint 3.9D-6
"""

import json
import pytest
from pathlib import Path
from ml_service.research.model_identity import ModelIdentity
from ml_service.research.registry_snapshot import RegistrySnapshot, RegistrySnapshotBuilder
from ml_service.research.registry_store import (
    RegistrySnapshotRecord,
    JsonRegistrySnapshotStore,
    RegistryStoreService
)


@pytest.fixture
def temp_storage(tmp_path):
    return str(tmp_path / "test_snapshots")


@pytest.fixture
def sample_models():
    return (
        ModelIdentity(
            artifact_path="models/BTCUSDT_4h_xgboost_crypto.pkl",
            symbol="BTCUSDT",
            timeframe="4h",
            model_type="xgboost",
            asset_class="crypto",
            feature_count=42,
            feature_fingerprint="abc123",
            trained_at="2024-01-15T10:00:00Z",
            validation_available=True,
            calibration_available=True,
            sample_count=1000,
            lifecycle_status="production"
        ),
        ModelIdentity(
            artifact_path="models/ETHUSDT_1d_xgboost_crypto.pkl",
            symbol="ETHUSDT",
            timeframe="1d",
            model_type="xgboost",
            asset_class="crypto",
            feature_count=42,
            feature_fingerprint="def456",
            trained_at="2024-01-16T10:00:00Z",
            validation_available=True,
            calibration_available=False,
            sample_count=800,
            lifecycle_status="production"
        ),
    )


@pytest.fixture
def sample_snapshot(sample_models):
    builder = RegistrySnapshotBuilder()
    return builder.build(sample_models)


class TestRegistrySnapshotRecord:
    def test_immutable(self):
        record = RegistrySnapshotRecord(
            snapshot_id="test123",
            file_path="/path/to/snapshot.json",
            created_at="2024-01-15T10:00:00Z",
            model_count=5
        )

        with pytest.raises(AttributeError):
            record.snapshot_id = "modified"


class TestJsonRegistrySnapshotStore:
    def test_save_snapshot(self, temp_storage, sample_snapshot):
        store = JsonRegistrySnapshotStore(temp_storage)
        snapshot_id = store.save(sample_snapshot)

        assert snapshot_id == sample_snapshot.snapshot_id

        file_path = Path(temp_storage) / f"snapshot_{snapshot_id}.json"
        assert file_path.exists()

    def test_load_snapshot(self, temp_storage, sample_snapshot):
        store = JsonRegistrySnapshotStore(temp_storage)
        store.save(sample_snapshot)

        loaded = store.load(sample_snapshot.snapshot_id)

        assert loaded == sample_snapshot
        assert loaded.snapshot_id == sample_snapshot.snapshot_id
        assert loaded.total_models == sample_snapshot.total_models
        assert loaded.models == sample_snapshot.models

    def test_serialization_roundtrip(self, temp_storage, sample_snapshot):
        store = JsonRegistrySnapshotStore(temp_storage)
        store.save(sample_snapshot)

        loaded = store.load(sample_snapshot.snapshot_id)

        assert loaded.snapshot_id == sample_snapshot.snapshot_id
        assert loaded.created_at == sample_snapshot.created_at
        assert loaded.total_models == sample_snapshot.total_models
        assert loaded.summary == sample_snapshot.summary
        assert len(loaded.models) == len(sample_snapshot.models)

        for original, restored in zip(sample_snapshot.models, loaded.models):
            assert restored.artifact_path == original.artifact_path
            assert restored.symbol == original.symbol
            assert restored.timeframe == original.timeframe
            assert restored.model_type == original.model_type
            assert restored.asset_class == original.asset_class
            assert restored.feature_count == original.feature_count
            assert restored.feature_fingerprint == original.feature_fingerprint
            assert restored.trained_at == original.trained_at
            assert restored.validation_available == original.validation_available
            assert restored.calibration_available == original.calibration_available
            assert restored.sample_count == original.sample_count
            assert restored.lifecycle_status == original.lifecycle_status

    def test_load_nonexistent_snapshot(self, temp_storage):
        store = JsonRegistrySnapshotStore(temp_storage)

        with pytest.raises(FileNotFoundError):
            store.load("nonexistent_id")

    def test_list_snapshots_empty(self, temp_storage):
        store = JsonRegistrySnapshotStore(temp_storage)
        records = store.list_snapshots()

        assert records == ()

    def test_list_snapshots_multiple(self, temp_storage, sample_models):
        store = JsonRegistrySnapshotStore(temp_storage)
        builder = RegistrySnapshotBuilder()

        snapshot1 = builder.build(sample_models[:1])
        snapshot2 = builder.build(sample_models)

        store.save(snapshot1)
        store.save(snapshot2)

        records = store.list_snapshots()

        assert len(records) == 2
        assert all(isinstance(r, RegistrySnapshotRecord) for r in records)
        assert records[0].created_at <= records[1].created_at

    def test_list_snapshots_sorted_by_created_at(self, temp_storage, sample_models):
        store = JsonRegistrySnapshotStore(temp_storage)
        builder = RegistrySnapshotBuilder()

        snapshots = [builder.build(sample_models) for _ in range(3)]

        for snapshot in snapshots:
            store.save(snapshot)

        records = store.list_snapshots()

        for i in range(len(records) - 1):
            assert records[i].created_at <= records[i + 1].created_at

    def test_get_latest_empty(self, temp_storage):
        store = JsonRegistrySnapshotStore(temp_storage)
        latest = store.get_latest()

        assert latest is None

    def test_get_latest_snapshot(self, temp_storage, sample_models):
        store = JsonRegistrySnapshotStore(temp_storage)
        builder = RegistrySnapshotBuilder()

        snapshot1 = builder.build(sample_models[:1])
        snapshot2 = builder.build(sample_models)

        store.save(snapshot1)
        store.save(snapshot2)

        latest = store.get_latest()

        assert latest is not None
        assert latest.snapshot_id == snapshot2.snapshot_id

    def test_atomic_write(self, temp_storage, sample_snapshot):
        store = JsonRegistrySnapshotStore(temp_storage)
        store.save(sample_snapshot)

        temp_files = list(Path(temp_storage).glob("*.tmp"))
        assert len(temp_files) == 0

    def test_deterministic_json(self, temp_storage, sample_snapshot):
        store = JsonRegistrySnapshotStore(temp_storage)
        store.save(sample_snapshot)

        file_path = Path(temp_storage) / f"snapshot_{sample_snapshot.snapshot_id}.json"

        with open(file_path, 'r') as f:
            data = json.load(f)

        assert isinstance(data['models'], list)
        assert data['snapshot_id'] == sample_snapshot.snapshot_id

    def test_corrupted_file_handling(self, temp_storage):
        store = JsonRegistrySnapshotStore(temp_storage)

        corrupted_file = Path(temp_storage) / "snapshot_corrupted.json"
        corrupted_file.write_text("invalid json {{{")

        records = store.list_snapshots()

        assert records == ()


class TestRegistryStoreService:
    def test_create_snapshot(self, temp_storage, sample_models):
        store = JsonRegistrySnapshotStore(temp_storage)
        service = RegistryStoreService(store)

        snapshot = service.create_snapshot(sample_models)

        assert snapshot.total_models == len(sample_models)
        assert len(snapshot.models) == len(sample_models)

        loaded = store.load(snapshot.snapshot_id)
        assert loaded == snapshot

    def test_get_latest_snapshot_empty(self, temp_storage):
        store = JsonRegistrySnapshotStore(temp_storage)
        service = RegistryStoreService(store)

        latest = service.get_latest_snapshot()

        assert latest is None

    def test_get_latest_snapshot(self, temp_storage, sample_models):
        store = JsonRegistrySnapshotStore(temp_storage)
        service = RegistryStoreService(store)

        snapshot1 = service.create_snapshot(sample_models[:1])
        snapshot2 = service.create_snapshot(sample_models)

        latest = service.get_latest_snapshot()

        assert latest is not None
        assert latest.snapshot_id == snapshot2.snapshot_id

    def test_compare_with_latest_no_previous(self, temp_storage, sample_models):
        store = JsonRegistrySnapshotStore(temp_storage)
        service = RegistryStoreService(store)

        diff = service.compare_with_latest(sample_models)

        assert diff is None

    def test_compare_with_latest(self, temp_storage, sample_models):
        store = JsonRegistrySnapshotStore(temp_storage)
        service = RegistryStoreService(store)

        service.create_snapshot(sample_models[:1])

        diff = service.compare_with_latest(sample_models)

        assert diff is not None
        assert len(diff.added_models) == 1
        assert len(diff.removed_models) == 0


class TestNoDatabaseDependency:
    def test_no_sqlite_import(self):
        import ml_service.research.registry_store as module
        import inspect

        source_files = [
            inspect.getsource(module),
            inspect.getsource(module.JsonRegistrySnapshotStore),
            inspect.getsource(module.RegistryStoreService)
        ]

        for source in source_files:
            assert 'sqlite' not in source.lower()

    def test_no_execution_dependency(self):
        from ml_service.research.registry_store import RegistryStoreService
        import inspect

        source = inspect.getsource(RegistryStoreService)

        forbidden_terms = ['PortfolioService', 'ExecutionSimulator', 'database', 'db.']
        for term in forbidden_terms:
            assert term not in source


class TestImmutability:
    def test_snapshot_record_frozen(self):
        record = RegistrySnapshotRecord(
            snapshot_id="test",
            file_path="/path",
            created_at="2024-01-01T00:00:00Z",
            model_count=5
        )

        with pytest.raises(AttributeError):
            record.model_count = 10

    def test_loaded_snapshot_immutable(self, temp_storage, sample_snapshot):
        store = JsonRegistrySnapshotStore(temp_storage)
        store.save(sample_snapshot)

        loaded = store.load(sample_snapshot.snapshot_id)

        with pytest.raises(AttributeError):
            loaded.total_models = 999
