"""Registry API Router - Sprint 3.9D-12

FastAPI endpoints for registry governance queries.
ADR-024 compliant: read-only, delegates to service layer.
"""

from fastapi import APIRouter, HTTPException, Depends

from ml_service.research.registry_api.schemas import (
    ModelListResponse,
    ModelDetailResponse,
    RegistrySummaryResponse,
    ProductionCandidatesResponse,
    ModelHistoryResponse,
)
from ml_service.research.registry_api.service import RegistryAPIService
from ml_service.research.registry_query import RegistryQueryEngine
from ml_service.research.registry_snapshot.snapshot import RegistrySnapshot
from ml_service.research.registry_event_ledger.service import RegistryEventLedger
from ml_service.research.registry_store import RegistryStoreService

router = APIRouter(prefix="/api/v1/registry", tags=["Registry Governance"])


def get_registry_service() -> RegistryAPIService:
    """Dependency injection for RegistryAPIService.

    Builds the dependency chain:
    - RegistryStoreService -> RegistrySnapshot + RegistryEventLedger
    - RegistryQueryEngine -> RegistryAPIService
    """
    store = RegistryStoreService()
    snapshot = RegistrySnapshot(store)
    ledger = RegistryEventLedger(store)
    query_engine = RegistryQueryEngine(snapshot, ledger)

    return RegistryAPIService(query_engine)


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    service: RegistryAPIService = Depends(get_registry_service)
) -> ModelListResponse:
    """List all models in registry with current state.

    Returns models sorted by (symbol, timeframe) for deterministic ordering.
    """
    return service.list_models()


@router.get("/models/{artifact_id:path}", response_model=ModelDetailResponse)
async def get_model_detail(
    artifact_id: str,
    service: RegistryAPIService = Depends(get_registry_service)
) -> ModelDetailResponse:
    """Get model detail by artifact ID.

    Args:
        artifact_id: Model artifact path (e.g., "models/BTCUSD_1h/...")

    Returns:
        ModelDetailResponse

    Raises:
        HTTPException: 404 if model not found
    """
    result = service.get_model_by_id(artifact_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Model not found: {artifact_id}"
        )

    return result


@router.get("/summary", response_model=RegistrySummaryResponse)
async def get_registry_summary(
    service: RegistryAPIService = Depends(get_registry_service)
) -> RegistrySummaryResponse:
    """Get registry summary statistics.

    Returns aggregated counts by asset class and lifecycle state.
    """
    return service.get_registry_summary()


@router.get("/production-candidates", response_model=ProductionCandidatesResponse)
async def get_production_candidates(
    service: RegistryAPIService = Depends(get_registry_service)
) -> ProductionCandidatesResponse:
    """Get models ready for production promotion.

    Criteria:
    - Lifecycle state = APPROVED
    - Validation available
    - Calibration available
    - Asset class = CRYPTO (proxy models excluded)

    Returns candidates sorted by (symbol, timeframe).
    """
    return service.get_production_candidates()


@router.get("/history/{artifact_id:path}", response_model=ModelHistoryResponse)
async def get_model_history(
    artifact_id: str,
    service: RegistryAPIService = Depends(get_registry_service)
) -> ModelHistoryResponse:
    """Get lifecycle transition history for model.

    Args:
        artifact_id: Model artifact path

    Returns:
        ModelHistoryResponse with lifecycle events

    Raises:
        HTTPException: 404 if model not found
    """
    result = service.get_model_history(artifact_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Model not found: {artifact_id}"
        )

    return result
