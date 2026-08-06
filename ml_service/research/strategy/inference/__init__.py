"""ML Inference Adapter Layer - Sprint 3.9B-4A

Decouples strategy execution from ML backend frameworks.
Maps FeatureSnapshot to Prediction via ModelRegistryService.

This layer DOES NOT:
- Access PortfolioService or ExecutionSimulator
- Create orders or execute trades
- Write to database
- Load models directly from filesystem
"""

from ml_service.research.strategy.inference.models import (
    Prediction,
    ModelMetadata,
    InferenceResult,
)
from ml_service.research.strategy.inference.interfaces import ModelInferenceBackend
from ml_service.research.strategy.inference.validator import (
    FeatureSchemaValidator,
    FeatureSchemaMismatchError,
)
from ml_service.research.strategy.inference.adapter import MLInferenceAdapter

__all__ = [
    "Prediction",
    "ModelMetadata",
    "InferenceResult",
    "ModelInferenceBackend",
    "FeatureSchemaValidator",
    "FeatureSchemaMismatchError",
    "MLInferenceAdapter",
]
