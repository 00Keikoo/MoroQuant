"""Promotion Manager layer governing lifecycle transitions and quality gate checks."""

import uuid
from datetime import datetime
from typing import Optional
from ml_service.research.model_registry.model_types import (
    ModelLifecycleState,
    PromotionRecord,
    EvaluationResult
)
from ml_service.research.model_registry.service import ModelRegistryService
from ml_service.research.model_registry.registry_manager import RegistryManager


class PromotionManager:
    """PromotionManager enforcing quality gates, state transitions, and automated demotions."""

    def __init__(self, service: ModelRegistryService, manager: RegistryManager):
        if not isinstance(service, ModelRegistryService):
            raise TypeError("Expected ModelRegistryService instance")
        if not isinstance(manager, RegistryManager):
            raise TypeError("Expected RegistryManager instance")
        self.service = service
        self.manager = manager

    def validate_transition(
        self,
        previous_state: ModelLifecycleState,
        new_state: ModelLifecycleState
    ) -> bool:
        """Validate logical lifecycle state transition."""
        valid_transitions = {
            ModelLifecycleState.DRAFT: [ModelLifecycleState.CANDIDATE, ModelLifecycleState.ARCHIVED],
            ModelLifecycleState.CANDIDATE: [ModelLifecycleState.VALIDATED, ModelLifecycleState.ARCHIVED],
            ModelLifecycleState.VALIDATED: [ModelLifecycleState.PRODUCTION, ModelLifecycleState.ARCHIVED],
            ModelLifecycleState.PRODUCTION: [ModelLifecycleState.ARCHIVED],
            ModelLifecycleState.ARCHIVED: []
        }
        return new_state in valid_transitions.get(previous_state, [])

    def _create_record(
        self,
        model_version_id: str,
        previous: ModelLifecycleState,
        new: ModelLifecycleState,
        promoter: str,
        reason: Optional[str] = None,
        reference: Optional[str] = None
    ) -> PromotionRecord:
        """Helper to create and register promotion events."""
        promo_id = f"promo-{uuid.uuid4()}"
        record = PromotionRecord(
            promotion_id=promo_id,
            model_version_id=model_version_id,
            previous_state=previous,
            new_state=new,
            promoted_by=promoter,
            promoted_at=datetime.utcnow(),
            promotion_reason=reason,
            approval_reference=reference
        )
        self.service.record_promotion(record)
        return record

    def promote_candidate(
        self,
        model_version_id: str,
        promoter: str,
        reason: Optional[str] = None
    ) -> PromotionRecord:
        """Transition DRAFT -> CANDIDATE."""
        version = self.service.get_version(model_version_id)
        if not version:
            raise ValueError(f"ModelVersion '{model_version_id}' not found")
        if not self.validate_transition(version.lifecycle_state, ModelLifecycleState.CANDIDATE):
            raise ValueError(f"Cannot transition {version.lifecycle_state.value} -> CANDIDATE")
        return self._create_record(
            model_version_id,
            version.lifecycle_state,
            ModelLifecycleState.CANDIDATE,
            promoter,
            reason
        )

    def validate_model(
        self,
        model_version_id: str,
        evaluation: EvaluationResult,
        reviewer: str
    ) -> EvaluationResult:
        """Validate quality gates and transition CANDIDATE -> VALIDATED."""
        version = self.service.get_version(model_version_id)
        if not version:
            raise ValueError(f"ModelVersion '{model_version_id}' not found")
        if not self.validate_transition(version.lifecycle_state, ModelLifecycleState.VALIDATED):
            raise ValueError(f"Cannot transition {version.lifecycle_state.value} -> VALIDATED")

        # Invariant quality gate checks
        errors = []
        if evaluation.sharpe_ratio < 1.5:
            errors.append(f"Sharpe ratio {evaluation.sharpe_ratio:.2f} < 1.5")
        if evaluation.max_drawdown < -0.15:
            errors.append(f"Max drawdown {evaluation.max_drawdown:.2f} worse than -0.15")
        if evaluation.ece >= 0.05:
            errors.append(f"ECE {evaluation.ece:.4f} >= 0.05")
        if evaluation.brier_score >= 0.22:
            errors.append(f"Brier score {evaluation.brier_score:.4f} >= 0.22")
        if evaluation.trade_count < 100:
            errors.append(f"Trade count {evaluation.trade_count} < 100")

        if errors:
            raise ValueError(f"Quality gate checks failed: {', '.join(errors)}")

        # Create approved evaluation record
        approved_eval = EvaluationResult(
            model_version_id=model_version_id,
            sharpe_ratio=evaluation.sharpe_ratio,
            max_drawdown=evaluation.max_drawdown,
            ece=evaluation.ece,
            brier_score=evaluation.brier_score,
            win_rate=evaluation.win_rate,
            profit_factor=evaluation.profit_factor,
            sortino_ratio=evaluation.sortino_ratio,
            trade_count=evaluation.trade_count,
            is_approved=True,
            approved_by=reviewer,
            approved_at=datetime.utcnow()
        )
        self.service.register_evaluation(approved_eval)

        # Transition model state to VALIDATED
        self._create_record(
            model_version_id,
            version.lifecycle_state,
            ModelLifecycleState.VALIDATED,
            reviewer,
            "Quality gate criteria satisfied",
            f"review-{uuid.uuid4()}"
        )
        return approved_eval

    def approve(
        self,
        model_version_id: str,
        evaluation: EvaluationResult,
        reviewer: str
    ) -> EvaluationResult:
        """Audit approval alias wrapper."""
        return self.validate_model(model_version_id, evaluation, reviewer)

    def promote_to_production(
        self,
        model_version_id: str,
        promoter: str,
        reason: Optional[str] = None
    ) -> PromotionRecord:
        """Promote a VALIDATED model to PRODUCTION, automatically archiving the old production model."""
        version = self.service.get_version(model_version_id)
        if not version:
            raise ValueError(f"ModelVersion '{model_version_id}' not found")
        if not self.validate_transition(version.lifecycle_state, ModelLifecycleState.PRODUCTION):
            raise ValueError(f"Cannot transition {version.lifecycle_state.value} -> PRODUCTION")

        # Quality check: must have approved evaluations to go production
        eval_res = self.service.get_evaluation(model_version_id)
        if not eval_res or not eval_res.is_approved:
            raise ValueError(f"ModelVersion '{model_version_id}' has not been approved and validated")

        # Auto-demote current production model family
        current_prod = self.manager.resolve_production_version(version.model_id)
        if current_prod and current_prod.model_version_id != model_version_id:
            self._create_record(
                current_prod.model_version_id,
                ModelLifecycleState.PRODUCTION,
                ModelLifecycleState.ARCHIVED,
                promoter,
                f"Automated demotion on promotion of champion '{model_version_id}'"
            )

        return self._create_record(
            model_version_id,
            version.lifecycle_state,
            ModelLifecycleState.PRODUCTION,
            promoter,
            reason
        )

    def archive_model(
        self,
        model_version_id: str,
        archiver: str,
        reason: Optional[str] = None
    ) -> PromotionRecord:
        """Transition model from current state to ARCHIVED."""
        version = self.service.get_version(model_version_id)
        if not version:
            raise ValueError(f"ModelVersion '{model_version_id}' not found")
        if not self.validate_transition(version.lifecycle_state, ModelLifecycleState.ARCHIVED):
            raise ValueError(f"Cannot transition {version.lifecycle_state.value} -> ARCHIVED")
        return self._create_record(
            model_version_id,
            version.lifecycle_state,
            ModelLifecycleState.ARCHIVED,
            archiver,
            reason
        )

    def reject(
        self,
        model_version_id: str,
        reviewer: str,
        reason: Optional[str] = None
    ) -> PromotionRecord:
        """Reject and archive model candidate."""
        return self.archive_model(model_version_id, reviewer, reason or "Rejected during validation")

    def rollback(
        self,
        model_version_id: str,
        operator: str,
        reason: Optional[str] = None
    ) -> PromotionRecord:
        """Rollback: archive the current production model, and promote the selected version to production."""
        version = self.service.get_version(model_version_id)
        if not version:
            raise ValueError(f"ModelVersion '{model_version_id}' not found")
            
        # Verify rollback target has passed quality checks previously
        eval_res = self.service.get_evaluation(model_version_id)
        if not eval_res or not eval_res.is_approved:
            raise ValueError(f"Rollback target version '{model_version_id}' has not been approved and validated")

        current_prod = self.manager.resolve_production_version(version.model_id)
        if current_prod:
            if current_prod.model_version_id == model_version_id:
                raise ValueError("Model version is already in production")
            # Archive current production model
            self._create_record(
                current_prod.model_version_id,
                ModelLifecycleState.PRODUCTION,
                ModelLifecycleState.ARCHIVED,
                operator,
                f"Demoted due to rollback to version '{model_version_id}'"
            )

        # Reconstruct promotion record directly to production (bypassing state constraint if valid)
        prev_state = version.lifecycle_state
        return self._create_record(
            model_version_id,
            prev_state,
            ModelLifecycleState.PRODUCTION,
            operator,
            reason or "Rollback execution"
        )
