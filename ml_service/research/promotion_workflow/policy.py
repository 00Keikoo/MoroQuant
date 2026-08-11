"""Workflow Policy - Sprint 3.9D-9

Policy enforcement for promotion workflow transitions.
ADR-024 compliant: research layer only, deterministic decisions.
"""

from ml_service.research.promotion_engine.models import RegistryProposal, PromotionStatus
from ml_service.research.model_lifecycle.models import LifecycleState


class WorkflowPolicy:
    """Workflow policy for promotion transitions.

    Rules:
    - APPROVED proposals can create promotion events
    - REJECTED proposals cannot promote
    - Proxy models cannot transition to PRODUCTION
    """

    def can_promote(self, proposal: RegistryProposal) -> tuple[bool, tuple[str, ...]]:
        """Check if proposal can be promoted.

        Returns:
            (allowed, reason_codes)
        """
        reason_codes = []

        if proposal.status == PromotionStatus.REJECTED:
            reason_codes.append("PROPOSAL_REJECTED")
            return (False, tuple(reason_codes))

        if proposal.status == PromotionStatus.BLOCKED:
            reason_codes.append("PROPOSAL_BLOCKED")
            return (False, tuple(reason_codes))

        if proposal.asset_class == "PROXY" and proposal.proposed_state == LifecycleState.PRODUCTION.value:
            reason_codes.append("PROXY_CANNOT_BE_PRODUCTION")
            return (False, tuple(reason_codes))

        if proposal.status == PromotionStatus.APPROVED:
            reason_codes.append("PROMOTION_APPROVED")
            return (True, tuple(reason_codes))

        reason_codes.append("PROPOSAL_NOT_APPROVED")
        return (False, tuple(reason_codes))
