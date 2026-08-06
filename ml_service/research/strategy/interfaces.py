"""Strategy Interface - Sprint 3.9B-1

Abstract interface for strategy implementations following ADR-024.
Pure functional state transitions - no side effects.
"""

from abc import ABC, abstractmethod
from typing import Optional
from ml_service.simulation.models import MarketSnapshot
from ml_service.research.strategy.models import (
    StrategyState,
    StrategyResult,
    FeatureSnapshot,
)
from ml_service.research.strategy.inference.models import Prediction


class Strategy(ABC):
    """Abstract strategy interface.

    All implementations must be:
    - Pure functional (no side effects)
    - Deterministic (same input -> same output)
    - Stateless (state passed explicitly)

    MUST NOT:
    - Access PortfolioService
    - Mutate SimulationState
    - Write to database
    - Create fills
    - Execute orders
    """

    @abstractmethod
    def initialize(self, state: StrategyState) -> StrategyState:
        """Initialize strategy state.

        Args:
            state: Initial strategy state

        Returns:
            Initialized strategy state (may be same or modified)

        Rules:
            - Pure function
            - No side effects
            - Returns new state via replace() if modified
        """
        pass

    @abstractmethod
    def process(
        self,
        market_snapshot: MarketSnapshot,
        state: StrategyState,
        feature_snapshot: Optional[FeatureSnapshot] = None,
        prediction: Optional[Prediction] = None,
    ) -> StrategyResult:
        """Process market snapshot and produce strategy decision.

        Args:
            market_snapshot: Current market data
            state: Current strategy state
            feature_snapshot: Optional container for calculated features
            prediction: Optional model inference output

        Returns:
            StrategyResult containing:
            - new_state: Updated strategy state
            - signal: Optional trading signal

        Rules:
            - Pure function
            - No side effects
            - Deterministic output
            - Returns new state, never mutates input
            - Signal is decision only, NOT order execution
        """
        pass
