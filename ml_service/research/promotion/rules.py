"""Research Promotion Rules - Sprint 3.9D-2

Promotion criteria and rule evaluation logic.
"""

from dataclasses import dataclass
from typing import Tuple
from ml_service.research.promotion.models import PromotionStatus


@dataclass(frozen=True)
class PromotionCriteria:
    """Criteria for evaluating model promotion decisions."""
    minimum_score_delta: float = 0.05
    minimum_win_rate: float = 0.55
    maximum_drawdown: float = 0.20

    def __post_init__(self):
        if self.minimum_score_delta < 0:
            raise ValueError("minimum_score_delta must be non-negative")
        if not (0.0 <= self.minimum_win_rate <= 1.0):
            raise ValueError("minimum_win_rate must be in [0.0, 1.0]")
        if not (0.0 <= self.maximum_drawdown <= 1.0):
            raise ValueError("maximum_drawdown must be in [0.0, 1.0]")


def evaluate_promotion_rules(
    candidate_score: float,
    current_score: float,
    metrics: Tuple[Tuple[str, float], ...],
    criteria: PromotionCriteria
) -> Tuple[PromotionStatus, str]:
    """Evaluate promotion rules and return decision with reason.

    Rules:
    - PROMOTE: candidate_score > current_score AND score_delta >= minimum_score_delta
               AND metrics satisfy risk constraints
    - REJECT: candidate_score < current_score
    - HOLD: difference exists but does not exceed promotion threshold

    Args:
        candidate_score: Score of the candidate model
        current_score: Score of the current production model
        metrics: Additional metrics as (name, value) tuples
        criteria: Promotion criteria thresholds

    Returns:
        Tuple of (PromotionStatus, reason string)
    """
    score_delta = candidate_score - current_score
    metrics_dict = dict(metrics)

    if candidate_score < current_score:
        return PromotionStatus.REJECT, f"Candidate score ({candidate_score:.4f}) is lower than current score ({current_score:.4f})"

    if score_delta < criteria.minimum_score_delta:
        return PromotionStatus.HOLD, f"Score improvement ({score_delta:.4f}) below minimum threshold ({criteria.minimum_score_delta:.4f})"

    win_rate = metrics_dict.get("win_rate", 1.0)
    if win_rate < criteria.minimum_win_rate:
        return PromotionStatus.HOLD, f"Win rate ({win_rate:.4f}) below minimum threshold ({criteria.minimum_win_rate:.4f})"

    drawdown = metrics_dict.get("max_drawdown", 0.0)
    if drawdown > criteria.maximum_drawdown:
        return PromotionStatus.HOLD, f"Max drawdown ({drawdown:.4f}) exceeds maximum threshold ({criteria.maximum_drawdown:.4f})"

    return PromotionStatus.PROMOTE, f"Candidate meets all promotion criteria with score improvement of {score_delta:.4f}"
