"""Analytics layer for research orchestrator."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from ml_service.research.research_orchestrator.repository import ResearchOrchestratorRepository
from ml_service.research.research_orchestrator.types import (
    JobState,
    StageType,
    PipelineMetrics
)


@dataclass
class StageReliability:
    """Reliability metrics for a pipeline stage."""
    stage_type: StageType
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    avg_duration_seconds: float
    p50_duration_seconds: float
    p95_duration_seconds: float


@dataclass
class PipelineAnalytics:
    """Aggregate pipeline analytics."""
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    cancelled_jobs: int
    success_rate: float
    avg_pipeline_duration_seconds: float
    stage_reliabilities: List[StageReliability]
    bottleneck_stage: Optional[StageType]


class ResearchOrchestratorAnalytics:
    """Analytics service for pipeline metrics."""

    def __init__(self, repository: Optional[ResearchOrchestratorRepository] = None):
        self.repository = repository or ResearchOrchestratorRepository()

    def compute_job_metrics(self, job_id: str) -> Optional[PipelineMetrics]:
        """Compute metrics for a specific job."""
        job = self.repository.get_job(job_id)
        if not job:
            return None

        steps = self.repository.get_steps(job_id)

        stage_durations = {}
        for step in steps:
            if step.completed_at and step.started_at:
                start = datetime.fromisoformat(step.started_at)
                end = datetime.fromisoformat(step.completed_at)
                duration = (end - start).total_seconds()
                stage_durations[step.stage_type.value] = duration

        total_duration = 0.0
        if job.started_at and job.completed_at:
            start = datetime.fromisoformat(job.started_at)
            end = datetime.fromisoformat(job.completed_at)
            total_duration = (end - start).total_seconds()

        success = job.state == JobState.COMPLETED
        failed_stage = None
        if job.state == JobState.FAILED and job.error_stage:
            failed_stage = job.error_stage.value

        return PipelineMetrics(
            job_id=job_id,
            total_duration_seconds=total_duration,
            stage_durations=stage_durations,
            success=success,
            failed_stage=failed_stage
        )

    def compute_stage_reliability(self, stage_type: StageType, limit: int = 100) -> StageReliability:
        """Compute reliability metrics for a specific stage."""
        jobs = self.repository.list_jobs(limit=limit)

        durations = []
        total_executions = 0
        successful_executions = 0
        failed_executions = 0

        for job in jobs:
            steps = self.repository.get_steps(job.job_id)
            for step in steps:
                if step.stage_type == stage_type:
                    total_executions += 1

                    if step.status == "COMPLETED":
                        successful_executions += 1

                        if step.completed_at and step.started_at:
                            start = datetime.fromisoformat(step.started_at)
                            end = datetime.fromisoformat(step.completed_at)
                            duration = (end - start).total_seconds()
                            durations.append(duration)
                    elif step.status == "FAILED":
                        failed_executions += 1

        success_rate = successful_executions / total_executions if total_executions > 0 else 0.0
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        durations_sorted = sorted(durations)
        p50 = durations_sorted[len(durations_sorted) // 2] if durations_sorted else 0.0
        p95_idx = int(len(durations_sorted) * 0.95)
        p95 = durations_sorted[p95_idx] if durations_sorted else 0.0

        return StageReliability(
            stage_type=stage_type,
            total_executions=total_executions,
            successful_executions=successful_executions,
            failed_executions=failed_executions,
            success_rate=success_rate,
            avg_duration_seconds=avg_duration,
            p50_duration_seconds=p50,
            p95_duration_seconds=p95
        )

    def compute_pipeline_analytics(self, limit: int = 100) -> PipelineAnalytics:
        """Compute aggregate pipeline analytics."""
        jobs = self.repository.list_jobs(limit=limit)

        total_jobs = len(jobs)
        completed_jobs = sum(1 for j in jobs if j.state == JobState.COMPLETED)
        failed_jobs = sum(1 for j in jobs if j.state == JobState.FAILED)
        cancelled_jobs = sum(1 for j in jobs if j.state == JobState.CANCELLED)

        success_rate = completed_jobs / total_jobs if total_jobs > 0 else 0.0

        pipeline_durations = []
        for job in jobs:
            if job.started_at and job.completed_at:
                start = datetime.fromisoformat(job.started_at)
                end = datetime.fromisoformat(job.completed_at)
                duration = (end - start).total_seconds()
                pipeline_durations.append(duration)

        avg_pipeline_duration = sum(pipeline_durations) / len(pipeline_durations) if pipeline_durations else 0.0

        stage_types = [
            StageType.SNAPSHOT,
            StageType.DATASET,
            StageType.FEATURE,
            StageType.EXPERIMENT,
            StageType.EVALUATION,
            StageType.REGISTRY,
            StageType.DASHBOARD
        ]

        stage_reliabilities = []
        for stage_type in stage_types:
            reliability = self.compute_stage_reliability(stage_type, limit)
            stage_reliabilities.append(reliability)

        bottleneck_stage = None
        max_avg_duration = 0.0
        for reliability in stage_reliabilities:
            if reliability.avg_duration_seconds > max_avg_duration:
                max_avg_duration = reliability.avg_duration_seconds
                bottleneck_stage = reliability.stage_type

        return PipelineAnalytics(
            total_jobs=total_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            cancelled_jobs=cancelled_jobs,
            success_rate=success_rate,
            avg_pipeline_duration_seconds=avg_pipeline_duration,
            stage_reliabilities=stage_reliabilities,
            bottleneck_stage=bottleneck_stage
        )

    def get_failure_patterns(self, limit: int = 50) -> Dict[str, int]:
        """Identify which stages fail most frequently."""
        jobs = self.repository.list_jobs(state=JobState.FAILED, limit=limit)

        failure_counts = {}
        for job in jobs:
            if job.error_stage:
                stage_name = job.error_stage.value
                failure_counts[stage_name] = failure_counts.get(stage_name, 0) + 1

        return dict(sorted(failure_counts.items(), key=lambda x: x[1], reverse=True))

    def get_recent_jobs_summary(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get summary of recent jobs."""
        jobs = self.repository.list_jobs(limit=limit)

        summaries = []
        for job in jobs:
            metrics = self.compute_job_metrics(job.job_id)

            summary = {
                'job_id': job.job_id,
                'state': job.state.value,
                'created_at': job.created_at,
                'duration_seconds': metrics.total_duration_seconds if metrics else 0.0,
                'config': {
                    'symbol': job.config.symbol,
                    'timeframe': job.config.timeframe,
                    'algorithm': job.config.algorithm
                },
                'error_stage': job.error_stage.value if job.error_stage else None,
                'error_message': job.error_message
            }
            summaries.append(summary)

        return summaries
