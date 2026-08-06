"""Research Governance Interfaces - Sprint 3.9D-3

Abstract interfaces for governance engine implementations.
"""

from abc import ABC, abstractmethod
from ml_service.research.promotion.models import PromotionDecision
from ml_service.research.governance.models import RegistryProposal


class GovernanceEngine(ABC):
    """Abstract governance engine for evaluating promotion decisions."""

    @abstractmethod
    def evaluate(self, promotion_decision: PromotionDecision) -> RegistryProposal:
        """Evaluate a promotion decision and produce a registry proposal.

        Args:
            promotion_decision: Immutable promotion decision from the promotion engine

        Returns:
            RegistryProposal: Immutable proposal for registry action

        Note:
            This method must be pure functional and deterministic.
            Must not perform any database access, registry mutation, or deployment.
        """
        pass
