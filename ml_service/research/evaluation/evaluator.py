"""Default Signal Evaluator - Sprint 3.9C-3

Implements pure-functional evaluation of trading signals.
"""

from typing import List
from ml_service.research.strategy.models import Signal, SignalAction
from ml_service.research.strategy.inference.models import Prediction
from ml_service.simulation.models import MarketSnapshot
from ml_service.research.evaluation.models import EvaluationResult
from ml_service.research.evaluation.interfaces import SignalEvaluator


class DefaultSignalEvaluator(SignalEvaluator):
    """Default threshold/correctness-based signal evaluator."""

    def evaluate(
        self,
        signal: Signal,
        prediction: Prediction,
        future_snapshots: List[MarketSnapshot],
    ) -> EvaluationResult:
        """Evaluates forward return, direction correctness, and classification hits.

        Pure-functional and deterministic.
        """
        if not future_snapshots:
            raise ValueError("future_snapshots sequence cannot be empty")

        entry_price = future_snapshots[0].mid_price
        exit_price = future_snapshots[-1].mid_price

        # Calculate decimal forward return based on signal direction
        if signal.action == SignalAction.LONG:
            forward_return = (exit_price / entry_price) - 1.0
        elif signal.action == SignalAction.SHORT:
            forward_return = 1.0 - (exit_price / entry_price)
        else:
            forward_return = 0.0

        # Determine price direction
        if exit_price > entry_price:
            actual_direction = "UP"
        elif exit_price < entry_price:
            actual_direction = "DOWN"
        else:
            actual_direction = "FLAT"

        predicted_direction = prediction.direction.upper()
        # Correctness: prediction direction matches actual price direction
        is_correct = (predicted_direction == actual_direction)

        # Hit/miss classification
        is_hit = (forward_return > 0.0) if signal.action in (SignalAction.LONG, SignalAction.SHORT) else (abs(exit_price / entry_price - 1.0) < 0.0005)

        metrics = (
            ("entry_price", entry_price),
            ("exit_price", exit_price),
            ("price_change_pct", (exit_price / entry_price) - 1.0),
        )

        return EvaluationResult(
            signal_timestamp=signal.timestamp,
            action=signal.action.value,
            predicted_direction=predicted_direction,
            actual_direction=actual_direction,
            is_correct=is_correct,
            forward_return=forward_return,
            is_hit=is_hit,
            metrics=metrics,
        )
