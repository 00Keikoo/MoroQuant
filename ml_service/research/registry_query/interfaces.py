"""Registry Query Interfaces - Sprint 3.9D-11

Protocol definitions for registry query components.
ADR-024 compliant: research layer only, no database dependencies.
"""

from typing import Protocol, Optional
from ml_service.research.registry_query.models import (
    RegistryQueryResult,
    ModelSummary,
    RegistrySummary,
)


class IRegistryQueryEngine(Protocol):
    """Protocol for registry query engine."""

    def list_models(self) -> RegistryQueryResult:
        """List all models in registry."""
        ...

    def find_model(self, symbol: str, timeframe: str) -> Optional[ModelSummary]:
        """Find model by symbol and timeframe."""
        ...

    def get_lifecycle_history(self, model_id: str) -> RegistryQueryResult:
        """Get lifecycle transition history for model."""
        ...

    def get_promotion_history(self, model_id: str) -> RegistryQueryResult:
        """Get promotion event history for model."""
        ...

    def get_production_candidates(self) -> RegistryQueryResult:
        """Get models ready for production promotion."""
        ...

    def get_registry_summary(self) -> RegistrySummary:
        """Get summary statistics for entire registry."""
        ...
