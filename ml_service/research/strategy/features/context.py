"""Feature Context - Sprint 3.9B-2A

Immutable point-in-time market state container following ADR-024.
Maintains rolling window of MarketSnapshot history for feature calculation.
"""

from dataclasses import dataclass, field
from typing import Tuple
from ml_service.simulation.models import MarketSnapshot


@dataclass(frozen=True)
class FeatureContext:
    """Immutable container for point-in-time market information.

    Maintains chronologically ordered MarketSnapshot history.
    Enforces no future data - all snapshots must be at or before timestamp.
    Used as input for feature calculation without side effects.
    """
    symbol: str
    timestamp: str
    window: Tuple[MarketSnapshot, ...] = field(default_factory=tuple)

    def __post_init__(self):
        """Validate chronological ordering and no future data."""
        if not self.window:
            return

        from datetime import datetime
        context_dt = datetime.fromisoformat(self.timestamp.replace('Z', ''))

        prev_snapshot = None
        for snapshot in self.window:
            if snapshot.timestamp > context_dt:
                raise ValueError(
                    f"Future data detected: snapshot at {snapshot.timestamp} "
                    f"exceeds context timestamp {self.timestamp}"
                )

            if prev_snapshot and snapshot.timestamp < prev_snapshot.timestamp:
                raise ValueError(
                    f"Window not chronologically ordered: {snapshot.timestamp} "
                    f"comes after {prev_snapshot.timestamp}"
                )

            prev_snapshot = snapshot
