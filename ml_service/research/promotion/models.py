"""Research Promotion Models - Sprint 3.9D-2

Immutable domain models representing promotion decision outputs.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple, Dict, Any


class PromotionStatus(Enum):
    """Status of a model promotion decision."""
    PROMOTE = "PROMOTE"
    REJECT = "REJECT"
    HOLD = "HOLD"


@dataclass(frozen=True)
class PromotionDecision:
    """Immutable promotion decision for a candidate model.

    Adheres to ADR-024 compliance with strict immutability and deterministic serialization.
    """
    model_id: str
    decision: PromotionStatus
    reason: str
    candidate_score: float
    current_score: float
    score_delta: float
    metrics: Tuple[Tuple[str, float], ...] = field(default_factory=tuple)

    def __post_init__(self):
        if not self.model_id:
            raise ValueError("model_id cannot be empty")
        if not self.reason:
            raise ValueError("reason cannot be empty")
        if not (-1.0 <= self.candidate_score <= 1.0):
            raise ValueError(f"candidate_score must be in [-1.0, 1.0], got {self.candidate_score}")
        if not (-1.0 <= self.current_score <= 1.0):
            raise ValueError(f"current_score must be in [-1.0, 1.0], got {self.current_score}")

        if not isinstance(self.decision, PromotionStatus):
            object.__setattr__(self, 'decision', PromotionStatus(self.decision))
        if not isinstance(self.metrics, tuple):
            object.__setattr__(self, 'metrics', tuple(self.metrics))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the promotion decision into a dictionary with sorted collections for determinism."""
        sorted_metrics = sorted(self.metrics, key=lambda x: x[0])
        return {
            "model_id": self.model_id,
            "decision": self.decision.value,
            "reason": self.reason,
            "candidate_score": self.candidate_score,
            "current_score": self.current_score,
            "score_delta": self.score_delta,
            "metrics": [list(x) for x in sorted_metrics],
        }

    def to_json(self) -> str:
        """Deterministic JSON serialization of the promotion decision."""
        return json.dumps(self.to_dict(), sort_keys=True)
