"""Research Promotion Engine - Sprint 3.9D-2

Pure functional promotion decision system for evaluating benchmark results.
Produces immutable promotion recommendations.

ADR-024 Compliant:
- Research layer only
- No database dependency
- No PortfolioService
- No ExecutionSimulator
- No model deployment
- No ModelRegistry mutation
- Pure functional and deterministic
"""

from ml_service.research.promotion.models import PromotionStatus, PromotionDecision
from ml_service.research.promotion.interfaces import PromotionEngine
from ml_service.research.promotion.rules import PromotionCriteria
from ml_service.research.promotion.promotion import DefaultPromotionEngine

__all__ = [
    "PromotionStatus",
    "PromotionDecision",
    "PromotionEngine",
    "PromotionCriteria",
    "DefaultPromotionEngine",
]
