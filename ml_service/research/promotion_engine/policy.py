"""Promotion Policy - Sprint 3.9D-8

Asset-specific promotion rules and eligibility constraints.
ADR-024 compliant: research layer only, deterministic decisions.
"""

from ml_service.research.promotion_engine.models import PromotionStatus, PromotionScore
from ml_service.research.model_identity.models import ModelIdentity
from ml_service.research.model_lifecycle.models import ModelLifecycleRecord, LifecycleState


class PromotionPolicy:
    """Deterministic promotion policy engine.

    Rules:
    - Crypto models:
      - VALIDATED + calibration + governance → APPROVED
      - APPROVED lifecycle → PRODUCTION
    - Proxy models:
      - Never PRODUCTION
      - Only APPROVED_RESEARCH
    - Reject if missing validation, calibration, or invalid lifecycle
    """

    MINIMUM_SCORE_THRESHOLD = 0.7

    def evaluate(
        self,
        model_identity: ModelIdentity,
        lifecycle_record: ModelLifecycleRecord,
        score: PromotionScore,
    ) -> tuple[str, PromotionStatus, tuple[str, ...]]:
        """Evaluate promotion eligibility.

        Returns:
            (proposed_state, status, reason_codes)
        """
        reason_codes = []

        if not model_identity.validation_available:
            reason_codes.append("MISSING_VALIDATION")

        if not model_identity.calibration_available:
            reason_codes.append("MISSING_CALIBRATION")

        if lifecycle_record.current_state == LifecycleState.REJECTED:
            reason_codes.append("LIFECYCLE_REJECTED")

        if lifecycle_record.current_state == LifecycleState.DISCOVERED:
            reason_codes.append("LIFECYCLE_NOT_VALIDATED")

        if model_identity.asset_class not in ["CRYPTO", "PROXY"]:
            reason_codes.append("UNKNOWN_ASSET_CLASS")

        if reason_codes:
            return (
                lifecycle_record.current_state.value,
                PromotionStatus.REJECTED,
                tuple(reason_codes),
            )

        if model_identity.asset_class == "PROXY":
            return self._evaluate_proxy(lifecycle_record, score)

        if model_identity.asset_class == "CRYPTO":
            return self._evaluate_crypto(lifecycle_record, score)

        reason_codes.append("INVALID_ASSET_CLASS")
        return (
            lifecycle_record.current_state.value,
            PromotionStatus.REJECTED,
            tuple(reason_codes),
        )

    def _evaluate_crypto(
        self,
        lifecycle_record: ModelLifecycleRecord,
        score: PromotionScore,
    ) -> tuple[str, PromotionStatus, tuple[str, ...]]:
        """Evaluate crypto model promotion."""
        reason_codes = []

        if score.total_score < self.MINIMUM_SCORE_THRESHOLD:
            reason_codes.append("SCORE_BELOW_THRESHOLD")
            return (
                lifecycle_record.current_state.value,
                PromotionStatus.REJECTED,
                tuple(reason_codes),
            )

        if lifecycle_record.current_state == LifecycleState.VALIDATED:
            reason_codes.append("CRYPTO_VALIDATED_TO_APPROVED")
            return (
                LifecycleState.APPROVED.value,
                PromotionStatus.APPROVED,
                tuple(reason_codes),
            )

        if lifecycle_record.current_state == LifecycleState.GOVERNANCE_READY:
            reason_codes.append("CRYPTO_GOVERNANCE_READY_TO_APPROVED")
            return (
                LifecycleState.APPROVED.value,
                PromotionStatus.APPROVED,
                tuple(reason_codes),
            )

        if lifecycle_record.current_state == LifecycleState.APPROVED:
            reason_codes.append("CRYPTO_APPROVED_TO_PRODUCTION")
            return (
                LifecycleState.PRODUCTION.value,
                PromotionStatus.APPROVED,
                tuple(reason_codes),
            )

        if lifecycle_record.current_state == LifecycleState.PRODUCTION:
            reason_codes.append("ALREADY_PRODUCTION")
            return (
                LifecycleState.PRODUCTION.value,
                PromotionStatus.APPROVED,
                tuple(reason_codes),
            )

        reason_codes.append("CRYPTO_INVALID_STATE")
        return (
            lifecycle_record.current_state.value,
            PromotionStatus.BLOCKED,
            tuple(reason_codes),
        )

    def _evaluate_proxy(
        self,
        lifecycle_record: ModelLifecycleRecord,
        score: PromotionScore,
    ) -> tuple[str, PromotionStatus, tuple[str, ...]]:
        """Evaluate proxy model promotion (never PRODUCTION)."""
        reason_codes = []

        if lifecycle_record.current_state == LifecycleState.PRODUCTION:
            reason_codes.append("PROXY_CANNOT_BE_PRODUCTION")
            return (
                lifecycle_record.current_state.value,
                PromotionStatus.BLOCKED,
                tuple(reason_codes),
            )

        if score.total_score < self.MINIMUM_SCORE_THRESHOLD:
            reason_codes.append("SCORE_BELOW_THRESHOLD")
            return (
                lifecycle_record.current_state.value,
                PromotionStatus.REJECTED,
                tuple(reason_codes),
            )

        if lifecycle_record.current_state in [
            LifecycleState.VALIDATED,
            LifecycleState.GOVERNANCE_READY,
        ]:
            reason_codes.append("PROXY_APPROVED_FOR_RESEARCH")
            return (
                LifecycleState.GOVERNANCE_READY.value,
                PromotionStatus.APPROVED,
                tuple(reason_codes),
            )

        if lifecycle_record.current_state == LifecycleState.APPROVED:
            reason_codes.append("PROXY_BLOCKED_FROM_PRODUCTION")
            return (
                lifecycle_record.current_state.value,
                PromotionStatus.BLOCKED,
                tuple(reason_codes),
            )

        reason_codes.append("PROXY_INVALID_STATE")
        return (
            lifecycle_record.current_state.value,
            PromotionStatus.BLOCKED,
            tuple(reason_codes),
        )
