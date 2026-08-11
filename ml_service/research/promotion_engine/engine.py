"""Promotion Engine - Sprint 3.9D-8

Deterministic promotion decision engine orchestrating scoring and policy.
ADR-024 compliant: research layer only, no database, immutable outputs.
"""

from ml_service.research.promotion_engine.models import RegistryProposal
from ml_service.research.promotion_engine.scorer import PromotionScorer
from ml_service.research.promotion_engine.policy import PromotionPolicy
from ml_service.research.model_identity.models import ModelIdentity
from ml_service.research.model_lifecycle.models import ModelLifecycleRecord


class PromotionEngine:
    """Deterministic promotion decision engine.

    Evaluates model candidates and produces immutable promotion proposals.
    Never mutates input objects.
    """

    def __init__(
        self,
        scorer: PromotionScorer | None = None,
        policy: PromotionPolicy | None = None,
    ):
        self.scorer = scorer or PromotionScorer()
        self.policy = policy or PromotionPolicy()

    def evaluate(
        self,
        model_identity: ModelIdentity,
        lifecycle_record: ModelLifecycleRecord,
        audit_report: dict,
    ) -> RegistryProposal:
        """Evaluate model candidate and produce promotion proposal.

        Args:
            model_identity: Immutable model identity from scanner
            lifecycle_record: Current lifecycle state record
            audit_report: Governance audit results

        Returns:
            Immutable RegistryProposal with decision and rationale
        """
        score = self.scorer.calculate_score(
            model_identity,
            lifecycle_record,
            audit_report,
        )

        proposed_state, status, reason_codes = self.policy.evaluate(
            model_identity,
            lifecycle_record,
            score,
        )

        return RegistryProposal(
            model_id=model_identity.artifact_path,
            symbol=model_identity.symbol,
            asset_class=model_identity.asset_class,
            current_state=lifecycle_record.current_state.value,
            proposed_state=proposed_state,
            status=status,
            score=score,
            reason_codes=reason_codes,
        )
