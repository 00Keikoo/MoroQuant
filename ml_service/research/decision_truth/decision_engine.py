"""Decision Engine - deterministic trading decision logic."""

from typing import Literal
from .types import DecisionContext, DecisionResult


class DecisionEngine:
    """Deterministic decision engine for trading actions.

    This is the single source of truth for decision logic.
    Must be used by Replay Engine, Experiment Engine, and Evaluation Engine.
    """

    DEFAULT_THRESHOLD = 0.5

    def __init__(self, threshold_long: float = DEFAULT_THRESHOLD, threshold_short: float = DEFAULT_THRESHOLD):
        """Initialize decision engine with fixed thresholds.

        Args:
            threshold_long: Threshold for LONG decisions (default 0.5)
            threshold_short: Threshold for SHORT decisions (default 0.5)
        """
        if not 0.0 <= threshold_long <= 1.0:
            raise ValueError(f"threshold_long must be between 0.0 and 1.0, got {threshold_long}")
        if not 0.0 <= threshold_short <= 1.0:
            raise ValueError(f"threshold_short must be between 0.0 and 1.0, got {threshold_short}")
        self._threshold_long = threshold_long
        self._threshold_short = threshold_short

    @property
    def threshold_long(self) -> float:
        """Get the configured LONG threshold."""
        return self._threshold_long

    @property
    def threshold_short(self) -> float:
        """Get the configured SHORT threshold."""
        return self._threshold_short

    def decide(self, context: DecisionContext) -> DecisionResult:
        """Make deterministic trading decision based on context.

        Pure function with no side effects. Same input always produces same output.
        Uses argmax logic matching production signal generation (predictor.py).

        Args:
            context: Decision context with probabilities and metadata

        Returns:
            DecisionResult with action, confidence, and reasoning
        """
        prob_short = context.probability_short
        prob_neutral = context.probability_neutral
        prob_long = context.probability_long

        # Equal probability handling:
        if prob_long == prob_short:
            action = "HOLD"
            confidence = max(prob_long, prob_short, prob_neutral)
            threshold_used = max(self._threshold_long, self._threshold_short)
            reason_code = ["PROBABILITIES_EQUAL"]
            return DecisionResult(
                action=action,
                confidence=confidence,
                threshold_used=threshold_used,
                reason_code=reason_code
            )

        # Argmax logic matching production signal generation (predictor.py)
        probs = [prob_short, prob_neutral, prob_long]
        prediction = int(max(range(len(probs)), key=lambda i: probs[i]))

        direction_map = {0: 'SHORT', 1: 'HOLD', 2: 'LONG'}
        argmax_action = direction_map[prediction]
        confidence = probs[prediction]

        reason_code: list[str] = []

        if argmax_action == "LONG":
            threshold_used = self._threshold_long
            # Threshold boundary behavior: probability > threshold only
            if confidence > self._threshold_long:
                action = "LONG"
                reason_code.append("LONG_PROBABILITY_EXCEEDS_THRESHOLD")
            else:
                action = "HOLD"
                if prob_long <= self._threshold_long and prob_short <= self._threshold_short:
                    reason_code.append("BOTH_PROBABILITIES_BELOW_THRESHOLD")
                else:
                    reason_code.append("CONFIDENCE_BELOW_LONG_THRESHOLD")
            reason_code.append(f"LONG_PROB_{prob_long:.3f}_GT_SHORT_{prob_short:.3f}_NEUTRAL_{prob_neutral:.3f}")

        elif argmax_action == "SHORT":
            threshold_used = self._threshold_short
            if confidence > self._threshold_short:
                action = "SHORT"
                reason_code.append("SHORT_PROBABILITY_EXCEEDS_THRESHOLD")
            else:
                action = "HOLD"
                if prob_long <= self._threshold_long and prob_short <= self._threshold_short:
                    reason_code.append("BOTH_PROBABILITIES_BELOW_THRESHOLD")
                else:
                    reason_code.append("CONFIDENCE_BELOW_SHORT_THRESHOLD")
            reason_code.append(f"SHORT_PROB_{prob_short:.3f}_GT_LONG_{prob_long:.3f}_NEUTRAL_{prob_neutral:.3f}")

        else:
            action = "HOLD"
            threshold_used = max(self._threshold_long, self._threshold_short)
            if prob_long <= self._threshold_long and prob_short <= self._threshold_short:
                reason_code.append("BOTH_PROBABILITIES_BELOW_THRESHOLD")
            else:
                reason_code.append("ARGMAX_NEUTRAL")
            reason_code.append(f"NEUTRAL_PROB_{prob_neutral:.3f}_GT_LONG_{prob_long:.3f}_SHORT_{prob_short:.3f}")

        return DecisionResult(
            action=action,
            confidence=confidence,
            threshold_used=threshold_used,
            reason_code=reason_code
        )
