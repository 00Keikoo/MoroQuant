"""Service layer for Decision Truth Layer."""

from typing import List
from .decision_engine import DecisionEngine
from .types import DecisionContext, DecisionResult


class DecisionTruthService:
    """Service layer for decision truth operations.

    Provides batch processing and convenience methods around DecisionEngine.
    """

    def __init__(self, threshold_long: float = DecisionEngine.DEFAULT_THRESHOLD,
                 threshold_short: float = DecisionEngine.DEFAULT_THRESHOLD):
        """Initialize decision truth service.

        Args:
            threshold_long: Threshold for LONG decisions
            threshold_short: Threshold for SHORT decisions
        """
        self._engine = DecisionEngine(threshold_long=threshold_long, threshold_short=threshold_short)

    @property
    def engine(self) -> DecisionEngine:
        """Get the underlying decision engine."""
        return self._engine

    @property
    def threshold_long(self) -> float:
        """Get the configured LONG threshold."""
        return self._engine.threshold_long

    @property
    def threshold_short(self) -> float:
        """Get the configured SHORT threshold."""
        return self._engine.threshold_short

    def decide(self, context: DecisionContext) -> DecisionResult:
        """Make single decision.

        Args:
            context: Decision context

        Returns:
            Decision result
        """
        return self._engine.decide(context)

    def decide_batch(self, contexts: List[DecisionContext]) -> List[DecisionResult]:
        """Make batch decisions.

        Args:
            contexts: List of decision contexts

        Returns:
            List of decision results in same order
        """
        return [self._engine.decide(ctx) for ctx in contexts]
