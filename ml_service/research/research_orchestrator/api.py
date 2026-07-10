"""API layer for research orchestrator."""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ml_service.research.research_orchestrator.service import ResearchOrchestratorService
from ml_service.research.research_orchestrator.analytics import ResearchOrchestratorAnalytics
from ml_service.research.research_orchestrator.types import JobConfig, JobState


router = APIRouter(prefix="/api/research/orchestrator", tags=["research_orchestrator"])


class CreateJobRequest(BaseModel):
    """Request to create a research job."""
    symbol: str
    timeframe: str
    algorithm: str
    start_date: str
    end_date: str
    parameters: dict
    created_by: str = "system"


class StartJobRequest(BaseModel):
    """Request to start a job."""
    job_id: str


class JobResponse(BaseModel):
    """Job status response."""
    job_id: str
    state: str
    config: dict
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_by: str
    error_message: Optional[str] = None
    error_stage: Optional[str] = None


service = ResearchOrchestratorService()
analytics = ResearchOrchestratorAnalytics()


@router.post("/jobs", response_model=JobResponse)
def create_job(request: CreateJobRequest):
    """Create a new research job."""
    config = JobConfig(
        symbol=request.symbol,
        timeframe=request.timeframe,
        algorithm=request.algorithm,
        start_date=request.start_date,
        end_date=request.end_date,
        parameters=request.parameters
    )

    job = service.create_job(config, created_by=request.created_by)

    return JobResponse(
        job_id=job.job_id,
        state=job.state.value,
        config={
            'symbol': job.config.symbol,
            'timeframe': job.config.timeframe,
            'algorithm': job.config.algorithm,
            'start_date': job.config.start_date,
            'end_date': job.config.end_date,
            'parameters': job.config.parameters
        },
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_by=job.created_by,
        error_message=job.error_message,
        error_stage=job.error_stage.value if job.error_stage else None
    )


@router.post("/jobs/{job_id}/start")
def start_job(job_id: str):
    """Start a research job."""
    try:
        success = service.start_job(job_id)
        job = service.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

        return {
            'job_id': job_id,
            'success': success,
            'state': job.state.value,
            'error_message': job.error_message,
            'error_stage': job.error_stage.value if job.error_stage else None
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    """Cancel a running job."""
    try:
        service.cancel_job(job_id)
        return {'job_id': job_id, 'status': 'cancelled'}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str):
    """Get job status."""
    job = service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return JobResponse(
        job_id=job.job_id,
        state=job.state.value,
        config={
            'symbol': job.config.symbol,
            'timeframe': job.config.timeframe,
            'algorithm': job.config.algorithm,
            'start_date': job.config.start_date,
            'end_date': job.config.end_date,
            'parameters': job.config.parameters
        },
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_by=job.created_by,
        error_message=job.error_message,
        error_stage=job.error_stage.value if job.error_stage else None
    )


@router.get("/jobs/{job_id}/steps")
def get_job_steps(job_id: str):
    """Get all steps for a job."""
    steps = service.get_job_steps(job_id)

    return {
        'job_id': job_id,
        'steps': [
            {
                'step_id': step.step_id,
                'stage_type': step.stage_type.value,
                'status': step.status,
                'started_at': step.started_at,
                'completed_at': step.completed_at,
                'output_metadata': step.output_metadata,
                'error_message': step.error_message
            }
            for step in steps
        ]
    }


@router.get("/jobs/{job_id}/logs")
def get_job_logs(job_id: str, level: Optional[str] = None):
    """Get logs for a job."""
    logs = service.get_job_logs(job_id, level)

    return {
        'job_id': job_id,
        'logs': [
            {
                'log_id': log.log_id,
                'timestamp': log.timestamp,
                'level': log.level,
                'message': log.message,
                'stage_type': log.stage_type.value if log.stage_type else None
            }
            for log in logs
        ]
    }


@router.get("/analytics/pipeline")
def get_pipeline_analytics(limit: int = 100):
    """Get aggregate pipeline analytics."""
    pipeline_analytics = analytics.compute_pipeline_analytics(limit)

    return {
        'total_jobs': pipeline_analytics.total_jobs,
        'completed_jobs': pipeline_analytics.completed_jobs,
        'failed_jobs': pipeline_analytics.failed_jobs,
        'cancelled_jobs': pipeline_analytics.cancelled_jobs,
        'success_rate': pipeline_analytics.success_rate,
        'avg_pipeline_duration_seconds': pipeline_analytics.avg_pipeline_duration_seconds,
        'bottleneck_stage': pipeline_analytics.bottleneck_stage.value if pipeline_analytics.bottleneck_stage else None,
        'stage_reliabilities': [
            {
                'stage_type': r.stage_type.value,
                'total_executions': r.total_executions,
                'successful_executions': r.successful_executions,
                'failed_executions': r.failed_executions,
                'success_rate': r.success_rate,
                'avg_duration_seconds': r.avg_duration_seconds,
                'p50_duration_seconds': r.p50_duration_seconds,
                'p95_duration_seconds': r.p95_duration_seconds
            }
            for r in pipeline_analytics.stage_reliabilities
        ]
    }


@router.get("/analytics/failures")
def get_failure_patterns(limit: int = 50):
    """Get failure pattern analysis."""
    patterns = analytics.get_failure_patterns(limit)
    return {'failure_patterns': patterns}


@router.get("/analytics/recent")
def get_recent_jobs(limit: int = 10):
    """Get summary of recent jobs."""
    summaries = analytics.get_recent_jobs_summary(limit)
    return {'recent_jobs': summaries}
