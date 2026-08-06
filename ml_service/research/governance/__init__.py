"""Research Governance Engine - Sprint 3.9D-3

Pure functional governance layer that transforms PromotionDecision outputs
into immutable registry proposals.

ADR-024 Compliant:
- Research layer only
- No database dependency
- No PortfolioService
- No ExecutionSimulator
- No model deployment
- No ModelRegistry mutation
- Pure functional and deterministic
"""

from ml_service.research.governance.models import GovernanceAction, RegistryProposal
from ml_service.research.governance.interfaces import GovernanceEngine
from ml_service.research.governance.policy import GovernancePolicy
from ml_service.research.governance.governance import DefaultGovernanceEngine

__all__ = [
    "GovernanceAction",
    "RegistryProposal",
    "GovernanceEngine",
    "GovernancePolicy",
    "DefaultGovernanceEngine",
]
