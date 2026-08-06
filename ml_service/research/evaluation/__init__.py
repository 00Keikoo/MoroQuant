"""Research Evaluation Layer - Sprint 3.9C-3

Defines contracts and models for evaluating signals against future outcomes.
"""

from ml_service.research.evaluation.models import EvaluationResult
from ml_service.research.evaluation.interfaces import SignalEvaluator
from ml_service.research.evaluation.evaluator import DefaultSignalEvaluator

__all__ = [
    "EvaluationResult",
    "SignalEvaluator",
    "DefaultSignalEvaluator",
]
