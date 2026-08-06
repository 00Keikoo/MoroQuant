"""Feature Context Layer - Sprint 3.9B-2A / 3.9B-3A

Immutable feature context and builder interfaces following ADR-024.
Maintains point-in-time market state for feature calculation.

This layer DOES NOT:
- Access PortfolioService or ExecutionSimulator
- Create orders or execute trades
- Load ML models or perform inference
- Write to database
"""

from ml_service.research.strategy.features.context import FeatureContext
from ml_service.research.strategy.features.interfaces import FeatureBuilder
from ml_service.research.strategy.features.builder import DefaultFeatureBuilder
from ml_service.research.strategy.features.feature_context_service import FeatureContextService
from ml_service.research.strategy.features.calculator import FeatureCalculator, NoOpFeatureCalculator

__all__ = [
    "FeatureContext",
    "FeatureBuilder",
    "DefaultFeatureBuilder",
    "FeatureContextService",
    "FeatureCalculator",
    "NoOpFeatureCalculator",
]
