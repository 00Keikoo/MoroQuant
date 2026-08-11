"""
Test Registry Snapshot Engine
Sprint 3.9D-5
"""

import pytest
from ml_service.research.model_identity import ModelIdentity
from ml_service.research.registry_snapshot import (
    RegistrySnapshotBuilder,
    RegistryDiffEngine,
    RegistrySnapshot,
    RegistryDiff,
)


def create_model_identity(
    artifact_path: str,
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    model_type: str = "xgb",
    asset_class: str = "crypto",
    feature_count: int = 10,
    feature_fingerprint: str = "fp123",
    trained_at: str = "2024-01-01T00:00:00Z",
    validation_available: bool = True,
    calibration_available: bool = False,
    sample_count: int = 1000,
    lifecycle_status: str = "candidate",
) -> ModelIdentity:
    return ModelIdentity(
        artifact_path=artifact_path,
        symbol=symbol,
        timeframe=timeframe,
        model_type=model_type,
        asset_class=asset_class,
        feature_count=feature_count,
        feature_fingerprint=feature_fingerprint,
        trained_at=trained_at,
        validation_available=validation_available,
        calibration_available=calibration_available,
        sample_count=sample_count,
        lifecycle_status=lifecycle_status,
    )


class TestRegistrySnapshotBuilder:
    def test_snapshot_creation(self):
        builder = RegistrySnapshotBuilder()

        models = (
            create_model_identity("artifacts/model1.pkl"),
            create_model_identity("artifacts/model2.pkl", symbol="ETHUSDT"),
        )

        snapshot = builder.build(models)

        assert isinstance(snapshot, RegistrySnapshot)
        assert snapshot.total_models == 2
        assert len(snapshot.models) == 2
        assert snapshot.snapshot_id.startswith("snapshot_")
        assert snapshot.created_at
        assert isinstance(snapshot.summary, dict)

    def test_immutable_snapshot(self):
        builder = RegistrySnapshotBuilder()
        models = (create_model_identity("artifacts/model1.pkl"),)
        snapshot = builder.build(models)

        with pytest.raises(Exception):
            snapshot.snapshot_id = "new_id"

        with pytest.raises(Exception):
            snapshot.total_models = 999

    def test_deterministic_snapshot_id(self):
        builder = RegistrySnapshotBuilder()

        models = (
            create_model_identity("artifacts/model1.pkl"),
            create_model_identity("artifacts/model2.pkl", symbol="ETHUSDT"),
        )

        snapshot1 = builder.build(models)
        snapshot2 = builder.build(models)

        assert snapshot1.snapshot_id == snapshot2.snapshot_id

    def test_same_registry_produces_same_id(self):
        builder = RegistrySnapshotBuilder()

        models_a = (
            create_model_identity("artifacts/model1.pkl", symbol="BTCUSDT"),
            create_model_identity("artifacts/model2.pkl", symbol="ETHUSDT"),
        )

        models_b = (
            create_model_identity("artifacts/model1.pkl", symbol="BTCUSDT"),
            create_model_identity("artifacts/model2.pkl", symbol="ETHUSDT"),
        )

        snapshot_a = builder.build(models_a)
        snapshot_b = builder.build(models_b)

        assert snapshot_a.snapshot_id == snapshot_b.snapshot_id

    def test_different_registry_produces_different_id(self):
        builder = RegistrySnapshotBuilder()

        models_a = (create_model_identity("artifacts/model1.pkl"),)

        models_b = (create_model_identity("artifacts/model2.pkl"),)

        snapshot_a = builder.build(models_a)
        snapshot_b = builder.build(models_b)

        assert snapshot_a.snapshot_id != snapshot_b.snapshot_id

    def test_timestamp_does_not_affect_snapshot_id(self):
        builder = RegistrySnapshotBuilder()

        models = (
            create_model_identity("artifacts/model1.pkl", trained_at="2024-01-01T00:00:00Z"),
        )

        snapshot1 = builder.build(models)
        snapshot2 = builder.build(models)

        assert snapshot1.snapshot_id == snapshot2.snapshot_id
        assert snapshot1.created_at != snapshot2.created_at

    def test_snapshot_summary_structure(self):
        builder = RegistrySnapshotBuilder()

        models = (
            create_model_identity(
                "artifacts/model1.pkl",
                lifecycle_status="candidate",
                validation_available=True,
            ),
            create_model_identity(
                "artifacts/model2.pkl",
                symbol="ETHUSDT",
                lifecycle_status="production",
                validation_available=False,
            ),
        )

        snapshot = builder.build(models)

        assert "by_lifecycle" in snapshot.summary
        assert "by_model_type" in snapshot.summary
        assert "by_symbol" in snapshot.summary
        assert "total_with_validation" in snapshot.summary
        assert "total_with_calibration" in snapshot.summary

        assert snapshot.summary["by_lifecycle"]["candidate"] == 1
        assert snapshot.summary["by_lifecycle"]["production"] == 1
        assert snapshot.summary["total_with_validation"] == 1

    def test_models_are_sorted(self):
        builder = RegistrySnapshotBuilder()

        models = (
            create_model_identity("artifacts/z.pkl", symbol="ZECUSDT"),
            create_model_identity("artifacts/a.pkl", symbol="ADAUSDT"),
            create_model_identity("artifacts/b.pkl", symbol="BTCUSDT"),
        )

        snapshot = builder.build(models)

        assert snapshot.models[0].symbol == "ADAUSDT"
        assert snapshot.models[1].symbol == "BTCUSDT"
        assert snapshot.models[2].symbol == "ZECUSDT"


class TestRegistryDiffEngine:
    def test_diff_detects_added_model(self):
        builder = RegistrySnapshotBuilder()
        diff_engine = RegistryDiffEngine()

        previous_models = (create_model_identity("artifacts/model1.pkl"),)

        current_models = (
            create_model_identity("artifacts/model1.pkl"),
            create_model_identity("artifacts/model2.pkl"),
        )

        prev_snapshot = builder.build(previous_models)
        curr_snapshot = builder.build(current_models)

        diff = diff_engine.diff(prev_snapshot, curr_snapshot)

        assert len(diff.added_models) == 1
        assert diff.added_models[0].artifact_path == "artifacts/model2.pkl"
        assert len(diff.removed_models) == 0
        assert len(diff.modified_models) == 0

    def test_diff_detects_removed_model(self):
        builder = RegistrySnapshotBuilder()
        diff_engine = RegistryDiffEngine()

        previous_models = (
            create_model_identity("artifacts/model1.pkl"),
            create_model_identity("artifacts/model2.pkl"),
        )

        current_models = (create_model_identity("artifacts/model1.pkl"),)

        prev_snapshot = builder.build(previous_models)
        curr_snapshot = builder.build(current_models)

        diff = diff_engine.diff(prev_snapshot, curr_snapshot)

        assert len(diff.added_models) == 0
        assert len(diff.removed_models) == 1
        assert diff.removed_models[0].artifact_path == "artifacts/model2.pkl"
        assert len(diff.modified_models) == 0

    def test_diff_detects_modified_lifecycle_status(self):
        builder = RegistrySnapshotBuilder()
        diff_engine = RegistryDiffEngine()

        previous_models = (
            create_model_identity("artifacts/model1.pkl", lifecycle_status="candidate"),
        )

        current_models = (
            create_model_identity("artifacts/model1.pkl", lifecycle_status="production"),
        )

        prev_snapshot = builder.build(previous_models)
        curr_snapshot = builder.build(current_models)

        diff = diff_engine.diff(prev_snapshot, curr_snapshot)

        assert len(diff.added_models) == 0
        assert len(diff.removed_models) == 0
        assert len(diff.modified_models) == 1

        prev_model, curr_model = diff.modified_models[0]
        assert prev_model.lifecycle_status == "candidate"
        assert curr_model.lifecycle_status == "production"

    def test_diff_detects_modified_feature_fingerprint(self):
        builder = RegistrySnapshotBuilder()
        diff_engine = RegistryDiffEngine()

        previous_models = (
            create_model_identity("artifacts/model1.pkl", feature_fingerprint="fp_old"),
        )

        current_models = (
            create_model_identity("artifacts/model1.pkl", feature_fingerprint="fp_new"),
        )

        prev_snapshot = builder.build(previous_models)
        curr_snapshot = builder.build(current_models)

        diff = diff_engine.diff(prev_snapshot, curr_snapshot)

        assert len(diff.modified_models) == 1

    def test_diff_detects_modified_validation_status(self):
        builder = RegistrySnapshotBuilder()
        diff_engine = RegistryDiffEngine()

        previous_models = (
            create_model_identity("artifacts/model1.pkl", validation_available=False),
        )

        current_models = (
            create_model_identity("artifacts/model1.pkl", validation_available=True),
        )

        prev_snapshot = builder.build(previous_models)
        curr_snapshot = builder.build(current_models)

        diff = diff_engine.diff(prev_snapshot, curr_snapshot)

        assert len(diff.modified_models) == 1

    def test_diff_unchanged_models(self):
        builder = RegistrySnapshotBuilder()
        diff_engine = RegistryDiffEngine()

        models = (create_model_identity("artifacts/model1.pkl"),)

        prev_snapshot = builder.build(models)
        curr_snapshot = builder.build(models)

        diff = diff_engine.diff(prev_snapshot, curr_snapshot)

        assert len(diff.added_models) == 0
        assert len(diff.removed_models) == 0
        assert len(diff.modified_models) == 0

    def test_diff_immutable(self):
        builder = RegistrySnapshotBuilder()
        diff_engine = RegistryDiffEngine()

        prev_models = (create_model_identity("artifacts/model1.pkl"),)
        curr_models = (create_model_identity("artifacts/model2.pkl"),)

        prev_snapshot = builder.build(prev_models)
        curr_snapshot = builder.build(curr_models)

        diff = diff_engine.diff(prev_snapshot, curr_snapshot)

        with pytest.raises(Exception):
            diff.added_models = ()


class TestNoDatabaseDependency:
    def test_no_database_imports(self):
        import ml_service.research.registry_snapshot.snapshot as snapshot_module
        import ml_service.research.registry_snapshot.diff as diff_module
        import ml_service.research.registry_snapshot.models as models_module

        snapshot_source = snapshot_module.__file__
        diff_source = diff_module.__file__
        models_source = models_module.__file__

        for source_file in [snapshot_source, diff_source, models_source]:
            with open(source_file) as f:
                content = f.read()
                assert "sqlalchemy" not in content.lower()
                assert "database" not in content.lower()
                assert "session" not in content.lower()
                assert "repository" not in content.lower()

    def test_no_execution_layer_imports(self):
        import ml_service.research.registry_snapshot.snapshot as snapshot_module
        import ml_service.research.registry_snapshot.diff as diff_module

        snapshot_source = snapshot_module.__file__
        diff_source = diff_module.__file__

        for source_file in [snapshot_source, diff_source]:
            with open(source_file) as f:
                content = f.read()
                assert "execution" not in content.lower()
                assert "simulator" not in content.lower()
                assert "portfolio" not in content.lower()
