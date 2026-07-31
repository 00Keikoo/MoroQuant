"""Tests for XGBoostTrainer."""

import pytest
import dataclasses
from ml_service.research.models import DatasetSnapshot, FeatureSnapshot
from ml_service.research.trainers.base_trainer import TrainerConfig, TrainingResult, TrainingMetrics, ArtifactMetadata
from ml_service.research.trainers.xgboost_trainer import XGBoostTrainer


@pytest.fixture
def valid_dataset():
    return DatasetSnapshot(
        dataset_version_id="DS_1.0.0",
        fingerprint="a" * 64,
        file_path="data/dataset.parquet",
        is_frozen=True,
        created_at="2026-07-31T00:00:00+00:00"
    )


@pytest.fixture
def valid_features():
    return FeatureSnapshot(
        feature_dataset_id="FS_1.0.0",
        source_dataset_id="DS_1.0.0",
        fingerprint="b" * 64,
        file_path="data/features.parquet",
        is_frozen=True,
        created_at="2026-07-31T00:00:00+00:00"
    )


@pytest.fixture
def valid_config():
    return TrainerConfig(
        model_type="xgboost",
        seed=42,
        hyperparameters=(("max_depth", 6), ("learning_rate", 0.1)),
        training_parameters=(("epochs", 100),)
    )


def test_trainer_construction():
    """Verify that XGBoostTrainer can be constructed and has correct initial state."""
    trainer = XGBoostTrainer()
    assert trainer._dataset is None
    assert trainer._features is None
    assert trainer._config is None
    assert trainer._is_trained is False
    assert trainer._metrics is None
    assert trainer._artifact is None


def test_validation_success(valid_dataset, valid_features, valid_config):
    """Verify validate() succeeds with correct arguments."""
    trainer = XGBoostTrainer()
    # Should not raise any exception
    trainer.validate(valid_dataset, valid_features, valid_config)


def test_validation_failures(valid_dataset, valid_features, valid_config):
    """Verify validate() raises ValueError under various invalid parameters."""
    trainer = XGBoostTrainer()

    # Invalid dataset type
    with pytest.raises(ValueError, match="DatasetSnapshot must be provided"):
        trainer.validate(None, valid_features, valid_config)

    with pytest.raises(ValueError, match="DatasetSnapshot must be provided"):
        trainer.validate("not_a_dataset", valid_features, valid_config)

    # Invalid features type
    with pytest.raises(ValueError, match="FeatureSnapshot must be provided"):
        trainer.validate(valid_dataset, None, valid_config)

    with pytest.raises(ValueError, match="FeatureSnapshot must be provided"):
        trainer.validate(valid_dataset, "not_features", valid_config)

    # Invalid config type
    with pytest.raises(ValueError, match="TrainerConfig must be provided"):
        trainer.validate(valid_dataset, valid_features, None)

    # Invalid model_type
    bad_config_model = TrainerConfig("lightgbm", 42, (("max_depth", 6),), (("epochs", 10),))
    with pytest.raises(ValueError, match="Invalid model_type"):
        trainer.validate(valid_dataset, valid_features, bad_config_model)

    # Empty hyperparameters
    bad_config_hparams = TrainerConfig("xgboost", 42, (), (("epochs", 10),))
    with pytest.raises(ValueError, match="Model hyperparameters must be present"):
        trainer.validate(valid_dataset, valid_features, bad_config_hparams)

    # Empty training parameters
    bad_config_train_params = TrainerConfig("xgboost", 42, (("max_depth", 6),), ())
    with pytest.raises(ValueError, match="Training parameters must be present"):
        trainer.validate(valid_dataset, valid_features, bad_config_train_params)


def test_train_execution(valid_dataset, valid_features, valid_config):
    """Verify that train() executes and returns correct TrainingResult."""
    trainer = XGBoostTrainer()
    result = trainer.train(valid_dataset, valid_features, valid_config)

    assert isinstance(result, TrainingResult)
    assert result.status == "SUCCESS"
    assert trainer._is_trained is True
    assert trainer._dataset == valid_dataset
    assert trainer._features == valid_features
    assert trainer._config == valid_config
    assert result.metrics == trainer.collect_metrics()
    assert result.artifacts == trainer.generate_artifact()


def test_evaluate_and_collect_metrics_before_training(valid_dataset):
    """Verify methods raise ValueError if called before train()."""
    trainer = XGBoostTrainer()

    with pytest.raises(ValueError, match="Trainer has not been trained yet"):
        trainer.evaluate(valid_dataset)

    with pytest.raises(ValueError, match="Trainer has not been trained yet"):
        trainer.collect_metrics()

    with pytest.raises(ValueError, match="Trainer has not been trained yet"):
        trainer.generate_artifact()


def test_evaluate_after_training(valid_dataset, valid_features, valid_config):
    """Verify evaluate() runs successfully after training."""
    trainer = XGBoostTrainer()
    trainer.train(valid_dataset, valid_features, valid_config)

    # Valid evaluation call
    eval_metrics = trainer.evaluate(valid_dataset)
    assert isinstance(eval_metrics, TrainingMetrics)
    assert len(eval_metrics.loss_history) > 0

    # Invalid evaluation call (missing/invalid dataset)
    with pytest.raises(ValueError, match="DatasetSnapshot must be provided"):
        trainer.evaluate(None)


def test_artifact_generation(valid_dataset, valid_features, valid_config):
    """Verify that generated artifact metadata has deterministic hash."""
    trainer = XGBoostTrainer()
    result = trainer.train(valid_dataset, valid_features, valid_config)

    artifact = trainer.generate_artifact()
    assert isinstance(artifact, ArtifactMetadata)
    assert len(artifact.checksum) == 64  # SHA-256 length
    assert artifact.file_path.startswith("/storage/models/xgboost_")
    assert artifact.size_bytes > 0
    assert artifact.permissions == "chmod 444"


def test_cleanup(valid_dataset, valid_features, valid_config):
    """Verify cleanup() resets internal state."""
    trainer = XGBoostTrainer()
    trainer.train(valid_dataset, valid_features, valid_config)
    assert trainer._is_trained is True

    trainer.cleanup()
    assert trainer._dataset is None
    assert trainer._features is None
    assert trainer._config is None
    assert trainer._is_trained is False
    assert trainer._metrics is None
    assert trainer._artifact is None


def test_deterministic_outputs(valid_dataset, valid_features):
    """Verify that trainer produces identical results for identical seeds and configuration."""
    config_1 = TrainerConfig(
        model_type="xgboost",
        seed=100,
        hyperparameters=(("max_depth", 6),),
        training_parameters=(("epochs", 50),)
    )
    config_2 = TrainerConfig(
        model_type="xgboost",
        seed=100,
        hyperparameters=(("max_depth", 6),),
        training_parameters=(("epochs", 50),)
    )
    config_3 = TrainerConfig(
        model_type="xgboost",
        seed=200,
        hyperparameters=(("max_depth", 6),),
        training_parameters=(("epochs", 50),)
    )

    trainer_a = XGBoostTrainer()
    trainer_b = XGBoostTrainer()
    trainer_c = XGBoostTrainer()

    res_a = trainer_a.train(valid_dataset, valid_features, config_1)
    res_b = trainer_b.train(valid_dataset, valid_features, config_2)
    res_c = trainer_c.train(valid_dataset, valid_features, config_3)

    # Identical configurations should produce identical metrics and artifacts
    assert res_a.metrics == res_b.metrics
    assert res_a.artifacts.checksum == res_b.artifacts.checksum
    assert res_a.artifacts.file_path == res_b.artifacts.file_path

    # Different configuration (different seed) should produce different metrics/checksum
    assert res_a.metrics != res_c.metrics
    assert res_a.artifacts.checksum != res_c.artifacts.checksum
