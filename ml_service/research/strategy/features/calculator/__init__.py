"""Feature Calculator Layer - Sprint 3.9B-3A

Abstraction for feature calculation logic following ADR-024.
Separates calculation from builder orchestration.

This layer contains pure feature calculation contracts.
- Define feature calculation interfaces
- Provide deterministic feature calculation implementations
- Maintain immutable feature outputs
"""

from ml_service.research.strategy.features.calculator.interfaces import FeatureCalculator
from ml_service.research.strategy.features.calculator.noop import NoOpFeatureCalculator

__all__ = [
    "FeatureCalculator",
    "NoOpFeatureCalculator",
]
