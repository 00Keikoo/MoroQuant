"""Signal Evaluator Interface - Sprint 3.9C-3

Abstract interface for evaluating signal performance.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from ml_service.research.strategy.models import Signal
from ml_service.research.strategy.inference.models import Prediction
from ml_service.simulation.models import MarketSnapshot
from ml_service.research.evaluation.models import EvaluationResult


class SignalEvaluator(ABC):
    """Abstract interface for evaluating signal and prediction correctness against future data.

    All implementations must be:
    - Pure functional (no side effects)
    - Deterministic (same input -> same output)
    - Stateless (no execution dependencies)

    MUST NOT:
    - Access PortfolioService
    - Access database
    - Access ExecutionSimulator
    """

    @abstractmethod
    def evaluate(
        self,
        signal: Signal,
        prediction: Prediction,
        future_snapshots: List[MarketSnapshot],
    ) -> EvaluationResult:
        """Evaluate a signal and prediction against future market snapshots.

        Args:
            signal: Generated trading signal
            prediction: ML inference prediction
            future_snapshots: Future chronological sequence of market snapshots

        Returns:
            Immutable EvaluationResult metrics scorecard
        """
        pass
