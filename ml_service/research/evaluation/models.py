"""Evaluation Models - Sprint 3.9C-3

Immutable models representing evaluation results.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Tuple


@dataclass(frozen=True)
class EvaluationResult:
    """Immutable evaluation metrics scorecard for a single signal prediction.

    Ensures deterministic, side-effect-free replay tracking.
    """
    signal_timestamp: str
    action: str
    predicted_direction: str
    actual_direction: str
    is_correct: bool
    forward_return: float
    is_hit: bool
    metrics: Tuple[Tuple[str, float], ...] = field(default_factory=tuple)

    def __post_init__(self):
        if not self.signal_timestamp:
            raise ValueError("signal_timestamp cannot be empty")
        if not self.action:
            raise ValueError("action cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        sorted_metrics = sorted(self.metrics, key=lambda x: x[0])
        return {
            "signal_timestamp": self.signal_timestamp,
            "action": self.action,
            "predicted_direction": self.predicted_direction,
            "actual_direction": self.actual_direction,
            "is_correct": self.is_correct,
            "forward_return": self.forward_return,
            "is_hit": self.is_hit,
            "metrics": [list(x) for x in sorted_metrics],
        }
