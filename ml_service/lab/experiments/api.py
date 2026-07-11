"""API routes for Experiment Registry.

Clean API aligned with remediated domain model.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, Field

from ml_service.lab.experiments.service import ExperimentService
from ml_service.lab.experiments.analytics import calculate_experiment_analytics

router = APIRouter()

experiment_service = ExperimentService()


class ExperimentCreateRequest(BaseModel):
    """Request model for creating an experiment."""
    experiment_id: str = Field(..., description="Experiment identifier grouping multiple runs")
    dataset_version: Optional[str] = Field(None, description="Dataset version used")
    feature_version: Optional[str] = Field(None, description="Feature version used")
    model_version: Optional[str] = Field(None, description="Model version used")
    hyperparameters: Optional[str] = Field(None, description="JSON string of hyperparameters")
    notes: Optional[str] = Field(None, description="Optional notes")


class ExperimentMetricsRequest(BaseModel):
    """Request model for updating experiment training metrics."""
    train_loss: Optional[float] = None
    validation_loss: Optional[float] = None


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
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    notes: Optional[str]


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
    training_experiments: int
    created_experiments: int
    completion_rate: float
    failure_rate: float
    avg_train_loss: float
    avg_validation_loss: float
    best_validation_loss_run_id: str
    worst_validation_loss_run_id: str


@router.post("/experiments", response_model=ExperimentResponse)
async def create_experiment(request: ExperimentCreateRequest):
    """Create a new experiment run."""
    experiment = experiment_service.create_experiment(
        experiment_id=request.experiment_id,
        dataset_version=request.dataset_version,
        feature_version=request.feature_version,
        model_version=request.model_version,
        hyperparameters=request.hyperparameters,
        notes=request.notes
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
        started_at=experiment.started_at,
        completed_at=experiment.completed_at,
        created_at=experiment.created_at,
        updated_at=experiment.updated_at,
        notes=experiment.notes
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
        started_at=experiment.started_at,
        completed_at=experiment.completed_at,
        created_at=experiment.created_at,
        updated_at=experiment.updated_at,
        notes=experiment.notes
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
            started_at=exp.started_at,
            completed_at=exp.completed_at,
            created_at=exp.created_at,
            updated_at=exp.updated_at,
            notes=exp.notes
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
            started_at=exp.started_at,
            completed_at=exp.completed_at,
            created_at=exp.created_at,
            updated_at=exp.updated_at,
            notes=exp.notes
        )
        for exp in experiments
    ]


@router.patch("/experiments/{run_id}/transition")
async def transition_experiment(run_id: str, status: str):
    """Transition experiment to a new status."""
    success = experiment_service.transition_to(run_id, status)

    if not success:
        raise HTTPException(status_code=404, detail=f"Experiment with run_id {run_id} not found")

    return {"success": True, "run_id": run_id, "status": status}


@router.patch("/experiments/{run_id}/complete")
async def complete_experiment(run_id: str, metrics: ExperimentMetricsRequest):
    """Mark experiment as COMPLETED and update training metrics."""
    success = experiment_service.complete_training(
        run_id=run_id,
        train_loss=metrics.train_loss,
        validation_loss=metrics.validation_loss
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
    """Update experiment training metrics."""
    success = experiment_service.update_training_metrics(
        run_id=run_id,
        train_loss=metrics.train_loss,
        validation_loss=metrics.validation_loss
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
        training_experiments=analytics.training_experiments,
        created_experiments=analytics.created_experiments,
        completion_rate=analytics.completion_rate,
        failure_rate=analytics.failure_rate,
        avg_train_loss=analytics.avg_train_loss,
        avg_validation_loss=analytics.avg_validation_loss,
        best_validation_loss_run_id=analytics.best_validation_loss_run_id,
        worst_validation_loss_run_id=analytics.worst_validation_loss_run_id
    )
