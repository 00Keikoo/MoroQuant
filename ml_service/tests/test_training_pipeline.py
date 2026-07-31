"""Tests for TrainingPipelineManager."""

import pytest
import dataclasses
from ml_service.research.models import ResearchRun, DatasetSnapshot, FeatureSnapshot
from ml_service.research.training_pipeline import (
    TrainingPipelineManager,
    TrainingResult,
    TrainingMetrics,
    ArtifactMetadata
)


@pytest.fixture
def sample_research_run() -> ResearchRun:
    return ResearchRun(
        run_id="run-123",
        experiment_id="exp-456",
        status="CREATED",
        session_id="session-789",
        hyperparameters=(("lr", 0.01), ("epochs", 10)),
        metrics=(),
        model_binary_path=None,
        created_at="2026-07-31T00:00:00Z",
        completed_at=None
    )


@pytest.fixture
def sample_dataset_snapshot() -> DatasetSnapshot:
    return DatasetSnapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint="ds-fingerprint-abc",
        file_path="/storage/datasets/ds_1.0.0.parquet",
        is_frozen=True,
        created_at="2026-07-31T00:00:00Z"
    )


@pytest.fixture
def sample_feature_snapshot() -> FeatureSnapshot:
    return FeatureSnapshot(
        feature_dataset_id="FDS_1.0.0",
        source_dataset_id="DS_1.0.0",
        fingerprint="feat-fingerprint-xyz",
        file_path="/storage/features/fds_1.0.0.parquet",
        is_frozen=True,
        created_at="2026-07-31T00:00:00Z"
    )


def test_pipeline_creation():
    """Verify TrainingPipelineManager can be instantiated."""
    manager = TrainingPipelineManager()
    assert manager is not None
    assert callable(manager._trainer_fn)


def test_placeholder_trainer_invocation(
    sample_research_run,
    sample_dataset_snapshot,
    sample_feature_snapshot
):
    """Verify that by default the trainer invocation raises ValueError when algorithm is omitted."""
    manager = TrainingPipelineManager()
    
    with pytest.raises(ValueError, match="model_type must be specified and non-empty."):
        manager.run(
            research_run=sample_research_run,
            dataset_snapshot=sample_dataset_snapshot,
            feature_snapshot=sample_feature_snapshot,
            training_config={"batch_size": 32, "epochs": 5},
            seed=42,
            model_params={"layers": [64, 32]}
        )


def test_algorithm_validation_cases(
    sample_research_run,
    sample_dataset_snapshot,
    sample_feature_snapshot
):
    """Verify fail-fast algorithm validation for various cases."""
    manager = TrainingPipelineManager()

    # None algorithm
    with pytest.raises(ValueError, match="model_type must be specified and non-empty."):
        manager.run(
            research_run=sample_research_run,
            dataset_snapshot=sample_dataset_snapshot,
            feature_snapshot=sample_feature_snapshot,
            training_config={},
            seed=42,
            model_params={"model_type": None}
        )

    # Empty string algorithm
    with pytest.raises(ValueError, match="model_type must be specified and non-empty."):
        manager.run(
            research_run=sample_research_run,
            dataset_snapshot=sample_dataset_snapshot,
            feature_snapshot=sample_feature_snapshot,
            training_config={},
            seed=42,
            model_params={"model_type": ""}
        )

    # Unknown algorithm
    with pytest.raises(ValueError, match="Unknown algorithm 'unknown'"):
        manager.run(
            research_run=sample_research_run,
            dataset_snapshot=sample_dataset_snapshot,
            feature_snapshot=sample_feature_snapshot,
            training_config={},
            seed=42,
            model_params={"model_type": "unknown"}
        )

    # Valid xgboost
    res_xgb, _ = manager.run(
        research_run=sample_research_run,
        dataset_snapshot=sample_dataset_snapshot,
        feature_snapshot=sample_feature_snapshot,
        training_config={"epochs": 10},
        seed=42,
        model_params={"model_type": "xgboost", "max_depth": 6}
    )
    assert res_xgb.status == "SUCCESS"

    # Valid lightgbm
    res_lgb, _ = manager.run(
        research_run=sample_research_run,
        dataset_snapshot=sample_dataset_snapshot,
        feature_snapshot=sample_feature_snapshot,
        training_config={"epochs": 10},
        seed=42,
        model_params={"model_type": "lightgbm", "num_leaves": 31}
    )
    assert res_lgb.status == "SUCCESS"



def test_validation_failure_on_missing_or_invalid_inputs(
    sample_research_run,
    sample_dataset_snapshot,
    sample_feature_snapshot
):
    """Verify that TrainingPipelineManager checks inputs and raises ValueError for missing/invalid inputs."""
    manager = TrainingPipelineManager()

    # None inputs
    with pytest.raises(ValueError, match="research_run cannot be None"):
        manager.run(None, sample_dataset_snapshot, sample_feature_snapshot, {}, 42, {})

    with pytest.raises(ValueError, match="dataset_snapshot cannot be None"):
        manager.run(sample_research_run, None, sample_feature_snapshot, {}, 42, {})

    with pytest.raises(ValueError, match="feature_snapshot cannot be None"):
        manager.run(sample_research_run, sample_dataset_snapshot, None, {}, 42, {})

    with pytest.raises(ValueError, match="training_config cannot be None"):
        manager.run(sample_research_run, sample_dataset_snapshot, sample_feature_snapshot, None, 42, {})

    with pytest.raises(ValueError, match="seed cannot be None"):
        manager.run(sample_research_run, sample_dataset_snapshot, sample_feature_snapshot, {}, None, {})

    with pytest.raises(ValueError, match="model_params cannot be None"):
        manager.run(sample_research_run, sample_dataset_snapshot, sample_feature_snapshot, {}, 42, None)

    # Invalid types
    with pytest.raises(ValueError, match="Expected ResearchRun"):
        manager.run("invalid_run", sample_dataset_snapshot, sample_feature_snapshot, {}, 42, {})

    with pytest.raises(ValueError, match="Expected DatasetSnapshot"):
        manager.run(sample_research_run, "invalid_snapshot", sample_feature_snapshot, {}, 42, {})

    with pytest.raises(ValueError, match="Expected FeatureSnapshot"):
        manager.run(sample_research_run, sample_dataset_snapshot, "invalid_snapshot", {}, 42, {})

    with pytest.raises(ValueError, match="Expected dict for training_config"):
        manager.run(sample_research_run, sample_dataset_snapshot, sample_feature_snapshot, "invalid_config", 42, {})

    with pytest.raises(ValueError, match="Expected int for seed"):
        manager.run(sample_research_run, sample_dataset_snapshot, sample_feature_snapshot, {}, "invalid_seed", {})

    with pytest.raises(ValueError, match="Expected dict for model_params"):
        manager.run(sample_research_run, sample_dataset_snapshot, sample_feature_snapshot, {}, 42, "invalid_params")


def test_deterministic_ordering_and_context_building(
    sample_research_run,
    sample_dataset_snapshot,
    sample_feature_snapshot
):
    """Verify that training context parameters and outputs are sorted deterministically."""
    captured_context = []

    def mock_trainer(context):
        captured_context.append(context)
        return {
            "metrics": {"sharpe": 2.5, "ece": 0.02, "brier": 0.1, "drawdown": 0.05},
            "model_path": "/storage/models/test.bin",
            "size_bytes": 500
        }

    manager = TrainingPipelineManager(trainer_fn=mock_trainer)
    
    # We pass training_config and model_params with unordered dict keys
    unordered_config = {"epochs": 10, "batch_size": 32, "lr": 0.001}
    unordered_params = {"activation": "relu", "layers": [128, 64], "dropout": 0.2}

    manager.run(
        research_run=sample_research_run,
        dataset_snapshot=sample_dataset_snapshot,
        feature_snapshot=sample_feature_snapshot,
        training_config=unordered_config,
        seed=42,
        model_params=unordered_params
    )

    assert len(captured_context) == 1
    ctx = captured_context[0]

    # Verify context lists/tuples are sorted
    assert ctx["config"] == (("batch_size", 32), ("epochs", 10), ("lr", 0.001))
    assert ctx["params"] == (("activation", "relu"), ("dropout", 0.2), ("layers", (128, 64)))
    
    # Verify dataset context is sorted tuple of key-value pairs
    assert isinstance(ctx["dataset"], tuple)
    assert ctx["dataset"] == (
        ("file_path", "/storage/datasets/ds_1.0.0.parquet"),
        ("fingerprint", "ds-fingerprint-abc"),
        ("version_id", "DS_1.0.0")
    )


def test_successful_execution_metrics_and_artifacts(
    sample_research_run,
    sample_dataset_snapshot,
    sample_feature_snapshot
):
    """Verify outputs (TrainingResult, TrainingMetrics, ArtifactMetadata, Updated ResearchRun) on success."""
    def mock_trainer(context):
        return {
            "metrics": {
                "loss_history": [0.5, 0.2, 0.01],
                "val_loss_history": [0.6, 0.25, 0.02],
                "sharpe": 3.2,
                "ece": 0.01,
                "brier": 0.08,
                "drawdown": 0.04
            },
            "model_path": "/storage/models/run-123.bin",
            "size_bytes": 2048
        }

    manager = TrainingPipelineManager(trainer_fn=mock_trainer)
    result, updated_run = manager.run(
        research_run=sample_research_run,
        dataset_snapshot=sample_dataset_snapshot,
        feature_snapshot=sample_feature_snapshot,
        training_config={},
        seed=100,
        model_params={}
    )

    # Verify TrainingResult structure and values
    assert isinstance(result, TrainingResult)
    assert result.status == "SUCCESS"
    assert result.error_message is None

    # Verify TrainingMetrics
    metrics = result.metrics
    assert isinstance(metrics, TrainingMetrics)
    assert metrics.loss_history == (0.5, 0.2, 0.01)
    assert metrics.val_loss_history == (0.6, 0.25, 0.02)
    assert metrics.sharpe == 3.2
    assert metrics.ece == 0.01
    assert metrics.brier == 0.08
    assert metrics.drawdown == 0.04

    # Verify ArtifactMetadata
    artifacts = result.artifacts
    assert isinstance(artifacts, ArtifactMetadata)
    assert artifacts.file_path == "/storage/models/run-123.bin"
    assert artifacts.size_bytes == 2048
    assert artifacts.permissions == "chmod 444"
    assert len(artifacts.checksum) == 64  # SHA-256 length

    # Verify Updated ResearchRun
    assert isinstance(updated_run, ResearchRun)
    assert updated_run.status == "COMPLETED"
    assert updated_run.model_binary_path == "/storage/models/run-123.bin"
    assert updated_run.completed_at is not None
    # Metrics tuple sorted
    assert updated_run.metrics == (
        ("brier", 0.08),
        ("drawdown", 0.04),
        ("ece", 0.01),
        ("final_loss", 0.01),
        ("final_val_loss", 0.02),
        ("sharpe", 3.2)
    )


def test_immutable_outputs(
    sample_research_run,
    sample_dataset_snapshot,
    sample_feature_snapshot
):
    """Verify that output dataclasses are frozen and immutable."""
    def mock_trainer(context):
        return {
            "metrics": {"sharpe": 1.5},
            "model_path": "/storage/models/test.bin",
            "size_bytes": 100
        }

    manager = TrainingPipelineManager(trainer_fn=mock_trainer)
    result, updated_run = manager.run(
        research_run=sample_research_run,
        dataset_snapshot=sample_dataset_snapshot,
        feature_snapshot=sample_feature_snapshot,
        training_config={},
        seed=42,
        model_params={}
    )

    # dataclasses are frozen
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.status = "MUTATED"

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.metrics.sharpe = 9.9

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.artifacts.file_path = "/mutated/path.bin"

    # ResearchRun is frozen
    with pytest.raises(dataclasses.FrozenInstanceError):
        updated_run.status = "MUTATED"


def test_failure_handling(
    sample_research_run,
    sample_dataset_snapshot,
    sample_feature_snapshot
):
    """Verify pipeline failure handling when trainer raises an unexpected error."""
    def bad_trainer(context):
        raise ValueError("Out of memory simulated error")

    manager = TrainingPipelineManager(trainer_fn=bad_trainer)
    result, updated_run = manager.run(
        research_run=sample_research_run,
        dataset_snapshot=sample_dataset_snapshot,
        feature_snapshot=sample_feature_snapshot,
        training_config={},
        seed=42,
        model_params={}
    )

    assert result.status == "FAILED_TRAINING"
    assert "Out of memory simulated error" in result.error_message
    assert updated_run.status == "FAILED"
    assert updated_run.completed_at is not None
