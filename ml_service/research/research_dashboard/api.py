"""FastAPI endpoints for Research Dashboard."""

from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ml_service.research.research_dashboard.service import ResearchDashboardService
from ml_service.research.research_dashboard.analytics import ResearchAnalytics
from ml_service.research.research_dashboard.repository import ResearchDashboardRepository


router = APIRouter(prefix="/research", tags=["research"])

_service: Optional[ResearchDashboardService] = None
_analytics: Optional[ResearchAnalytics] = None


def get_service() -> ResearchDashboardService:
    """Get or create service instance."""
    global _service
    if _service is None:
        _service = ResearchDashboardService()
    return _service


def get_analytics() -> ResearchAnalytics:
    """Get or create analytics instance."""
    global _analytics
    if _analytics is None:
        repository = ResearchDashboardRepository()
        _analytics = ResearchAnalytics(repository)
    return _analytics


class ComparisonRequest(BaseModel):
    """Request body for experiment comparison."""
    experiment_ids: List[str]


@router.get("/experiments")
def list_experiments(
    strategy: Optional[str] = None,
    status: Optional[str] = None
):
    """List all experiments with optional filters."""
    service = get_service()
    summaries = service.list_experiments(strategy, status)
    return [
        {
            "experiment_id": s.experiment_id,
            "name": s.name,
            "strategy_name": s.strategy_name,
            "created_at": s.created_at,
            "status": s.status,
            "metrics": s.metrics
        }
        for s in summaries
    ]


@router.get("/experiments/{experiment_id}")
def get_experiment(experiment_id: str):
    """Get detailed experiment configuration."""
    service = get_service()
    detail = service.get_experiment(experiment_id)

    if not detail:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return {
        "experiment_id": detail.experiment_id,
        "name": detail.name,
        "description": detail.description,
        "strategy_name": detail.strategy_name,
        "parameters": detail.parameters,
        "created_at": detail.created_at,
        "status": detail.status,
        "duration_seconds": detail.duration_seconds,
        "git_commit": detail.git_commit
    }


@router.get("/experiments/{experiment_id}/lineage")
def get_experiment_lineage(experiment_id: str):
    """Get experiment lineage trace to source datasets and features."""
    service = get_service()
    lineage = service.get_lineage(experiment_id)

    if not lineage:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return {
        "experiment_id": lineage.experiment_id,
        "source_dataset_id": lineage.source_dataset_id,
        "source_dataset_fingerprint": lineage.source_dataset_fingerprint,
        "feature_datasets": [
            {
                "feature_dataset_id": fd.feature_dataset_id,
                "feature_version_id": fd.feature_version_id,
                "fingerprint": fd.fingerprint
            }
            for fd in lineage.feature_datasets
        ]
    }


@router.get("/experiments/{experiment_id}/evaluation")
def get_experiment_evaluation(experiment_id: str):
    """Get experiment evaluation summary."""
    service = get_service()
    evaluation = service.get_evaluation(experiment_id)

    if not evaluation:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return {
        "experiment_id": evaluation.experiment_id,
        "total_trades": evaluation.total_trades,
        "win_rate": evaluation.win_rate,
        "profit_factor": evaluation.profit_factor,
        "average_trade_return": evaluation.average_trade_return,
        "daily_return_volatility": evaluation.daily_return_volatility,
        "information_coefficient": evaluation.information_coefficient
    }


@router.post("/experiments/compare")
def compare_experiments(request: ComparisonRequest):
    """Compare multiple experiments side-by-side."""
    if len(request.experiment_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 experiments required")

    analytics = get_analytics()
    comparison = analytics.compare_experiments(request.experiment_ids)

    return {
        "compared_ids": comparison.compared_ids,
        "metrics_comparison": comparison.metrics_comparison,
        "parameter_differentials": comparison.parameter_differentials
    }
