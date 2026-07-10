"""Model Registry module for Sprint 4.4.

Manages model metadata, versioning, lifecycle, lineage tracking, and artifact registration
per ADR-013 Model Registry Lifecycle and Lineage Policy.

Architecture:
    Repository -> Service -> Analytics -> API

Lifecycle States:
    CANDIDATE -> VALIDATED -> PRODUCTION -> ARCHIVED

One Production Model Rule:
    Only ONE model may have status=PRODUCTION for a given symbol/timeframe/algorithm.
    Promoting a new production model automatically demotes the previous one.
"""

from ml_service.research.model_registry.model_types import (
    ModelLifecycleState,
    ModelLineage,
    ModelEvaluation,
    ModelVersionMetadata,
    PromotionRequest,
    RegistrationRequest,
    ValidationResult
)

from ml_service.research.model_registry.repository import ModelRegistryRepository
from ml_service.research.model_registry.service import ModelRegistryService

__all__ = [
    'ModelLifecycleState',
    'ModelLineage',
    'ModelEvaluation',
    'ModelVersionMetadata',
    'PromotionRequest',
    'RegistrationRequest',
    'ValidationResult',
    'ModelRegistryRepository',
    'ModelRegistryService'
]
