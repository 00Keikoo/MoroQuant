"""Promotion Workflow - Sprint 3.9D-9

Orchestration for consuming RegistryProposal and creating PromotionEvents.
ADR-024 compliant: research layer only, no database, immutable outputs.
"""

from datetime import datetime, UTC
from typing import Optional

from ml_service.research.promotion_workflow.models import PromotionEvent
from ml_service.research.promotion_workflow.policy import WorkflowPolicy
from ml_service.research.promotion_engine.models import RegistryProposal, PromotionStatus


class PromotionWorkflow:
    """Workflow orchestration for promotion decisions.

    Consumes RegistryProposal and creates immutable PromotionEvents.
    Never mutates input objects or model files.
    """

    def __init__(self, policy: Optional[WorkflowPolicy] = None):
        self.policy = policy or WorkflowPolicy()

    def evaluate(self, proposal: RegistryProposal) -> Optional[PromotionEvent]:
        """Evaluate proposal and create event if eligible.

        Args:
            proposal: Immutable RegistryProposal from PromotionEngine

        Returns:
            PromotionEvent if eligible, None if blocked
        """
        can_promote, reason_codes = self.policy.can_promote(proposal)

        if not can_promote:
            return None

        if proposal.status == PromotionStatus.APPROVED:
            return self.approve(proposal)

        return None

    def approve(self, proposal: RegistryProposal) -> PromotionEvent:
        """Create promotion event for approved proposal.

        Args:
            proposal: APPROVED RegistryProposal

        Returns:
            Immutable PromotionEvent for the promotion
        """
        created_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        event_id = PromotionEvent.generate_event_id(
            model_id=proposal.model_id,
            from_state=proposal.current_state,
            to_state=proposal.proposed_state,
            created_at=created_at,
        )

        all_reason_codes = list(proposal.reason_codes) + ["WORKFLOW_APPROVED"]

        return PromotionEvent(
            event_id=event_id,
            model_id=proposal.model_id,
            from_state=proposal.current_state,
            to_state=proposal.proposed_state,
            decision="APPROVED",
            reason_codes=tuple(all_reason_codes),
            created_at=created_at,
        )

    def reject(self, proposal: RegistryProposal) -> PromotionEvent:
        """Create rejection event for rejected proposal.

        Args:
            proposal: REJECTED or BLOCKED RegistryProposal

        Returns:
            Immutable PromotionEvent for the rejection
        """
        created_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        event_id = PromotionEvent.generate_event_id(
            model_id=proposal.model_id,
            from_state=proposal.current_state,
            to_state=proposal.current_state,
            created_at=created_at,
        )

        all_reason_codes = list(proposal.reason_codes) + ["WORKFLOW_REJECTED"]

        return PromotionEvent(
            event_id=event_id,
            model_id=proposal.model_id,
            from_state=proposal.current_state,
            to_state=proposal.current_state,
            decision="REJECTED",
            reason_codes=tuple(all_reason_codes),
            created_at=created_at,
        )
