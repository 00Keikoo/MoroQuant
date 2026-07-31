"""Trainer Factory implementation for MoroQuant Research Platform."""

from typing import Any, Dict, Type
from ml_service.research.trainers.base_trainer import BaseTrainer
from ml_service.research.trainers.xgboost_trainer import XGBoostTrainer
from ml_service.research.trainers.lightgbm_trainer import LightGBMTrainer


class TrainerFactory:
    """
    Factory for selecting and instantiating appropriate trainer implementations.
    Strictly isolated with no side effects.
    """

    _registry: Dict[str, Type[BaseTrainer]] = {
        "xgboost": XGBoostTrainer,
        "lightgbm": LightGBMTrainer,
    }

    @classmethod
    def create(cls, algorithm: str, **kwargs: Any) -> BaseTrainer:
        """
        Create a trainer instance for the given algorithm.
        
        Args:
            algorithm: Name of the algorithm (e.g., 'xgboost', 'lightgbm').
            **kwargs: Extensible keyword arguments passed to the trainer constructor.
            
        Returns:
            An instance of a concrete BaseTrainer subclass.
            
        Raises:
            ValueError: If the algorithm is not supported/registered.
        """
        if not isinstance(algorithm, str):
            raise ValueError("Algorithm name must be a string.")

        if algorithm not in cls._registry:
            raise ValueError(
                f"Unknown algorithm '{algorithm}'. Supported algorithms: {list(cls._registry.keys())}"
            )

        trainer_class = cls._registry[algorithm]
        return trainer_class(**kwargs)
