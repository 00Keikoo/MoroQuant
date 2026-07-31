"""Tests for the real LightGBMTrainer implementation."""

import hashlib
import os
import dataclasses
import numpy as np
import pandas as pd
import pytest

from ml_service.research.models import DatasetSnapshot, FeatureSnapshot, ResearchRun
from ml_service.research.trainers.base_trainer import TrainerConfig, TrainingResult, ArtifactMetadata
from ml_service.research.trainers.lightgbm_trainer import LightGBMTrainer, LightGBMTrainingMetrics


def compute_file_sha256(file_path: str) -> str:
    """Compute SHA-256 checksum of a file."""
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


@pytest.fixture
def temp_data_paths(tmp_path):
    """Fixture to generate synthetic dataset and feature parquets and return snapshots."""
    np.random.seed(42)
    n_rows = 100
    timestamps = pd.date_range("2026-01-01", periods=n_rows, freq="h")
    
    # Positive correlation to guarantee positive Sharpe ratio
    df_dataset = pd.DataFrame({
        "timestamp": timestamps,
        "symbol": "BTCUSDT",
        "target": (np.random.normal(0.5, 1.0, n_rows) > 0.0).astype(float)
    })
    
    df_features = pd.DataFrame({
        "timestamp": timestamps,
        "symbol": "BTCUSDT",
        "feat_1": np.random.normal(0.5, 1.0, n_rows),
        "feat_2": np.random.normal(-0.5, 1.0, n_rows)
    })
    
    ds_path = str(tmp_path / "dataset.parquet")
    feat_path = str(tmp_path / "features.parquet")
    
    df_dataset.to_parquet(ds_path)
    df_features.to_parquet(feat_path)
    
    ds_hash = compute_file_sha256(ds_path)
    feat_hash = compute_file_sha256(feat_path)
    
    dataset_snapshot = DatasetSnapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint=ds_hash,
        file_path=ds_path,
        is_frozen=True,
        created_at="2026-07-31T00:00:00Z"
    )
    
    feature_snapshot = FeatureSnapshot(
        feature_dataset_id="FDS_1.0.0",
        source_dataset_id="DS_1.0.0",
        fingerprint=feat_hash,
        file_path=feat_path,
        is_frozen=True,
        created_at="2026-07-31T00:00:00Z"
    )
    
    return dataset_snapshot, feature_snapshot


@pytest.fixture
def valid_config():
    return TrainerConfig(
        model_type="lightgbm",
        seed=42,
        hyperparameters=(
            ("max_depth", 3),
            ("learning_rate", 0.1),
            ("objective", "binary"),
            ("metric", "binary_logloss")
        ),
        training_parameters=(
            ("epochs", 10),
            ("validation_split_ratio", 0.2),
            ("target_column", "target")
        )
    )


@pytest.fixture
def sample_research_run():
    return ResearchRun(
        run_id="run-123",
        experiment_id="exp-456",
        status="CREATED",
        session_id="session-789",
        hyperparameters=(),
        metrics=(),
        model_binary_path=None,
        created_at="2026-07-31T00:00:00Z",
        completed_at=None
    )


def test_validation(temp_data_paths, valid_config, sample_research_run):
    """Verify validation constraints."""
    trainer = LightGBMTrainer()
    dataset, features = temp_data_paths

    # Should succeed with valid config/state
    trainer.validate(dataset, features, valid_config, sample_research_run)

    # Empty hyperparameters
    bad_config_hparams = TrainerConfig("lightgbm", 42, (), (("epochs", 10),))
    with pytest.raises(ValueError, match="Model hyperparameters must be present"):
        trainer.validate(dataset, features, bad_config_hparams)

    # Invalid model type
    bad_config_model = TrainerConfig("xgboost", 42, (("max_depth", 6),), (("epochs", 10),))
    with pytest.raises(ValueError, match="Invalid model_type"):
        trainer.validate(dataset, features, bad_config_model)


def test_deterministic_seed(temp_data_paths, valid_config, sample_research_run):
    """Verify that using the same seed produces identical results."""
    dataset, features = temp_data_paths

    config_1 = TrainerConfig(
        model_type="lightgbm",
        seed=100,
        hyperparameters=(("max_depth", 3), ("bagging_fraction", 0.5), ("bagging_freq", 1)),
        training_parameters=(("epochs", 10),)
    )
    config_2 = TrainerConfig(
        model_type="lightgbm",
        seed=100,
        hyperparameters=(("max_depth", 3), ("bagging_fraction", 0.5), ("bagging_freq", 1)),
        training_parameters=(("epochs", 10),)
    )
    config_3 = TrainerConfig(
        model_type="lightgbm",
        seed=200,
        hyperparameters=(("max_depth", 3), ("bagging_fraction", 0.5), ("bagging_freq", 1)),
        training_parameters=(("epochs", 10),)
    )

    trainer_1 = LightGBMTrainer()
    res_1 = trainer_1.train(dataset, features, config_1, sample_research_run)

    trainer_2 = LightGBMTrainer()
    res_2 = trainer_2.train(dataset, features, config_2, sample_research_run)

    trainer_3 = LightGBMTrainer()
    res_3 = trainer_3.train(dataset, features, config_3, sample_research_run)

    assert res_1.metrics.accuracy == res_2.metrics.accuracy
    assert res_1.artifacts.checksum == res_2.artifacts.checksum
    assert res_1.metrics.accuracy != res_3.metrics.accuracy or res_1.artifacts.checksum != res_3.artifacts.checksum


def test_successful_training(temp_data_paths, valid_config, sample_research_run):
    """Verify end-to-end training and metric collection."""
    dataset, features = temp_data_paths
    trainer = LightGBMTrainer()
    
    result = trainer.train(dataset, features, valid_config, sample_research_run)
    assert isinstance(result, TrainingResult)
    assert result.status == "SUCCESS"
    assert isinstance(result.metrics, LightGBMTrainingMetrics)
    assert len(result.metrics.loss_history) > 0
    assert result.metrics.accuracy >= 0.0
    assert result.metrics.f1 >= 0.0


def test_evaluation(temp_data_paths, valid_config, sample_research_run):
    """Verify evaluate yields valid metrics post training."""
    dataset, features = temp_data_paths
    trainer = LightGBMTrainer()

    # Pre-train check
    with pytest.raises(ValueError, match="Cannot evaluate"):
        trainer.evaluate(dataset)

    trainer.train(dataset, features, valid_config, sample_research_run)
    
    eval_metrics = trainer.evaluate(dataset)
    assert isinstance(eval_metrics, LightGBMTrainingMetrics)
    assert eval_metrics.accuracy >= 0.0


def test_artifact_generation(temp_data_paths, valid_config, sample_research_run):
    """Verify generate_artifacts builds in-memory serialized structure."""
    dataset, features = temp_data_paths
    trainer = LightGBMTrainer()
    
    trainer.train(dataset, features, valid_config, sample_research_run)

    artifacts = trainer.generate_artifacts()
    assert "model" in artifacts
    assert "feature_importance" in artifacts
    assert "metadata" in artifacts
    assert "metrics" in artifacts
    
    assert artifacts["metadata"]["model_type"] == "lightgbm"
    assert "feat_1" in artifacts["metadata"]["feature_names"]


def test_failure_handling(temp_data_paths, valid_config, sample_research_run, tmp_path):
    """Verify failure state handling when fingerprints are invalid."""
    dataset, features = temp_data_paths
    
    bad_dataset = dataclasses.replace(dataset, fingerprint="invalid_hash")
    trainer = LightGBMTrainer()
    
    with pytest.raises(ValueError, match="Dataset fingerprint mismatch"):
        trainer.train(bad_dataset, features, valid_config, sample_research_run)


def test_immutable_outputs(temp_data_paths, valid_config, sample_research_run):
    """Verify metrics and result objects are frozen."""
    dataset, features = temp_data_paths
    trainer = LightGBMTrainer()
    
    result = trainer.train(dataset, features, valid_config, sample_research_run)
    
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.metrics.accuracy = 1.0
