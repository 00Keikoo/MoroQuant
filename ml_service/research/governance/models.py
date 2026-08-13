"""Research Governance Models - Sprint 3.9D-3

DEPRECATED: This module is part of the legacy promotion system.
The active research governance path uses:
- promotion_engine.models.RegistryProposal (canonical)
- promotion_engine.engine.PromotionEngine
- promotion_workflow.workflow.PromotionWorkflow

Immutable domain models representing governance outputs and registry proposals.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple, Dict, Any


class GovernanceAction(Enum):
    """Action to be taken on a model promotion."""
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REVIEW = "REVIEW"


@dataclass(frozen=True)
class RegistryProposal:
    """Immutable registry proposal for a candidate model.

    Adheres to ADR-024 compliance with strict immutability and deterministic serialization.
    Represents the governance decision without executing any registry mutations.
    """
    model_id: str
    action: GovernanceAction
    reason: str
    promotion_score: float
    benchmark_score: float
    metadata: Tuple[Tuple[str, Any], ...] = field(default_factory=tuple)

    def __post_init__(self):
        if not self.model_id:
            raise ValueError("model_id cannot be empty")
        if not self.reason:
            raise ValueError("reason cannot be empty")
        if not (0.0 <= self.promotion_score <= 1.0):
            raise ValueError(f"promotion_score must be in [0.0, 1.0], got {self.promotion_score}")
        if not (-1.0 <= self.benchmark_score <= 1.0):
            raise ValueError(f"benchmark_score must be in [-1.0, 1.0], got {self.benchmark_score}")

        if not isinstance(self.action, GovernanceAction):
            object.__setattr__(self, 'action', GovernanceAction(self.action))
        if not isinstance(self.metadata, tuple):
            object.__setattr__(self, 'metadata', tuple(self.metadata))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the registry proposal into a dictionary with sorted collections for determinism."""
        sorted_metadata = sorted(self.metadata, key=lambda x: x[0])
        return {
            "model_id": self.model_id,
            "action": self.action.value,
            "reason": self.reason,
            "promotion_score": self.promotion_score,
            "benchmark_score": self.benchmark_score,
            "metadata": [list(x) for x in sorted_metadata],
        }

    def to_json(self) -> str:
        """Deterministic JSON serialization of the registry proposal."""
        return json.dumps(self.to_dict(), sort_keys=True)
