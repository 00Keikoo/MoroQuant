"""Promotion Workflow Interfaces - Sprint 3.9D-9

Protocol definitions for promotion workflow components.
ADR-024 compliant: research layer only, no database dependencies.
"""

from typing import Protocol, Optional
from ml_service.research.promotion_workflow.models import PromotionEvent
from ml_service.research.promotion_engine.models import RegistryProposal


class IWorkflowPolicy(Protocol):
    """Protocol for workflow policy enforcement."""

    def can_promote(self, proposal: RegistryProposal) -> tuple[bool, tuple[str, ...]]:
        """Check if proposal can be promoted.

        Returns:
            (allowed, reason_codes)
        """
        ...


class IPromotionWorkflow(Protocol):
    """Protocol for promotion workflow orchestration."""

    def evaluate(self, proposal: RegistryProposal) -> Optional[PromotionEvent]:
        """Evaluate proposal and create event if eligible."""
        ...

    def approve(self, proposal: RegistryProposal) -> PromotionEvent:
        """Create promotion event for approved proposal."""
        ...

    def reject(self, proposal: RegistryProposal) -> PromotionEvent:
        """Create rejection event for rejected proposal."""
        ...
