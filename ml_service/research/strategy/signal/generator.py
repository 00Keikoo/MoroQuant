"""Default Signal Generator - Sprint 3.9C-1

Implements threshold-based prediction gating to generate signals.
"""

from typing import Optional
from ml_service.research.strategy.models import Signal, SignalAction, StrategyState, FeatureSnapshot
from ml_service.research.strategy.inference.models import Prediction
from ml_service.research.strategy.signal.interfaces import SignalGenerator


class DefaultSignalGenerator(SignalGenerator):
    """Default signal generator using threshold-based prediction gating.

    Maps prediction probabilities to LONG, SHORT, or FLAT signals.
    """

    def __init__(self, entry_threshold: float = 0.6, exit_threshold: float = 0.5):
        """Initialize generator with entry/exit threshold gates.

        Args:
            entry_threshold: Confidence required to enter a LONG or SHORT position.
            exit_threshold: Confidence level below which position reverts to FLAT.
        """
        if not (0.0 <= exit_threshold <= entry_threshold <= 1.0):
            raise ValueError("Thresholds must satisfy: 0.0 <= exit_threshold <= entry_threshold <= 1.0")
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold

    def generate(
        self,
        prediction: Prediction,
        features: Optional[FeatureSnapshot],
        state: StrategyState,
    ) -> Optional[Signal]:
        """Maps prediction probabilities to trading signals using configured thresholds.

        Pure-functional and deterministic.
        """
        probability = prediction.probability
        direction = prediction.direction.upper()

        if probability >= self.entry_threshold:
            if direction in ("LONG", "UP", "BUY"):
                action = SignalAction.LONG
            elif direction in ("SHORT", "DOWN", "SELL"):
                action = SignalAction.SHORT
            else:
                action = SignalAction.FLAT
        elif probability < self.exit_threshold:
            action = SignalAction.FLAT
        else:
            # Inside the deadband zone - do not output a new action change signal
            return None

        # Build immutable metadata tuple
        metadata = (
            ("model_version_id", prediction.model_version_id),
            ("probability", probability),
            ("direction", direction),
            ("entry_threshold", self.entry_threshold),
            ("exit_threshold", self.exit_threshold),
        )

        return Signal(
            timestamp=prediction.timestamp,
            action=action,
            confidence=probability,
            metadata=metadata,
        )
