"""Promotion Workflow - Sprint 3.9D-9

Research-only workflow for consuming RegistryProposal and creating PromotionEvents.
ADR-024 compliant: research layer only, no database, immutable outputs.

Exports:
    - PromotionEvent: Immutable promotion event record
    - PromotionWorkflow: Workflow orchestration for promotion decisions
    - WorkflowPolicy: Policy enforcement for workflow transitions
"""

from ml_service.research.promotion_workflow.models import PromotionEvent
from ml_service.research.promotion_workflow.workflow import PromotionWorkflow
from ml_service.research.promotion_workflow.policy import WorkflowPolicy

__all__ = [
    "PromotionEvent",
    "PromotionWorkflow",
    "WorkflowPolicy",
]
