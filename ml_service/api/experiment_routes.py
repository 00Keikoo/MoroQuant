"""API routes for Experiment Registry."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, Field

from ml_service.lab.experiments import ExperimentService, calculate_experiment_analytics

router = APIRouter()

experiment_service = ExperimentService()


class ExperimentCreateRequest(BaseModel):
    """Request model for creating an experiment."""
    experiment_id: str = Field(..., description="Experiment identifier grouping multiple runs")
    dataset_version: Optional[str] = Field(None, description="Dataset version used")
    feature_version: Optional[str] = Field(None, description="Feature version used")
    model_version: Optional[str] = Field(None, description="Model version used")
    hyperparameters: Optional[str] = Field(None, description="JSON string of hyperparameters")


class ExperimentMetricsRequest(BaseModel):
    """Request model for updating experiment metrics."""
    train_loss: Optional[float] = None
    validation_loss: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    profit_factor: Optional[float] = None
    win_rate: Optional[float] = None
    max_drawdown: Optional[float] = None
    ece: Optional[float] = None
    brier_score: Optional[float] = None


class ExperimentResponse(BaseModel):
    """Response model for experiment."""
    id: int
    experiment_id: str
    run_id: str
    status: str
    dataset_version: Optional[str]
    feature_version: Optional[str]
    model_version: Optional[str]
    hyperparameters: Optional[str]
    train_loss: Optional[float]
    validation_loss: Optional[float]
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    calmar_ratio: Optional[float]
    profit_factor: Optional[float]
    win_rate: Optional[float]
    max_drawdown: Optional[float]
    ece: Optional[float]
    brier_score: Optional[float]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


class ExperimentListResponse(BaseModel):
    """Response model for experiment list."""
    experiments: List[ExperimentResponse]
    total: int
    limit: int
    offset: int


class ExperimentAnalyticsResponse(BaseModel):
    """Response model for experiment analytics."""
    total_experiments: int
    completed_experiments: int
    failed_experiments: int
    running_experiments: int
    completion_rate: float
    avg_sharpe_ratio: float
    avg_sortino_ratio: float
    avg_calmar_ratio: float
    avg_profit_factor: float
    avg_win_rate: float
    avg_max_drawdown: float
    avg_ece: float
    avg_brier_score: float
    best_sharpe_run_id: str
    worst_sharpe_run_id: str


@router.post("/experiments", response_model=ExperimentResponse)
async def create_experiment(request: ExperimentCreateRequest):
    """Create a new experiment run."""
    experiment = experiment_service.create_experiment(
        experiment_id=request.experiment_id,
        dataset_version=request.dataset_version,
        feature_version=request.feature_version,
        model_version=request.model_version,
        hyperparameters=request.hyperparameters
    )

    if not experiment:
        raise HTTPException(status_code=500, detail="Failed to create experiment")

    return ExperimentResponse(
        id=experiment.id,
        experiment_id=experiment.experiment_id,
        run_id=experiment.run_id,
        status=experiment.status,
        dataset_version=experiment.dataset_version,
        feature_version=experiment.feature_version,
        model_version=experiment.model_version,
        hyperparameters=experiment.hyperparameters,
        train_loss=experiment.train_loss,
        validation_loss=experiment.validation_loss,
        sharpe_ratio=experiment.sharpe_ratio,
        sortino_ratio=experiment.sortino_ratio,
        calmar_ratio=experiment.calmar_ratio,
        profit_factor=experiment.profit_factor,
        win_rate=experiment.win_rate,
        max_drawdown=experiment.max_drawdown,
        ece=experiment.ece,
        brier_score=experiment.brier_score,
        started_at=experiment.started_at,
        completed_at=experiment.completed_at,
        created_at=experiment.created_at,
        updated_at=experiment.updated_at
    )


@router.get("/experiments/{run_id}", response_model=ExperimentResponse)
async def get_experiment(run_id: str):
    """Get experiment by run_id."""
    experiment = experiment_service.get_run(run_id)

    if not experiment:
        raise HTTPException(status_code=404, detail=f"Experiment with run_id {run_id} not found")

    return ExperimentResponse(
        id=experiment.id,
        experiment_id=experiment.experiment_id,
        run_id=experiment.run_id,
        status=experiment.status,
        dataset_version=experiment.dataset_version,
        feature_version=experiment.feature_version,
        model_version=experiment.model_version,
        hyperparameters=experiment.hyperparameters,
        train_loss=experiment.train_loss,
        validation_loss=experiment.validation_loss,
        sharpe_ratio=experiment.sharpe_ratio,
        sortino_ratio=experiment.sortino_ratio,
        calmar_ratio=experiment.calmar_ratio,
        profit_factor=experiment.profit_factor,
        win_rate=experiment.win_rate,
        max_drawdown=experiment.max_drawdown,
        ece=experiment.ece,
        brier_score=experiment.brier_score,
        started_at=experiment.started_at,
        completed_at=experiment.completed_at,
        created_at=experiment.created_at,
        updated_at=experiment.updated_at
    )


@router.get("/experiments", response_model=ExperimentListResponse)
async def list_experiments(
    limit: int = Query(100, ge=1, le=1000, description="Maximum results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """List experiments with pagination and optional status filter."""
    if status:
        experiments = experiment_service.list_by_status(status)
        total = len(experiments)
        experiments = experiments[offset:offset + limit]
    else:
        experiments = experiment_service.list_all_runs(limit=limit, offset=offset)
        total = experiment_service.get_run_count()

    experiment_responses = [
        ExperimentResponse(
            id=exp.id,
            experiment_id=exp.experiment_id,
            run_id=exp.run_id,
            status=exp.status,
            dataset_version=exp.dataset_version,
            feature_version=exp.feature_version,
            model_version=exp.model_version,
            hyperparameters=exp.hyperparameters,
            train_loss=exp.train_loss,
            validation_loss=exp.validation_loss,
            sharpe_ratio=exp.sharpe_ratio,
            sortino_ratio=exp.sortino_ratio,
            calmar_ratio=exp.calmar_ratio,
            profit_factor=exp.profit_factor,
            win_rate=exp.win_rate,
            max_drawdown=exp.max_drawdown,
            ece=exp.ece,
            brier_score=exp.brier_score,
            started_at=exp.started_at,
            completed_at=exp.completed_at,
            created_at=exp.created_at,
            updated_at=exp.updated_at
        )
        for exp in experiments
    ]

    return ExperimentListResponse(
        experiments=experiment_responses,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/experiments/by-experiment-id/{experiment_id}", response_model=List[ExperimentResponse])
async def get_experiment_runs(experiment_id: str):
    """Get all runs for a given experiment_id."""
    experiments = experiment_service.get_experiment_runs(experiment_id)

    return [
        ExperimentResponse(
            id=exp.id,
            experiment_id=exp.experiment_id,
            run_id=exp.run_id,
            status=exp.status,
            dataset_version=exp.dataset_version,
            feature_version=exp.feature_version,
            model_version=exp.model_version,
            hyperparameters=exp.hyperparameters,
            train_loss=exp.train_loss,
            validation_loss=exp.validation_loss,
            sharpe_ratio=exp.sharpe_ratio,
            sortino_ratio=exp.sortino_ratio,
            calmar_ratio=exp.calmar_ratio,
            profit_factor=exp.profit_factor,
            win_rate=exp.win_rate,
            max_drawdown=exp.max_drawdown,
            ece=exp.ece,
            brier_score=exp.brier_score,
            started_at=exp.started_at,
            completed_at=exp.completed_at,
            created_at=exp.created_at,
            updated_at=exp.updated_at
        )
        for exp in experiments
    ]


@router.patch("/experiments/{run_id}/start")
async def start_experiment(run_id: str):
    """Mark experiment as RUNNING."""
    success = experiment_service.start_run(run_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Experiment with run_id {run_id} not found")

    return {"success": True, "run_id": run_id, "status": "RUNNING"}


@router.patch("/experiments/{run_id}/complete")
async def complete_experiment(run_id: str, metrics: ExperimentMetricsRequest):
    """Mark experiment as COMPLETED and update metrics."""
    success = experiment_service.complete_run(
        run_id=run_id,
        train_loss=metrics.train_loss,
        validation_loss=metrics.validation_loss,
        sharpe_ratio=metrics.sharpe_ratio,
        sortino_ratio=metrics.sortino_ratio,
        calmar_ratio=metrics.calmar_ratio,
        profit_factor=metrics.profit_factor,
        win_rate=metrics.win_rate,
        max_drawdown=metrics.max_drawdown,
        ece=metrics.ece,
        brier_score=metrics.brier_score
    )

    if not success:
        raise HTTPException(status_code=404, detail=f"Experiment with run_id {run_id} not found")

    return {"success": True, "run_id": run_id, "status": "COMPLETED"}


@router.patch("/experiments/{run_id}/fail")
async def fail_experiment(run_id: str):
    """Mark experiment as FAILED."""
    success = experiment_service.fail_run(run_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Experiment with run_id {run_id} not found")

    return {"success": True, "run_id": run_id, "status": "FAILED"}


@router.patch("/experiments/{run_id}/metrics")
async def update_experiment_metrics(run_id: str, metrics: ExperimentMetricsRequest):
    """Update experiment metrics."""
    success = experiment_service.update_metrics(
        run_id=run_id,
        train_loss=metrics.train_loss,
        validation_loss=metrics.validation_loss,
        sharpe_ratio=metrics.sharpe_ratio,
        sortino_ratio=metrics.sortino_ratio,
        calmar_ratio=metrics.calmar_ratio,
        profit_factor=metrics.profit_factor,
        win_rate=metrics.win_rate,
        max_drawdown=metrics.max_drawdown,
        ece=metrics.ece,
        brier_score=metrics.brier_score
    )

    if not success:
        raise HTTPException(status_code=404, detail=f"Experiment with run_id {run_id} not found")

    return {"success": True, "run_id": run_id}


@router.delete("/experiments/{run_id}")
async def delete_experiment(run_id: str):
    """Delete experiment by run_id."""
    success = experiment_service.delete_run(run_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Experiment with run_id {run_id} not found")

    return {"success": True, "run_id": run_id, "deleted": True}


@router.get("/experiments/analytics/summary", response_model=ExperimentAnalyticsResponse)
async def get_experiment_analytics():
    """Get aggregate analytics for all experiments."""
    experiments = experiment_service.list_all_runs(limit=10000, offset=0)
    analytics = calculate_experiment_analytics(experiments)

    return ExperimentAnalyticsResponse(
        total_experiments=analytics.total_experiments,
        completed_experiments=analytics.completed_experiments,
        failed_experiments=analytics.failed_experiments,
        running_experiments=analytics.running_experiments,
        completion_rate=analytics.completion_rate,
        avg_sharpe_ratio=analytics.avg_sharpe_ratio,
        avg_sortino_ratio=analytics.avg_sortino_ratio,
        avg_calmar_ratio=analytics.avg_calmar_ratio,
        avg_profit_factor=analytics.avg_profit_factor,
        avg_win_rate=analytics.avg_win_rate,
        avg_max_drawdown=analytics.avg_max_drawdown,
        avg_ece=analytics.avg_ece,
        avg_brier_score=analytics.avg_brier_score,
        best_sharpe_run_id=analytics.best_sharpe_run_id,
        worst_sharpe_run_id=analytics.worst_sharpe_run_id
    )
