"""Registry Governance API - Sprint 3.9D-12

Read-only FastAPI layer for registry governance queries.
ADR-024 compliant: API layer only, delegates to registry_query.

Exports:
    - router: FastAPI router for registry endpoints
"""

from ml_service.research.registry_api.router import router

__all__ = ["router"]
