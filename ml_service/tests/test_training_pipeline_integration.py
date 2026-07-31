"""Integration tests for TrainingPipelineManager and TrainerFactory."""

import pytest
import dataclasses
from unittest.mock import MagicMock

from ml_service.research.models import ResearchRun, DatasetSnapshot, FeatureSnapshot
from ml_service.research.training_pipeline import TrainingPipelineManager, TrainingResult, TrainingMetrics
from ml_service.research.trainers.trainer_factory import TrainerFactory


@pytest.fixture
def sample_research_run() -> ResearchRun:
    return ResearchRun(
        run_id="run-999",
        experiment_id="exp-999",
        status="CREATED",
        session_id="session-999",
        hyperparameters=(("max_depth", 6), ("epochs", 10)),
        metrics=(),
        model_binary_path=None,
        created_at="2026-07-31T00:00:00Z",
        completed_at=None
    )


@pytest.fixture
def sample_dataset_snapshot() -> DatasetSnapshot:
    return DatasetSnapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint="ds-fingerprint-999",
        file_path="/storage/datasets/ds_1.0.0.parquet",
        is_frozen=True,
        created_at="2026-07-31T00:00:00Z"
    )


@pytest.fixture
def sample_feature_snapshot() -> FeatureSnapshot:
    return FeatureSnapshot(
        feature_dataset_id="FDS_1.0.0",
        source_dataset_id="DS_1.0.0",
        fingerprint="feat-fingerprint-999",
        file_path="/storage/features/fds_1.0.0.parquet",
        is_frozen=True,
        created_at="2026-07-31T00:00:00Z"
    )


def test_xgboost_pipeline(sample_research_run, sample_dataset_snapshot, sample_feature_snapshot):
    """Verify that the pipeline completes successfully using the xgboost trainer."""
    manager = TrainingPipelineManager()
    
    result, updated_run = manager.run(
        research_run=sample_research_run,
        dataset_snapshot=sample_dataset_snapshot,
        feature_snapshot=sample_feature_snapshot,
        training_config={"epochs": 50},
        seed=42,
        model_params={"model_type": "xgboost", "max_depth": 6}
    )

    assert result.status == "SUCCESS"
    assert updated_run.status == "COMPLETED"
    assert updated_run.model_binary_path.startswith("/storage/models/xgboost_")
    assert result.metrics.sharpe > 0.0
    assert result.artifacts.permissions == "chmod 444"


def test_lightgbm_pipeline(sample_research_run, sample_dataset_snapshot, sample_feature_snapshot):
    """Verify that the pipeline completes successfully using the lightgbm trainer."""
    manager = TrainingPipelineManager()
    
    result, updated_run = manager.run(
        research_run=sample_research_run,
        dataset_snapshot=sample_dataset_snapshot,
        feature_snapshot=sample_feature_snapshot,
        training_config={"epochs": 50},
        seed=42,
        model_params={"model_type": "lightgbm", "num_leaves": 31}
    )

    assert result.status == "SUCCESS"
    assert updated_run.status == "COMPLETED"
    assert updated_run.model_binary_path.startswith("/storage/models/lightgbm_")
    assert result.metrics.sharpe > 0.0
    assert result.artifacts.permissions == "chmod 444"


def test_invalid_algorithm(sample_research_run, sample_dataset_snapshot, sample_feature_snapshot):
    """Verify that an invalid algorithm immediately raises ValueError."""
    manager = TrainingPipelineManager()

    with pytest.raises(ValueError, match="Unknown algorithm"):
        manager.run(
            research_run=sample_research_run,
            dataset_snapshot=sample_dataset_snapshot,
            feature_snapshot=sample_feature_snapshot,
            training_config={"epochs": 50},
            seed=42,
            model_params={"model_type": "unknown_algo"}
        )


def test_deterministic_execution(sample_research_run, sample_dataset_snapshot, sample_feature_snapshot):
    """Verify that identical runs yield identical results."""
    manager = TrainingPipelineManager()

    res_1, run_1 = manager.run(
        research_run=sample_research_run,
        dataset_snapshot=sample_dataset_snapshot,
        feature_snapshot=sample_feature_snapshot,
        training_config={"epochs": 50},
        seed=123,
        model_params={"model_type": "xgboost", "max_depth": 6}
    )

    res_2, run_2 = manager.run(
        research_run=sample_research_run,
        dataset_snapshot=sample_dataset_snapshot,
        feature_snapshot=sample_feature_snapshot,
        training_config={"epochs": 50},
        seed=123,
        model_params={"model_type": "xgboost", "max_depth": 6}
    )

    assert res_1.metrics == res_2.metrics
    assert res_1.artifacts.checksum == res_2.artifacts.checksum
    assert run_1.model_binary_path == run_2.model_binary_path


def test_immutable_outputs(sample_research_run, sample_dataset_snapshot, sample_feature_snapshot):
    """Verify outputs are immutable."""
    manager = TrainingPipelineManager()
    result, updated_run = manager.run(
        research_run=sample_research_run,
        dataset_snapshot=sample_dataset_snapshot,
        feature_snapshot=sample_feature_snapshot,
        training_config={"epochs": 50},
        seed=42,
        model_params={"model_type": "xgboost", "max_depth": 6}
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.status = "MUTATED"  # type: ignore

    with pytest.raises(dataclasses.FrozenInstanceError):
        updated_run.status = "MUTATED"  # type: ignore


def test_lifecycle_ordering(sample_research_run, sample_dataset_snapshot, sample_feature_snapshot, monkeypatch):
    """Verify that the trainer lifecycle methods are executed in the correct order."""
    call_order = []

    # Mock TrainerFactory.create to return a mocked trainer that logs calls
    original_create = TrainerFactory.create
    
    def mock_create(algorithm: str, **kwargs):
        trainer = original_create(algorithm, **kwargs)
        
        # Spy on all key lifecycle methods
        orig_prepare = trainer.prepare
        orig_train = trainer.train
        orig_evaluate = trainer.evaluate
        orig_save_artifacts = trainer.save_artifacts
        
        def spy_prepare(*args, **kwargs):
            call_order.append("prepare")
            return orig_prepare(*args, **kwargs)
            
        def spy_train(*args, **kwargs):
            call_order.append("train")
            return orig_train(*args, **kwargs)
            
        def spy_evaluate(*args, **kwargs):
            call_order.append("evaluate")
            return orig_evaluate(*args, **kwargs)
            
        def spy_save_artifacts(*args, **kwargs):
            call_order.append("save_artifacts")
            return orig_save_artifacts(*args, **kwargs)
            
        trainer.prepare = spy_prepare
        trainer.train = spy_train
        trainer.evaluate = spy_evaluate
        trainer.save_artifacts = spy_save_artifacts
        return trainer

    monkeypatch.setattr(TrainerFactory, "create", mock_create)
    
    manager = TrainingPipelineManager()
    manager.run(
        research_run=sample_research_run,
        dataset_snapshot=sample_dataset_snapshot,
        feature_snapshot=sample_feature_snapshot,
        training_config={"epochs": 50},
        seed=42,
        model_params={"model_type": "xgboost", "max_depth": 6}
    )

    assert call_order == ["prepare", "train", "evaluate", "save_artifacts"]


def test_fail_fast_behavior(sample_research_run, sample_dataset_snapshot, sample_feature_snapshot):
    """Verify that validation failures are handled immediately without executing any lifecycle methods."""
    manager = TrainingPipelineManager()

    # Pass an invalid research run, should fail fast raising ValueError
    with pytest.raises(ValueError, match="Expected ResearchRun"):
        manager.run(
            research_run="not_a_research_run",  # type: ignore
            dataset_snapshot=sample_dataset_snapshot,
            feature_snapshot=sample_feature_snapshot,
            training_config={"epochs": 50},
            seed=42,
            model_params={"model_type": "xgboost"}
        )
