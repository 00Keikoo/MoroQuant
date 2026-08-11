"""Promotion Scorer - Sprint 3.9D-8

Deterministic weighted scoring for model promotion candidates.
ADR-024 compliant: research layer only, immutable outputs.
"""

from ml_service.research.promotion_engine.models import PromotionScore
from ml_service.research.model_identity.models import ModelIdentity
from ml_service.research.model_lifecycle.models import ModelLifecycleRecord, LifecycleState


class PromotionScorer:
    """Deterministic promotion score calculator.

    Weights:
    - validation: 30%
    - calibration: 20%
    - lifecycle: 30%
    - governance: 20%
    """

    VALIDATION_WEIGHT = 0.30
    CALIBRATION_WEIGHT = 0.20
    LIFECYCLE_WEIGHT = 0.30
    GOVERNANCE_WEIGHT = 0.20

    def calculate_score(
        self,
        model_identity: ModelIdentity,
        lifecycle_record: ModelLifecycleRecord,
        audit_report: dict,
    ) -> PromotionScore:
        """Calculate weighted promotion score."""
        validation_score = self._score_validation(model_identity)
        calibration_score = self._score_calibration(model_identity)
        lifecycle_score = self._score_lifecycle(lifecycle_record)
        governance_score = self._score_governance(audit_report)

        total_score = (
            validation_score * self.VALIDATION_WEIGHT +
            calibration_score * self.CALIBRATION_WEIGHT +
            lifecycle_score * self.LIFECYCLE_WEIGHT +
            governance_score * self.GOVERNANCE_WEIGHT
        )

        return PromotionScore(
            model_id=model_identity.artifact_path,
            validation_score=validation_score,
            calibration_score=calibration_score,
            lifecycle_score=lifecycle_score,
            governance_score=governance_score,
            total_score=total_score,
        )

    def _score_validation(self, model_identity: ModelIdentity) -> float:
        """Score validation availability (binary: 0.0 or 1.0)."""
        return 1.0 if model_identity.validation_available else 0.0

    def _score_calibration(self, model_identity: ModelIdentity) -> float:
        """Score calibration availability (binary: 0.0 or 1.0)."""
        return 1.0 if model_identity.calibration_available else 0.0

    def _score_lifecycle(self, lifecycle_record: ModelLifecycleRecord) -> float:
        """Score lifecycle state progression."""
        state_scores = {
            LifecycleState.DISCOVERED: 0.0,
            LifecycleState.VALIDATED: 0.4,
            LifecycleState.GOVERNANCE_READY: 0.7,
            LifecycleState.APPROVED: 1.0,
            LifecycleState.PRODUCTION: 1.0,
            LifecycleState.REJECTED: 0.0,
        }
        return state_scores.get(lifecycle_record.current_state, 0.0)

    def _score_governance(self, audit_report: dict) -> float:
        """Score governance readiness from audit report."""
        if not audit_report:
            return 0.0

        governance_ready = audit_report.get("governance_ready", False)
        return 1.0 if governance_ready else 0.0
