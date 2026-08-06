"""Signal Generator Interface - Sprint 3.9C-1

Abstract interface for mapping predictions and features to trading signals.
"""

from abc import ABC, abstractmethod
from typing import Optional
from ml_service.research.strategy.models import Signal, StrategyState, FeatureSnapshot
from ml_service.research.strategy.inference.models import Prediction


class SignalGenerator(ABC):
    """Abstract interface for mapping predictions and features to trading signals.

    All implementations must be:
    - Pure functional (no side effects)
    - Deterministic (same input -> same output)
    - Stateless (no internal execution state)

    MUST NOT:
    - Access PortfolioService
    - Mutate StrategyState
    - Access database
    - Access ExecutionSimulator
    """

    @abstractmethod
    def generate(
        self,
        prediction: Prediction,
        features: Optional[FeatureSnapshot],
        state: StrategyState,
    ) -> Optional[Signal]:
        """Generate trading signal from ML prediction outputs and features.

        Args:
            prediction: Ingested ML model prediction
            features: Optional calculated feature snapshots
            state: Current strategy state

        Returns:
            Optional Signal if signal triggered, None otherwise
        """
        pass
