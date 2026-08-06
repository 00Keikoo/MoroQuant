"""Feature Context Service - Sprint 3.9B-2B

Manages FeatureContext lifecycle within Strategy runtime.
Integrates FeatureBuilder with MarketSnapshot flow following ADR-024.
"""

from typing import Dict
from ml_service.research.strategy.features.context import FeatureContext
from ml_service.research.strategy.features.interfaces import FeatureBuilder
from ml_service.research.strategy.models import FeatureSnapshot
from ml_service.simulation.models import MarketSnapshot


class FeatureContextService:
    """Service for managing feature context lifecycle during strategy execution.

    Responsibilities:
    - Initialize feature context per symbol
    - Update context from MarketSnapshot
    - Generate FeatureSnapshot from context

    Must be:
    - Deterministic (same inputs -> same outputs)
    - Stateless (context passed explicitly)
    - Immutable transitions (no mutation)

    MUST NOT:
    - Mutate StrategyState
    - Mutate Portfolio state
    - Access ExecutionSimulator
    - Access database
    - Load ML models
    - Calculate technical indicators (delegated to FeatureBuilder)
    """

    def __init__(self, feature_builder: FeatureBuilder):
        """Initialize service with feature builder.

        Args:
            feature_builder: FeatureBuilder implementation for feature calculation
        """
        self._feature_builder = feature_builder
        self._contexts: Dict[str, FeatureContext] = {}

    def initialize_context(self, symbol: str) -> FeatureContext:
        """Initialize empty feature context for a symbol.

        Args:
            symbol: Trading symbol identifier

        Returns:
            Empty FeatureContext with no window data

        Rules:
            - Pure function
            - No side effects
            - Creates new context
        """
        context = self._feature_builder.initialize(symbol)
        self._contexts[symbol] = context
        return context

    def update_context(
        self,
        symbol: str,
        market_snapshot: MarketSnapshot,
    ) -> FeatureContext:
        """Update feature context with new market snapshot.

        Creates new context with snapshot added to rolling window.
        Original context remains unchanged (immutability).

        Args:
            symbol: Trading symbol identifier
            market_snapshot: New market data to incorporate

        Returns:
            New FeatureContext with updated window

        Raises:
            ValueError: If context not initialized for symbol
            ValueError: If snapshot timestamp violates chronological ordering

        Rules:
            - Pure function
            - No side effects
            - Returns new context
            - Original context unchanged
        """
        if symbol not in self._contexts:
            raise ValueError(f"Context not initialized for symbol: {symbol}")

        current_context = self._contexts[symbol]
        updated_context = self._feature_builder.update(current_context, market_snapshot)
        self._contexts[symbol] = updated_context
        return updated_context

    def build_snapshot(self, symbol: str) -> FeatureSnapshot:
        """Generate feature snapshot from current context.

        Args:
            symbol: Trading symbol identifier

        Returns:
            Immutable FeatureSnapshot with calculated features

        Raises:
            ValueError: If context not initialized for symbol

        Rules:
            - Pure function
            - No side effects
            - Deterministic output
        """
        if symbol not in self._contexts:
            raise ValueError(f"Context not initialized for symbol: {symbol}")

        context = self._contexts[symbol]
        return self._feature_builder.build(context)

    def get_context(self, symbol: str) -> FeatureContext:
        """Get current feature context for symbol.

        Args:
            symbol: Trading symbol identifier

        Returns:
            Current FeatureContext

        Raises:
            ValueError: If context not initialized for symbol

        Rules:
            - Pure getter
            - No side effects
        """
        if symbol not in self._contexts:
            raise ValueError(f"Context not initialized for symbol: {symbol}")

        return self._contexts[symbol]

    def has_context(self, symbol: str) -> bool:
        """Check if context exists for symbol.

        Args:
            symbol: Trading symbol identifier

        Returns:
            True if context initialized, False otherwise

        Rules:
            - Pure function
            - No side effects
        """
        return symbol in self._contexts

    def reset(self) -> None:
        """Clear all feature contexts.

        Used for simulation reset or cleanup.

        Rules:
            - Idempotent
            - No side effects beyond clearing state
        """
        self._contexts.clear()
