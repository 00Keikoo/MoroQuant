"""Default Feature Builder - Sprint 3.9B-2A / 3.9B-3A

Reference implementation of FeatureBuilder interface.
Maintains rolling window and delegates calculation to FeatureCalculator.
"""

from dataclasses import replace
from datetime import datetime
from ml_service.research.strategy.features.context import FeatureContext
from ml_service.research.strategy.features.interfaces import FeatureBuilder
from ml_service.research.strategy.features.calculator import FeatureCalculator, NoOpFeatureCalculator
from ml_service.research.strategy.models import FeatureSnapshot
from ml_service.simulation.models import MarketSnapshot


class DefaultFeatureBuilder(FeatureBuilder):
    """Default feature builder with rolling window management.

    Responsibilities:
    - Maintain chronologically ordered rolling window
    - Enforce timestamp ordering
    - Delegate feature calculation to injected calculator

    Does NOT:
    - Calculate technical indicators directly
    - Call ML models
    - Access database
    - Access portfolio state
    """

    def __init__(self, window_size: int = 100, calculator: FeatureCalculator = None):
        """Initialize builder with window size and calculator.

        Args:
            window_size: Maximum number of snapshots to retain in window
            calculator: FeatureCalculator instance for feature computation
                       Defaults to NoOpFeatureCalculator if not provided
        """
        self.window_size = window_size
        self.calculator = calculator if calculator is not None else NoOpFeatureCalculator()

    def initialize(self, symbol: str) -> FeatureContext:
        """Create empty feature context for symbol.

        Args:
            symbol: Trading symbol identifier

        Returns:
            Empty FeatureContext with no window data
        """
        return FeatureContext(
            symbol=symbol,
            timestamp=datetime.now().isoformat() + 'Z',
            window=tuple()
        )

    def update(self, context: FeatureContext, snapshot: MarketSnapshot) -> FeatureContext:
        """Create new context with snapshot added to window.

        Pure function - original context unchanged.
        Enforces chronological ordering and window size limit.

        Args:
            context: Current immutable feature context
            snapshot: New market snapshot to add

        Returns:
            New FeatureContext with updated window

        Raises:
            ValueError: If snapshot timestamp is before last window timestamp
        """
        if context.window:
            last_snapshot = context.window[-1]
            if snapshot.timestamp < last_snapshot.timestamp:
                raise ValueError(
                    f"Snapshot timestamp {snapshot.timestamp} is before "
                    f"last window timestamp {last_snapshot.timestamp}"
                )

        new_window = context.window + (snapshot,)

        if len(new_window) > self.window_size:
            new_window = new_window[-self.window_size:]

        snapshot_ts = snapshot.timestamp.isoformat()
        if not snapshot_ts.endswith('Z'):
            snapshot_ts += 'Z'

        return replace(
            context,
            timestamp=snapshot_ts,
            window=new_window
        )

    def build(self, context: FeatureContext) -> FeatureSnapshot:
        """Generate feature snapshot using injected calculator.

        Delegates feature calculation to calculator instance.
        Pure function with deterministic output.

        Args:
            context: Current feature context

        Returns:
            FeatureSnapshot with calculated features
        """
        features = self.calculator.calculate(context)

        return FeatureSnapshot(
            timestamp=context.timestamp,
            features=features,
            schema_version="1.0.0"
        )
