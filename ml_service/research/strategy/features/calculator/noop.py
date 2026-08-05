"""No-Op Feature Calculator - Sprint 3.9B-3A

Reference implementation that returns empty features.
Used as default calculator and for testing calculator abstraction.
"""

from typing import Tuple
from ml_service.research.strategy.features.calculator.interfaces import FeatureCalculator
from ml_service.research.strategy.features.context import FeatureContext


class NoOpFeatureCalculator(FeatureCalculator):
    """No-op calculator returning empty features.

    Reference implementation demonstrating calculator contract.
    Used as default before technical indicators are implemented.
    """

    def calculate(self, context: FeatureContext) -> Tuple[Tuple[str, float], ...]:
        """Return empty feature tuple.

        Args:
            context: Feature context (unused in no-op implementation)

        Returns:
            Empty tuple - no features calculated
        """
        return tuple()
