"""Feature Builder Interface - Sprint 3.9B-2A

Abstract interface for feature calculation following ADR-024.
All implementations must be pure functions with no side effects.
"""

from abc import ABC, abstractmethod
from ml_service.research.strategy.features.context import FeatureContext
from ml_service.research.strategy.models import FeatureSnapshot
from ml_service.simulation.models import MarketSnapshot


class FeatureBuilder(ABC):
    """Abstract builder for feature context and snapshot creation.

    All methods must be pure functions:
    - No database access
    - No ML model loading
    - No portfolio state access
    - No order creation
    - Deterministic output for same inputs
    """

    @abstractmethod
    def initialize(self, symbol: str) -> FeatureContext:
        """Create initial empty feature context for a symbol.

        Args:
            symbol: Trading symbol identifier

        Returns:
            Empty FeatureContext with no window data
        """
        pass

    @abstractmethod
    def update(self, context: FeatureContext, snapshot: MarketSnapshot) -> FeatureContext:
        """Create new context with updated market snapshot.

        Must be pure function - original context unchanged.
        Enforces chronological ordering and no future data.

        Args:
            context: Current immutable feature context
            snapshot: New market snapshot to incorporate

        Returns:
            New FeatureContext with snapshot added to window

        Raises:
            ValueError: If snapshot timestamp violates ordering or contains future data
        """
        pass

    @abstractmethod
    def build(self, context: FeatureContext) -> FeatureSnapshot:
        """Generate feature snapshot from context.

        Must be pure function with deterministic output.
        No ML inference or external state access.

        Args:
            context: Current feature context with market window

        Returns:
            Immutable FeatureSnapshot with calculated features
        """
        pass
