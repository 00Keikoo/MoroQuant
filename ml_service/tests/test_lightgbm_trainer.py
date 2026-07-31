"""Tests for LightGBMTrainer."""

import pytest
import dataclasses
from ml_service.research.models import DatasetSnapshot, FeatureSnapshot, ResearchRun
from ml_service.research.trainers.base_trainer import TrainerConfig, TrainingResult, TrainingMetrics, ArtifactMetadata
from ml_service.research.trainers.lightgbm_trainer import LightGBMTrainer


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
        model_type="lightgbm",
        seed=42,
        hyperparameters=(("num_leaves", 31), ("learning_rate", 0.05)),
        training_parameters=(("epochs", 100),)
    )


@pytest.fixture
def valid_run():
    return ResearchRun(
        run_id="run-12345",
        experiment_id="exp-12345",
        status="CREATED",
        session_id="session-12345",
        hyperparameters=(("num_leaves", 31), ("learning_rate", 0.05))
    )


def test_trainer_construction():
    """Verify that LightGBMTrainer can be constructed and has correct initial state."""
    trainer = LightGBMTrainer()
    assert trainer._dataset is None
    assert trainer._features is None
    assert trainer._config is None
    assert trainer._run is None
    assert trainer._is_prepared is False
    assert trainer._is_trained is False
    assert trainer._metrics is None
    assert trainer._artifact is None


def test_validation_success(valid_dataset, valid_features, valid_config, valid_run):
    """Verify validate() succeeds with correct arguments."""
    trainer = LightGBMTrainer()
    # Should not raise any exception
    trainer.validate(valid_dataset, valid_features, valid_config, valid_run)


def test_validation_failures(valid_dataset, valid_features, valid_config, valid_run):
    """Verify validate() raises ValueError under various invalid parameters."""
    trainer = LightGBMTrainer()

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
    bad_config_model = TrainerConfig("xgboost", 42, (("num_leaves", 31),), (("epochs", 10),))
    with pytest.raises(ValueError, match="Invalid model_type"):
        trainer.validate(valid_dataset, valid_features, bad_config_model)

    # Empty hyperparameters
    bad_config_hparams = TrainerConfig("lightgbm", 42, (), (("epochs", 10),))
    with pytest.raises(ValueError, match="Model hyperparameters must be present"):
        trainer.validate(valid_dataset, valid_features, bad_config_hparams)

    # Empty training parameters
    bad_config_train_params = TrainerConfig("lightgbm", 42, (("num_leaves", 31),), ())
    with pytest.raises(ValueError, match="Training parameters must be present"):
        trainer.validate(valid_dataset, valid_features, bad_config_train_params)


def test_invalid_run_validation(valid_dataset, valid_features, valid_config):
    """Verify validate() raises ValueError for invalid research run."""
    trainer = LightGBMTrainer()

    # Wrong type
    with pytest.raises(ValueError, match="ResearchRun must be provided"):
        trainer.validate(valid_dataset, valid_features, valid_config, run="not_a_run")

    # Missing run_id
    bad_run_id = ResearchRun("", "exp-123", "CREATED")
    with pytest.raises(ValueError, match="ResearchRun must have a valid run_id"):
        trainer.validate(valid_dataset, valid_features, valid_config, run=bad_run_id)

    # Missing experiment_id
    bad_exp_id = ResearchRun("run-123", "", "CREATED")
    with pytest.raises(ValueError, match="ResearchRun must have a valid experiment_id"):
        trainer.validate(valid_dataset, valid_features, valid_config, run=bad_exp_id)


def test_prepare_lifecycle(valid_dataset, valid_features, valid_config, valid_run):
    """Verify prepare() lifecycle method."""
    trainer = LightGBMTrainer()
    trainer.prepare(valid_dataset, valid_features, valid_config, valid_run)

    assert trainer._is_prepared is True
    assert trainer._dataset == valid_dataset
    assert trainer._features == valid_features
    assert trainer._config == valid_config
    assert trainer._run == valid_run


def test_train_execution(valid_dataset, valid_features, valid_config, valid_run):
    """Verify that train() executes and returns correct TrainingResult."""
    trainer = LightGBMTrainer()
    # Implicit preparation during train
    result = trainer.train(valid_dataset, valid_features, valid_config, valid_run)

    assert isinstance(result, TrainingResult)
    assert result.status == "SUCCESS"
    assert trainer._is_trained is True
    assert trainer._dataset == valid_dataset
    assert trainer._features == valid_features
    assert trainer._config == valid_config
    assert trainer._run == valid_run
    assert result.metrics == trainer.collect_metrics()
    assert result.artifacts == trainer.generate_artifact()


def test_evaluate_and_collect_metrics_before_training(valid_dataset):
    """Verify methods raise ValueError if called before train()."""
    trainer = LightGBMTrainer()

    with pytest.raises(ValueError, match="Trainer has not been trained yet"):
        trainer.evaluate(valid_dataset)

    with pytest.raises(ValueError, match="Trainer has not been trained yet"):
        trainer.collect_metrics()

    with pytest.raises(ValueError, match="Trainer has not been trained yet"):
        trainer.generate_artifact()

    with pytest.raises(ValueError, match="Trainer has not been trained yet"):
        trainer.save_artifacts()


def test_evaluate_after_training(valid_dataset, valid_features, valid_config, valid_run):
    """Verify evaluate() runs successfully after training."""
    trainer = LightGBMTrainer()
    trainer.train(valid_dataset, valid_features, valid_config, valid_run)

    # Valid evaluation call
    eval_metrics = trainer.evaluate(valid_dataset)
    assert isinstance(eval_metrics, TrainingMetrics)
    assert len(eval_metrics.loss_history) > 0

    # Invalid evaluation call (missing/invalid dataset)
    with pytest.raises(ValueError, match="DatasetSnapshot must be provided"):
        trainer.evaluate(None)


def test_artifact_generation(valid_dataset, valid_features, valid_config, valid_run):
    """Verify that generated artifact metadata has deterministic hash."""
    trainer = LightGBMTrainer()
    trainer.train(valid_dataset, valid_features, valid_config, valid_run)

    artifact = trainer.generate_artifact()
    assert isinstance(artifact, ArtifactMetadata)
    assert len(artifact.checksum) == 64  # SHA-256 length
    assert artifact.file_path.startswith("/storage/models/lightgbm_")
    assert artifact.size_bytes > 0
    assert artifact.permissions == "chmod 444"

    # save_artifacts should return the same
    saved_artifact = trainer.save_artifacts()
    assert saved_artifact == artifact


def test_cleanup(valid_dataset, valid_features, valid_config, valid_run):
    """Verify cleanup() resets internal state."""
    trainer = LightGBMTrainer()
    trainer.train(valid_dataset, valid_features, valid_config, valid_run)
    assert trainer._is_trained is True

    trainer.cleanup()
    assert trainer._dataset is None
    assert trainer._features is None
    assert trainer._config is None
    assert trainer._run is None
    assert trainer._is_prepared is False
    assert trainer._is_trained is False
    assert trainer._metrics is None
    assert trainer._artifact is None


def test_deterministic_outputs(valid_dataset, valid_features, valid_run):
    """Verify that trainer produces identical results for identical seeds and configuration."""
    config_1 = TrainerConfig(
        model_type="lightgbm",
        seed=100,
        hyperparameters=(("num_leaves", 31),),
        training_parameters=(("epochs", 50),)
    )
    config_2 = TrainerConfig(
        model_type="lightgbm",
        seed=100,
        hyperparameters=(("num_leaves", 31),),
        training_parameters=(("epochs", 50),)
    )
    config_3 = TrainerConfig(
        model_type="lightgbm",
        seed=200,
        hyperparameters=(("num_leaves", 31),),
        training_parameters=(("epochs", 50),)
    )

    trainer_a = LightGBMTrainer()
    trainer_b = LightGBMTrainer()
    trainer_c = LightGBMTrainer()

    res_a = trainer_a.train(valid_dataset, valid_features, config_1, valid_run)
    res_b = trainer_b.train(valid_dataset, valid_features, config_2, valid_run)
    res_c = trainer_c.train(valid_dataset, valid_features, config_3, valid_run)

    # Identical configurations should produce identical metrics and artifacts
    assert res_a.metrics == res_b.metrics
    assert res_a.artifacts.checksum == res_b.artifacts.checksum
    assert res_a.artifacts.file_path == res_b.artifacts.file_path

    # Different configuration (different seed) should produce different metrics/checksum
    assert res_a.metrics != res_c.metrics
    assert res_a.artifacts.checksum != res_c.artifacts.checksum


def test_immutable_outputs(valid_dataset, valid_features, valid_config, valid_run):
    """Verify that the training results and outputs are frozen / immutable."""
    trainer = LightGBMTrainer()
    result = trainer.train(valid_dataset, valid_features, valid_config, valid_run)
    
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.status = "FAILED"  # type: ignore

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.metrics.sharpe = 0.0  # type: ignore

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.artifacts.file_path = "hacked"  # type: ignore
