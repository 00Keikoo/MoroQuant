"""Research Governance Policy - Sprint 3.9D-3

Policy rules for evaluating promotion decisions and determining governance actions.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GovernancePolicy:
    """Policy for evaluating model promotion decisions.

    Defines thresholds and requirements for automatic approval vs manual review.
    """
    minimum_score: float = 0.75
    require_manual_review: bool = True

    def __post_init__(self):
        if not (0.0 <= self.minimum_score <= 1.0):
            raise ValueError(f"minimum_score must be in [0.0, 1.0], got {self.minimum_score}")
