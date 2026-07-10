"""API layer for model registry."""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ml_service.research.model_registry.service import ModelRegistryService
from ml_service.research.model_registry.model_types import (
    RegistrationRequest,
    ModelEvaluation,
    ModelLifecycleState
)
from ml_service.research.model_registry import analytics


router = APIRouter(prefix="/models", tags=["model_registry"])

_service: Optional[ModelRegistryService] = None


def get_service() -> ModelRegistryService:
    """Get or create model registry service instance."""
    global _service
    if _service is None:
        _service = ModelRegistryService()
    return _service


class RegisterRequest(BaseModel):
    model_id: str
    version_bump: str
    storage_path: str
    hyperparameters: Dict[str, Any]
    lineage: Dict[str, str]
    symbol: str
    timeframe: str
    algorithm: str
    git_commit: Optional[str] = None
    git_tag: Optional[str] = None


class ValidateRequest(BaseModel):
    sharpe_ratio: float
    max_drawdown: float
    ece: float
    brier_score: float
    win_rate: float
    profit_factor: float
    sortino_ratio: float
    trade_count: int
    reviewer: Optional[str] = "system"


class PromoteRequest(BaseModel):
    promoter: Optional[str] = "system"


class ArchiveRequest(BaseModel):
    archiver: Optional[str] = "system"


class CompareRequest(BaseModel):
    model_version_ids: List[str]


class RankRequest(BaseModel):
    model_version_ids: List[str]
    weights: Optional[Dict[str, float]] = None


@router.post("/register")
def register_model(request: RegisterRequest):
    """Register new model candidate."""
    try:
        req = RegistrationRequest(
            model_id=request.model_id,
            version_bump=request.version_bump,
            storage_path=request.storage_path,
            hyperparameters=request.hyperparameters,
            lineage=request.lineage,
            symbol=request.symbol,
            timeframe=request.timeframe,
            algorithm=request.algorithm,
            git_commit=request.git_commit,
            git_tag=request.git_tag
        )

        service = get_service()
        metadata = service.register_candidate(req)

        return {
            'status': 'success',
            'model_version_id': metadata.model_version_id,
            'lifecycle_state': metadata.lifecycle_state.value,
            'fingerprint': metadata.fingerprint
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{model_version_id}/validate")
def validate_model(model_version_id: str, request: ValidateRequest):
    """Validate model and promote to VALIDATED state."""
    try:
        evaluation = ModelEvaluation(
            sharpe_ratio=request.sharpe_ratio,
            max_drawdown=request.max_drawdown,
            ece=request.ece,
            brier_score=request.brier_score,
            win_rate=request.win_rate,
            profit_factor=request.profit_factor,
            sortino_ratio=request.sortino_ratio,
            trade_count=request.trade_count
        )

        service = get_service()
        success = service.evaluate_and_validate(model_version_id, evaluation, request.reviewer)

        return {
            'status': 'success',
            'model_version_id': model_version_id,
            'lifecycle_state': 'VALIDATED',
            'validated': success
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{model_version_id}/promote")
def promote_model(model_version_id: str, request: PromoteRequest):
    """Promote model to PRODUCTION state."""
    try:
        service = get_service()
        service.promote_to_production(model_version_id, request.promoter)

        return {
            'status': 'success',
            'model_version_id': model_version_id,
            'lifecycle_state': 'PRODUCTION'
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{model_version_id}/archive")
def archive_model(model_version_id: str, request: ArchiveRequest):
    """Archive model version."""
    try:
        service = get_service()
        service.archive_model(model_version_id, request.archiver)

        return {
            'status': 'success',
            'model_version_id': model_version_id,
            'lifecycle_state': 'ARCHIVED'
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{model_version_id}")
def get_model(model_version_id: str):
    """Get model version metadata."""
    try:
        service = get_service()
        metadata = service.get_model(model_version_id)

        if not metadata:
            raise HTTPException(status_code=404, detail='Model not found')

        return {
            'status': 'success',
            'model': metadata.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{model_version_id}/lineage")
def get_lineage(model_version_id: str):
    """Get complete lineage chain."""
    try:
        service = get_service()
        lineage = service.get_lineage_chain(model_version_id)

        if not lineage:
            raise HTTPException(status_code=404, detail='Lineage not found')

        return {
            'status': 'success',
            'lineage': lineage
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{model_version_id}/analytics")
def get_analytics(model_version_id: str):
    """Get model analytics."""
    try:
        service = get_service()
        metadata = service.get_model(model_version_id)

        if not metadata:
            raise HTTPException(status_code=404, detail='Model not found')

        if not metadata.evaluation:
            raise HTTPException(status_code=404, detail='No evaluation data')

        readiness = analytics.production_readiness(metadata)
        calibration = analytics.calibration_score(metadata.evaluation)
        risk = analytics.risk_metrics(metadata.evaluation)
        lineage = service.get_lineage_chain(model_version_id)
        lineage_summary = analytics.lineage_summary(lineage)

        return {
            'status': 'success',
            'model_version_id': model_version_id,
            'production_readiness': readiness,
            'calibration': calibration,
            'risk_metrics': risk,
            'lineage_summary': lineage_summary
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/production/{symbol}/{timeframe}/{algorithm}")
def get_production_model(symbol: str, timeframe: str, algorithm: str):
    """Get current production model for symbol/timeframe/algorithm."""
    try:
        service = get_service()
        metadata = service.get_production_model(symbol, timeframe, algorithm)

        if not metadata:
            return {
                'status': 'success',
                'message': 'No production model found',
                'model': None
            }

        return {
            'status': 'success',
            'model': metadata.to_dict()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/state/{state}")
def list_by_state(state: str):
    """List all models in a specific lifecycle state."""
    try:
        lifecycle_state = ModelLifecycleState(state.upper())

        service = get_service()
        models = service.list_models_by_state(lifecycle_state)

        return {
            'status': 'success',
            'state': lifecycle_state.value,
            'count': len(models),
            'models': [m.to_dict() for m in models]
        }

    except ValueError:
        raise HTTPException(status_code=400, detail=f'Invalid state: {state}')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare")
def compare_models(request: CompareRequest):
    """Compare multiple models."""
    try:
        service = get_service()
        models = [service.get_model(mid) for mid in request.model_version_ids]
        models = [m for m in models if m is not None]

        comparison = analytics.compare_models(models)

        return {
            'status': 'success',
            'comparison': comparison
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rank")
def rank_models(request: RankRequest):
    """Rank models by composite score."""
    try:
        service = get_service()
        models = [service.get_model(mid) for mid in request.model_version_ids]
        models = [m for m in models if m is not None]

        ranking = analytics.ranking(models, request.weights)

        return {
            'status': 'success',
            'ranking': ranking
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
