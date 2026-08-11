"""Registry Query Engine - Sprint 3.9D-11

Read-only query layer for model governance data.
ADR-024 compliant: research layer only, no database, immutable outputs.

Exports:
    - RegistryQueryResult: Immutable query result container
    - RegistryQueryEngine: Read-only query interface for registry data
"""

from ml_service.research.registry_query.models import RegistryQueryResult
from ml_service.research.registry_query.query import RegistryQueryEngine

__all__ = [
    "RegistryQueryResult",
    "RegistryQueryEngine",
]
