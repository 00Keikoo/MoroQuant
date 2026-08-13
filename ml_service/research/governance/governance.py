"""Research Governance Engine Implementation - Sprint 3.9D-3

DEPRECATED: Use promotion_engine.engine.PromotionEngine instead.
This module provides backward compatibility only.

Default implementation of governance engine that applies policy rules
to promotion decisions and produces registry proposals.
"""

from ml_service.research.promotion.models import PromotionDecision, PromotionStatus
from ml_service.research.governance.models import GovernanceAction, RegistryProposal
from ml_service.research.governance.interfaces import GovernanceEngine
from ml_service.research.governance.policy import GovernancePolicy
from ml_service.research.promotion_engine.models import PromotionScore, PromotionStatus as CanonicalStatus


class DefaultGovernanceEngine(GovernanceEngine):
    """Default governance engine implementation.

    Applies policy rules to promotion decisions and produces immutable
    registry proposals without executing any registry mutations.

    ADR-024 Compliant:
    - Pure functional
    - Deterministic
    - No database access
    - No registry mutation
    - No deployment actions
    """

    def __init__(self, policy: GovernancePolicy):
        self._policy = policy

    def evaluate(self, promotion_decision: PromotionDecision) -> RegistryProposal:
        """Evaluate a promotion decision and produce a registry proposal.

        Policy rules:
        - REJECT: if promotion decision is REJECT
        - REVIEW: if promotion decision is PROMOTE and manual review required
        - APPROVE: if promotion decision is PROMOTE and score satisfies policy and no manual review

        Args:
            promotion_decision: Immutable promotion decision from the promotion engine

        Returns:
            RegistryProposal: Immutable proposal for registry action
        """
        if promotion_decision.decision == PromotionStatus.REJECT:
            return self._create_reject_proposal(promotion_decision)

        if promotion_decision.decision == PromotionStatus.PROMOTE:
            if self._policy.require_manual_review:
                return self._create_review_proposal(promotion_decision)

            if promotion_decision.candidate_score >= self._policy.minimum_score:
                return self._create_approve_proposal(promotion_decision)

            return self._create_reject_proposal(
                promotion_decision,
                reason=f"Score {promotion_decision.candidate_score:.3f} below minimum {self._policy.minimum_score:.3f}"
            )

        return self._create_review_proposal(
            promotion_decision,
            reason=f"Unknown promotion status: {promotion_decision.decision}"
        )

    def _create_approve_proposal(self, decision: PromotionDecision) -> RegistryProposal:
        """Create an approval proposal."""
        score = PromotionScore(
            model_id=decision.model_id,
            validation_score=decision.candidate_score,
            calibration_score=decision.candidate_score,
            lifecycle_score=decision.candidate_score,
            governance_score=decision.candidate_score,
            total_score=decision.candidate_score,
        )
        return RegistryProposal(
            model_id=decision.model_id,
            symbol="DEPRECATED_TEST",
            asset_class="CRYPTO",
            current_state="VALIDATED",
            proposed_state="APPROVED_RESEARCH",
            status=CanonicalStatus.APPROVED,
            score=score,
            reason_codes=(f"APPROVED: {decision.reason}",),
        )

    def _create_reject_proposal(self, decision: PromotionDecision, reason: str = None) -> RegistryProposal:
        """Create a rejection proposal."""
        score = PromotionScore(
            model_id=decision.model_id,
            validation_score=decision.candidate_score,
            calibration_score=decision.candidate_score,
            lifecycle_score=decision.candidate_score,
            governance_score=decision.candidate_score,
            total_score=decision.candidate_score,
        )
        return RegistryProposal(
            model_id=decision.model_id,
            symbol="DEPRECATED_TEST",
            asset_class="CRYPTO",
            current_state="VALIDATED",
            proposed_state="REJECTED",
            status=CanonicalStatus.REJECTED,
            score=score,
            reason_codes=(reason or f"REJECTED: {decision.reason}",),
        )

    def _create_review_proposal(self, decision: PromotionDecision, reason: str = None) -> RegistryProposal:
        """Create a review proposal."""
        score = PromotionScore(
            model_id=decision.model_id,
            validation_score=decision.candidate_score,
            calibration_score=decision.candidate_score,
            lifecycle_score=decision.candidate_score,
            governance_score=decision.candidate_score,
            total_score=decision.candidate_score,
        )
        return RegistryProposal(
            model_id=decision.model_id,
            symbol="DEPRECATED_TEST",
            asset_class="CRYPTO",
            current_state="VALIDATED",
            proposed_state="GOVERNANCE_READY",
            status=CanonicalStatus.CANDIDATE,
            score=score,
            reason_codes=(reason or f"REVIEW: {decision.reason}",),
        )

    def _normalize_score(self, score_delta: float) -> float:
        """Normalize score delta to [0.0, 1.0] range for promotion_score.

        Score delta can be negative (worse) or positive (better).
        Map to [0.0, 1.0] where 0.5 = no change, >0.5 = improvement, <0.5 = regression.
        """
        return max(0.0, min(1.0, 0.5 + (score_delta / 2.0)))
