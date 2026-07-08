"""Evaluation Engine - Quant Metrics Layer.

Computes statistical performance metrics and ranks experiment strategies.
"""

from ml_service.research.evaluation_engine.types import (
    StrategyScore,
    EvaluationResult,
)
from ml_service.research.evaluation_engine.engine import (
    compute_strategy_score,
    evaluate_experiment,
)
from ml_service.research.evaluation_engine.service import EvaluationService

__all__ = [
    "StrategyScore",
    "EvaluationResult",
    "compute_strategy_score",
    "evaluate_experiment",
    "EvaluationService",
]
