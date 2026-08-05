"""Feature Calculator Interface - Sprint 3.9B-3A

Abstract interface for feature calculation logic following ADR-024.
Separates calculation from builder orchestration.
"""

from abc import ABC, abstractmethod
from typing import Tuple
from ml_service.research.strategy.features.context import FeatureContext


class FeatureCalculator(ABC):
    """Abstract calculator for feature computation.

    All implementations must be pure functions:

    Requirements:
    - deterministic output
    - no external state mutation
    - no external system dependency
    """

    @abstractmethod
    def calculate(self, context: FeatureContext) -> Tuple[Tuple[str, float], ...]:
        """Calculate features from context.

        Pure function with deterministic output.
        No side effects or external state access.

        Args:
            context: Immutable feature context with market window

        Returns:
            Tuple of (feature_name, feature_value) pairs
            Example: (("rsi_14", 45.2), ("ema_20", 150.3))
        """
        pass
