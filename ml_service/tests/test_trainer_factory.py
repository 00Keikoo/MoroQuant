"""Tests for TrainerFactory."""

import pytest
from ml_service.research.trainers.trainer_factory import TrainerFactory
from ml_service.research.trainers.xgboost_trainer import XGBoostTrainer
from ml_service.research.trainers.lightgbm_trainer import LightGBMTrainer


def test_create_xgboost():
    """Verify that TrainerFactory successfully creates an XGBoostTrainer instance."""
    trainer = TrainerFactory.create("xgboost")
    assert isinstance(trainer, XGBoostTrainer)


def test_create_lightgbm():
    """Verify that TrainerFactory successfully creates a LightGBMTrainer instance."""
    trainer = TrainerFactory.create("lightgbm")
    assert isinstance(trainer, LightGBMTrainer)


def test_invalid_algorithm():
    """Verify that TrainerFactory raises ValueError for invalid or unsupported algorithms."""
    # Unknown string
    with pytest.raises(ValueError, match="Unknown algorithm 'invalid_algo'"):
        TrainerFactory.create("invalid_algo")

    # Invalid type
    with pytest.raises(ValueError, match="Algorithm name must be a string"):
        TrainerFactory.create(12345)  # type: ignore

    with pytest.raises(ValueError, match="Algorithm name must be a string"):
        TrainerFactory.create(None)  # type: ignore


def test_returned_object_type():
    """Verify the factory returns subclass instances of BaseTrainer and proper types."""
    from ml_service.research.trainers.base_trainer import BaseTrainer

    xgboost_trainer = TrainerFactory.create("xgboost")
    lightgbm_trainer = TrainerFactory.create("lightgbm")

    assert isinstance(xgboost_trainer, BaseTrainer)
    assert isinstance(lightgbm_trainer, BaseTrainer)


def test_deterministic_behavior():
    """Verify that calling the factory with the same parameters repeatedly returns instances of the expected class."""
    for _ in range(5):
        assert isinstance(TrainerFactory.create("xgboost"), XGBoostTrainer)
        assert isinstance(TrainerFactory.create("lightgbm"), LightGBMTrainer)


def test_no_shared_mutable_state():
    """Verify that different calls to TrainerFactory.create return distinct instances with no shared mutable state."""
    trainer_a = TrainerFactory.create("xgboost")
    trainer_b = TrainerFactory.create("xgboost")
    
    # Verify that the two instances are distinct objects
    assert trainer_a is not trainer_b

    # Verify mutating one does not affect the other
    trainer_a._is_trained = True
    assert trainer_b._is_trained is False

    trainer_c = TrainerFactory.create("lightgbm")
    trainer_d = TrainerFactory.create("lightgbm")
    
    assert trainer_c is not trainer_d
    trainer_c._is_prepared = True
    assert trainer_d._is_prepared is False
