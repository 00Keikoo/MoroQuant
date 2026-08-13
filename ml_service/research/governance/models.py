"""Research Governance Models - Sprint 3.9D-3

DEPRECATED: This module is part of the legacy promotion system.
The active research governance path uses:
- promotion_engine.models.RegistryProposal (canonical)
- promotion_engine.engine.PromotionEngine
- promotion_workflow.workflow.PromotionWorkflow

For backward compatibility, RegistryProposal is re-exported from the canonical location.
"""

from enum import Enum

# Import canonical RegistryProposal from promotion_engine
from ml_service.research.promotion_engine.models import RegistryProposal


class GovernanceAction(Enum):
    """Action to be taken on a model promotion."""
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REVIEW = "REVIEW"


__all__ = ["GovernanceAction", "RegistryProposal"]
