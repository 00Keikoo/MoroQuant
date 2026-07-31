"""Tests for BaseTrainer and related data structures."""

import pytest
import dataclasses
from typing import Any
from ml_service.research.trainers.base_trainer import (
    BaseTrainer,
    TrainerConfig,
    TrainingMetrics,
    ArtifactMetadata,
    TrainingResult
)


def test_base_trainer_cannot_be_instantiated():
    """Verify that BaseTrainer cannot be instantiated directly because it is an abstract class."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class BaseTrainer"):
        BaseTrainer()  # type: ignore


class DummyTrainer(BaseTrainer):
    """A dummy implementation of BaseTrainer for testing."""
    def validate(self, dataset: Any, features: Any, config: TrainerConfig) -> None:
        pass

    def train(self, dataset: Any, features: Any, config: TrainerConfig) -> None:
        pass

    def evaluate(self, dataset: Any) -> TrainingMetrics:
        return TrainingMetrics((), (), 0.0, 0.0, 0.0, 0.0)

    def collect_metrics(self) -> TrainingMetrics:
        return TrainingMetrics((), (), 0.0, 0.0, 0.0, 0.0)

    def generate_artifact(self) -> ArtifactMetadata:
        return ArtifactMetadata("", "", 0, "")

    def cleanup(self) -> None:
        pass


def test_dummy_trainer_instantiation_and_methods():
    """Verify that a subclass implementing all abstract methods can be instantiated and called."""
    trainer = DummyTrainer()
    config = TrainerConfig("xgboost", 42)
    
    # Test method invocation works without errors
    trainer.validate(None, None, config)
    trainer.train(None, None, config)
    
    metrics = trainer.evaluate(None)
    assert isinstance(metrics, TrainingMetrics)
    
    metrics_collected = trainer.collect_metrics()
    assert isinstance(metrics_collected, TrainingMetrics)
    
    artifact = trainer.generate_artifact()
    assert isinstance(artifact, ArtifactMetadata)
    
    trainer.cleanup()


def test_immutable_outputs_and_configs():
    """Verify that all trainer structures (configs, metrics, results) are frozen and immutable."""
    config = TrainerConfig(
        model_type="xgboost",
        seed=123,
        hyperparameters=(("max_depth", 6),),
        training_parameters=(("epochs", 100),)
    )
    
    metrics = TrainingMetrics(
        loss_history=(0.5, 0.2),
        val_loss_history=(0.6, 0.25),
        sharpe=2.5,
        ece=0.03,
        brier=0.12,
        drawdown=0.08
    )
    
    artifact = ArtifactMetadata(
        checksum="sha-hash",
        file_path="/path/to/model",
        size_bytes=1024,
        permissions="chmod 444"
    )
    
    result = TrainingResult(
        status="SUCCESS",
        metrics=metrics,
        artifacts=artifact,
        error_message=None
    )

    # Asserts that instances are read-only
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.seed = 999  # type: ignore

    with pytest.raises(dataclasses.FrozenInstanceError):
        metrics.sharpe = 9.9  # type: ignore

    with pytest.raises(dataclasses.FrozenInstanceError):
        artifact.file_path = "/mutated"  # type: ignore

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.status = "MUTATED"  # type: ignore


def test_trainer_config_creation():
    """Verify TrainerConfig fields are populated correctly."""
    config = TrainerConfig("lightgbm", 7, (("lr", 0.05),), (("early_stopping", 5),))
    assert config.model_type == "lightgbm"
    assert config.seed == 7
    assert config.hyperparameters == (("lr", 0.05),)
    assert config.training_parameters == (("early_stopping", 5),)


def test_training_result_creation():
    """Verify TrainingResult properties are populated correctly."""
    metrics = TrainingMetrics((0.1,), (0.2,), 1.2, 0.05, 0.1, 0.15)
    artifact = ArtifactMetadata("chk", "path", 10, "perm")
    result = TrainingResult("FAILED_TRAINING", metrics, artifact, "Some error occurred")
    
    assert result.status == "FAILED_TRAINING"
    assert result.metrics == metrics
    assert result.artifacts == artifact
    assert result.error_message == "Some error occurred"
