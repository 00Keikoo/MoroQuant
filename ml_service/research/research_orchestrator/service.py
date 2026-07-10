"""Service layer for research orchestrator."""

import traceback
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from ml_service.research.research_orchestrator.repository import ResearchOrchestratorRepository
from ml_service.research.research_orchestrator.types import (
    ResearchJob,
    JobState,
    JobConfig,
    JobStep,
    JobLog,
    StageType,
    StageResult
)
from ml_service.research.snapshot_engine.service import SnapshotService
from ml_service.research.dataset_manager.service import DatasetService
from ml_service.research.feature_store.service import FeatureService
from ml_service.research.experiment_engine.service import ExperimentService
from ml_service.research.evaluation_engine.service import EvaluationService
from ml_service.research.model_registry.service import ModelRegistryService
from ml_service.research.research_dashboard.service import ResearchDashboardService


class ResearchOrchestratorService:
    """Sequential research pipeline orchestrator per ADR-014."""

    def __init__(self, repository: Optional[ResearchOrchestratorRepository] = None):
        self.repository = repository or ResearchOrchestratorRepository()

        self.snapshot_service = SnapshotService()
        self.dataset_service = DatasetService()
        self.feature_service = FeatureService()
        self.experiment_service = ExperimentService()
        self.evaluation_service = EvaluationService()
        self.registry_service = ModelRegistryService()
        self.dashboard_service = ResearchDashboardService()

    def create_job(self, config: JobConfig, created_by: str = "system") -> ResearchJob:
        """Create new research job."""
        job_id = f"job_{uuid.uuid4().hex[:12]}"

        job = ResearchJob(
            job_id=job_id,
            state=JobState.CREATED,
            config=config,
            created_at=datetime.utcnow().isoformat(),
            created_by=created_by
        )

        self.repository.save_job(job)
        self._log(job_id, "INFO", f"Job created: {job_id}")

        return job

    def start_job(self, job_id: str) -> bool:
        """Start job execution."""
        job = self.repository.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        if job.state != JobState.CREATED:
            raise ValueError(f"Job must be in CREATED state, found: {job.state.value}")

        self.repository.update_job_state(
            job_id,
            JobState.RUNNING,
            started_at=datetime.utcnow().isoformat()
        )

        self._log(job_id, "INFO", "Pipeline execution started")

        try:
            self._execute_pipeline(job_id, job.config)

            self.repository.update_job_state(
                job_id,
                JobState.COMPLETED,
                completed_at=datetime.utcnow().isoformat()
            )
            self._log(job_id, "INFO", "Pipeline execution completed successfully")
            return True

        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()

            self._log(job_id, "ERROR", f"Pipeline failed: {error_msg}")
            self._log(job_id, "DEBUG", f"Traceback: {error_trace}")

            current_job = self.repository.get_job(job_id)
            error_stage = current_job.error_stage if current_job else None

            self.repository.update_job_state(
                job_id,
                JobState.FAILED,
                completed_at=datetime.utcnow().isoformat(),
                error_message=error_msg,
                error_stage=error_stage
            )
            return False

    def _execute_pipeline(self, job_id: str, config: JobConfig) -> None:
        """Execute pipeline stages sequentially."""

        snapshot_result, snapshot_obj = self._execute_stage_snapshot(job_id, config)
        dataset_result = self._execute_stage_dataset(job_id, config, snapshot_result, snapshot_obj)
        feature_result = self._execute_stage_feature(job_id, config, dataset_result)
        experiment_result = self._execute_stage_experiment(job_id, config, feature_result)
        evaluation_result = self._execute_stage_evaluation(job_id, config, experiment_result)
        registry_result = self._execute_stage_registry(job_id, config, evaluation_result)
        self._execute_stage_dashboard(job_id, config, registry_result)

    def _execute_stage_snapshot(self, job_id: str, config: JobConfig) -> tuple[StageResult, Any]:
        """Execute Snapshot stage."""
        step_id = f"{job_id}_snapshot"
        stage_type = StageType.SNAPSHOT
        started_at = datetime.utcnow().isoformat()

        self._log(job_id, "INFO", "Stage: SNAPSHOT started", stage_type)

        step = JobStep(
            step_id=step_id,
            job_id=job_id,
            stage_type=stage_type,
            status="RUNNING",
            started_at=started_at
        )
        self.repository.save_step(step)

        try:
            snapshot = self.snapshot_service.create_snapshot(symbol=config.symbol)

            output_metadata = {
                "snapshot_id": snapshot.snapshot_id,
                "snapshot_timestamp": snapshot.timestamp,
                "trade_count": len(snapshot.trades),
                "signal_count": len(snapshot.signals)
            }
            completed_at = datetime.utcnow().isoformat()

            self.repository.update_step(
                step_id,
                status="COMPLETED",
                completed_at=completed_at,
                output_metadata=output_metadata
            )

            self._log(job_id, "INFO", f"Stage: SNAPSHOT completed - {snapshot.snapshot_id}", stage_type)

            stage_result = StageResult(
                stage_type=stage_type,
                status="COMPLETED",
                started_at=started_at,
                completed_at=completed_at,
                output_metadata=output_metadata
            )

            return stage_result, snapshot

        except Exception as e:
            error_msg = str(e)
            self.repository.update_step(
                step_id,
                status="FAILED",
                completed_at=datetime.utcnow().isoformat(),
                error_message=error_msg
            )
            self.repository.update_job_state(job_id, JobState.FAILED, error_stage=stage_type)
            raise

    def _execute_stage_dataset(
        self,
        job_id: str,
        config: JobConfig,
        snapshot_result: StageResult,
        snapshot: Any
    ) -> StageResult:
        """Execute Dataset stage."""
        step_id = f"{job_id}_dataset"
        stage_type = StageType.DATASET
        started_at = datetime.utcnow().isoformat()

        self._log(job_id, "INFO", "Stage: DATASET started", stage_type)

        step = JobStep(
            step_id=step_id,
            job_id=job_id,
            stage_type=stage_type,
            status="RUNNING",
            started_at=started_at
        )
        self.repository.save_step(step)

        try:
            dataset_metadata, _ = self.dataset_service.create_dataset(
                snapshot=snapshot,
                version="1.0.0",
                symbol_filter=config.symbol
            )

            output_metadata = {
                "dataset_id": dataset_metadata.dataset_id,
                "snapshot_id": snapshot_result.output_metadata["snapshot_id"]
            }
            completed_at = datetime.utcnow().isoformat()

            self.repository.update_step(
                step_id,
                status="COMPLETED",
                completed_at=completed_at,
                output_metadata=output_metadata
            )

            self._log(job_id, "INFO", f"Stage: DATASET completed - {dataset_metadata.dataset_id}", stage_type)

            return StageResult(
                stage_type=stage_type,
                status="COMPLETED",
                started_at=started_at,
                completed_at=completed_at,
                output_metadata=output_metadata
            )

        except Exception as e:
            error_msg = str(e)
            self.repository.update_step(
                step_id,
                status="FAILED",
                completed_at=datetime.utcnow().isoformat(),
                error_message=error_msg
            )
            self.repository.update_job_state(job_id, JobState.FAILED, error_stage=stage_type)
            raise

    def _execute_stage_feature(
        self,
        job_id: str,
        config: JobConfig,
        dataset_result: StageResult
    ) -> StageResult:
        """Execute Feature stage."""
        step_id = f"{job_id}_feature"
        stage_type = StageType.FEATURE
        started_at = datetime.utcnow().isoformat()

        self._log(job_id, "INFO", "Stage: FEATURE started", stage_type)

        step = JobStep(
            step_id=step_id,
            job_id=job_id,
            stage_type=stage_type,
            status="RUNNING",
            started_at=started_at
        )
        self.repository.save_step(step)

        try:
            dataset_id = dataset_result.output_metadata["dataset_id"]
            dataset_metadata, df = self.dataset_service.get_dataset(dataset_id)

            feature_params = config.parameters.get("feature_params", {})

            feature_dataset = self.feature_service.compute_feature_dataset(
                dataset_metadata=dataset_metadata,
                raw_data=df,
                feature_names=feature_params.get("features", ["rsi_14", "macd"]),
                version="1.0.0"
            )

            output_metadata = {
                "feature_dataset_id": feature_dataset.feature_dataset_id,
                "dataset_id": dataset_id,
                "snapshot_id": dataset_result.output_metadata["snapshot_id"]
            }
            completed_at = datetime.utcnow().isoformat()

            self.repository.update_step(
                step_id,
                status="COMPLETED",
                completed_at=completed_at,
                output_metadata=output_metadata
            )

            self._log(job_id, "INFO", f"Stage: FEATURE completed - {feature_dataset.feature_dataset_id}", stage_type)

            return StageResult(
                stage_type=stage_type,
                status="COMPLETED",
                started_at=started_at,
                completed_at=completed_at,
                output_metadata=output_metadata
            )

        except Exception as e:
            error_msg = str(e)
            self.repository.update_step(
                step_id,
                status="FAILED",
                completed_at=datetime.utcnow().isoformat(),
                error_message=error_msg
            )
            self.repository.update_job_state(job_id, JobState.FAILED, error_stage=stage_type)
            raise

    def _execute_stage_experiment(
        self,
        job_id: str,
        config: JobConfig,
        feature_result: StageResult
    ) -> StageResult:
        """Execute Experiment stage."""
        step_id = f"{job_id}_experiment"
        stage_type = StageType.EXPERIMENT
        started_at = datetime.utcnow().isoformat()

        self._log(job_id, "INFO", "Stage: EXPERIMENT started", stage_type)

        step = JobStep(
            step_id=step_id,
            job_id=job_id,
            stage_type=stage_type,
            status="RUNNING",
            started_at=started_at
        )
        self.repository.save_step(step)

        try:
            from ml_service.research.experiment_engine.types import ExperimentConfig, StrategyConfig

            experiment_id = f"exp_{job_id}"
            snapshot_id = feature_result.output_metadata.get("snapshot_id", "")

            experiment_params = config.parameters.get("experiment_params", {})
            configs = experiment_params.get("strategy_configs", [])

            if not configs:
                configs = [
                    StrategyConfig(
                        config_id="default",
                        threshold_long=0.5,
                        threshold_short=0.5,
                        enable_filter=False
                    )
                ]
            else:
                configs = [
                    StrategyConfig(**cfg) if isinstance(cfg, dict) else cfg
                    for cfg in configs
                ]

            experiment_config = ExperimentConfig(
                experiment_id=experiment_id,
                snapshot_id=snapshot_id,
                configs=configs
            )

            model_id = f"mdl_{config.symbol}_{config.algorithm}"
            artifact_dir = Path(__file__).parent.parent.parent.parent / "storage" / "models" / model_id

            experiment_result = self.experiment_service.run_experiment(
                experiment_config,
                artifact_dir=str(artifact_dir)
            )

            if experiment_result is None:
                raise ValueError(f"Experiment failed: snapshot {snapshot_id} not found")

            best_config_id = experiment_result.results[0].config_id if experiment_result.results else "default"

            output_metadata = {
                "experiment_id": experiment_id,
                "best_config_id": best_config_id,
                "feature_dataset_id": feature_result.output_metadata["feature_dataset_id"],
                "dataset_id": feature_result.output_metadata["dataset_id"],
                "snapshot_id": snapshot_id,
                "experiment_result": experiment_result,
                "artifact_path": experiment_result.artifact_path
            }
            completed_at = datetime.utcnow().isoformat()

            self.repository.update_step(
                step_id,
                status="COMPLETED",
                completed_at=completed_at,
                output_metadata=output_metadata
            )

            self._log(job_id, "INFO", f"Stage: EXPERIMENT completed - {experiment_id}", stage_type)

            return StageResult(
                stage_type=stage_type,
                status="COMPLETED",
                started_at=started_at,
                completed_at=completed_at,
                output_metadata=output_metadata
            )

        except Exception as e:
            error_msg = str(e)
            self.repository.update_step(
                step_id,
                status="FAILED",
                completed_at=datetime.utcnow().isoformat(),
                error_message=error_msg
            )
            self.repository.update_job_state(job_id, JobState.FAILED, error_stage=stage_type)
            raise

    def _execute_stage_evaluation(
        self,
        job_id: str,
        config: JobConfig,
        experiment_result: StageResult
    ) -> StageResult:
        """Execute Evaluation stage."""
        step_id = f"{job_id}_evaluation"
        stage_type = StageType.EVALUATION
        started_at = datetime.utcnow().isoformat()

        self._log(job_id, "INFO", "Stage: EVALUATION started", stage_type)

        step = JobStep(
            step_id=step_id,
            job_id=job_id,
            stage_type=stage_type,
            status="RUNNING",
            started_at=started_at
        )
        self.repository.save_step(step)

        try:
            exp_result = experiment_result.output_metadata["experiment_result"]

            evaluation_result = self.evaluation_service.evaluate(exp_result)

            best_strategy = evaluation_result.best_strategy_id
            best_score = next(
                (s for s in evaluation_result.strategy_scores if s.config_id == best_strategy),
                evaluation_result.strategy_scores[0] if evaluation_result.strategy_scores else None
            )

            if best_score is None:
                raise ValueError("No strategy scores available from evaluation")

            output_metadata = {
                "experiment_id": experiment_result.output_metadata["experiment_id"],
                "best_strategy_id": best_strategy,
                "dataset_id": experiment_result.output_metadata["dataset_id"],
                "feature_dataset_id": experiment_result.output_metadata["feature_dataset_id"],
                "snapshot_id": experiment_result.output_metadata["snapshot_id"],
                "artifact_path": experiment_result.output_metadata.get("artifact_path"),
                "metrics": {
                    "sharpe_ratio": best_score.sharpe_ratio,
                    "max_drawdown": best_score.max_drawdown,
                    "win_rate": best_score.win_rate,
                    "profit_factor": best_score.profit_factor,
                    "sortino_ratio": best_score.sortino_ratio,
                    "trade_count": best_score.trade_count
                },
                "evaluation_result": evaluation_result
            }
            completed_at = datetime.utcnow().isoformat()

            self.repository.update_step(
                step_id,
                status="COMPLETED",
                completed_at=completed_at,
                output_metadata=output_metadata
            )

            self._log(job_id, "INFO", f"Stage: EVALUATION completed - {output_metadata['experiment_id']}", stage_type)

            return StageResult(
                stage_type=stage_type,
                status="COMPLETED",
                started_at=started_at,
                completed_at=completed_at,
                output_metadata=output_metadata
            )

        except Exception as e:
            error_msg = str(e)
            self.repository.update_step(
                step_id,
                status="FAILED",
                completed_at=datetime.utcnow().isoformat(),
                error_message=error_msg
            )
            self.repository.update_job_state(job_id, JobState.FAILED, error_stage=stage_type)
            raise

    def _execute_stage_registry(
        self,
        job_id: str,
        config: JobConfig,
        evaluation_result: StageResult
    ) -> StageResult:
        """Execute Registry stage."""
        step_id = f"{job_id}_registry"
        stage_type = StageType.REGISTRY
        started_at = datetime.utcnow().isoformat()

        self._log(job_id, "INFO", "Stage: REGISTRY started", stage_type)

        step = JobStep(
            step_id=step_id,
            job_id=job_id,
            stage_type=stage_type,
            status="RUNNING",
            started_at=started_at
        )
        self.repository.save_step(step)

        try:
            from ml_service.research.model_registry.model_types import RegistrationRequest
            from pathlib import Path

            experiment_id = evaluation_result.output_metadata["experiment_id"]
            best_strategy_id = evaluation_result.output_metadata["best_strategy_id"]
            metrics = evaluation_result.output_metadata["metrics"]

            model_id = f"mdl_{config.symbol}_{config.algorithm}"

            artifact_path = evaluation_result.output_metadata.get("artifact_path")
            if not artifact_path:
                raise ValueError(f"No artifact path from experiment stage for {experiment_id}")

            storage_path = Path(artifact_path).parent

            registry_params = config.parameters.get("registry_params", {})
            hyperparameters = registry_params.get("hyperparameters", {
                "threshold_long": 0.5,
                "threshold_short": 0.5,
                "enable_filter": False
            })

            dataset_id = evaluation_result.output_metadata.get("dataset_id", "unknown")
            feature_dataset_id = evaluation_result.output_metadata.get("feature_dataset_id", "unknown")
            snapshot_id = evaluation_result.output_metadata.get("snapshot_id", "unknown")

            request = RegistrationRequest(
                model_id=model_id,
                version_bump="minor",
                storage_path=str(storage_path),
                hyperparameters=hyperparameters,
                lineage={
                    "snapshot_id": snapshot_id,
                    "dataset_id": dataset_id,
                    "feature_dataset_id": feature_dataset_id,
                    "experiment_id": experiment_id,
                    "best_config_id": best_strategy_id
                },
                symbol=config.symbol,
                timeframe=config.timeframe,
                algorithm=config.algorithm
            )

            model_version = self.registry_service.register_candidate(request)

            output_metadata = {
                "model_version_id": model_version.model_version_id,
                "evaluation_id": evaluation_result.output_metadata["evaluation_id"],
                "experiment_id": experiment_id,
                "storage_path": str(storage_path)
            }
            completed_at = datetime.utcnow().isoformat()

            self.repository.update_step(
                step_id,
                status="COMPLETED",
                completed_at=completed_at,
                output_metadata=output_metadata
            )

            self._log(job_id, "INFO", f"Stage: REGISTRY completed - {model_version.model_version_id}", stage_type)

            return StageResult(
                stage_type=stage_type,
                status="COMPLETED",
                started_at=started_at,
                completed_at=completed_at,
                output_metadata=output_metadata
            )

        except Exception as e:
            error_msg = str(e)
            self.repository.update_step(
                step_id,
                status="FAILED",
                completed_at=datetime.utcnow().isoformat(),
                error_message=error_msg
            )
            self.repository.update_job_state(job_id, JobState.FAILED, error_stage=stage_type)
            raise

    def _execute_stage_dashboard(
        self,
        job_id: str,
        config: JobConfig,
        registry_result: StageResult
    ) -> StageResult:
        """Execute Dashboard stage."""
        step_id = f"{job_id}_dashboard"
        stage_type = StageType.DASHBOARD
        started_at = datetime.utcnow().isoformat()

        self._log(job_id, "INFO", "Stage: DASHBOARD started", stage_type)

        step = JobStep(
            step_id=step_id,
            job_id=job_id,
            stage_type=stage_type,
            status="RUNNING",
            started_at=started_at
        )
        self.repository.save_step(step)

        try:
            experiment_id = registry_result.output_metadata.get("experiment_id")
            model_version_id = registry_result.output_metadata["model_version_id"]

            experiment_detail = None
            lineage = None
            evaluation = None

            if experiment_id:
                experiment_detail = self.dashboard_service.get_experiment(experiment_id)
                lineage = self.dashboard_service.get_lineage(experiment_id)
                evaluation = self.dashboard_service.get_evaluation(experiment_id)

            output_metadata = {
                "dashboard_updated": True,
                "model_version_id": model_version_id,
                "experiment_id": experiment_id,
                "has_experiment_detail": experiment_detail is not None,
                "has_lineage": lineage is not None,
                "has_evaluation": evaluation is not None
            }
            completed_at = datetime.utcnow().isoformat()

            self.repository.update_step(
                step_id,
                status="COMPLETED",
                completed_at=completed_at,
                output_metadata=output_metadata
            )

            self._log(job_id, "INFO", "Stage: DASHBOARD completed", stage_type)

            return StageResult(
                stage_type=stage_type,
                status="COMPLETED",
                started_at=started_at,
                completed_at=completed_at,
                output_metadata=output_metadata
            )

        except Exception as e:
            error_msg = str(e)
            self.repository.update_step(
                step_id,
                status="FAILED",
                completed_at=datetime.utcnow().isoformat(),
                error_message=error_msg
            )
            self.repository.update_job_state(job_id, JobState.FAILED, error_stage=stage_type)
            raise

    def cancel_job(self, job_id: str) -> None:
        """Cancel a running job."""
        job = self.repository.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        if job.state not in [JobState.CREATED, JobState.RUNNING]:
            raise ValueError(f"Cannot cancel job in {job.state.value} state")

        self.repository.update_job_state(
            job_id,
            JobState.CANCELLED,
            completed_at=datetime.utcnow().isoformat()
        )
        self._log(job_id, "INFO", "Job cancelled")

    def get_job(self, job_id: str) -> Optional[ResearchJob]:
        """Get job by ID."""
        return self.repository.get_job(job_id)

    def get_job_steps(self, job_id: str) -> list:
        """Get all steps for a job."""
        return self.repository.get_steps(job_id)

    def get_job_logs(self, job_id: str, level: Optional[str] = None) -> list:
        """Get logs for a job."""
        return self.repository.get_logs(job_id, level)

    def _log(
        self,
        job_id: str,
        level: str,
        message: str,
        stage_type: Optional[StageType] = None
    ) -> None:
        """Log execution event."""
        log = JobLog(
            log_id=f"log_{uuid.uuid4().hex[:12]}",
            job_id=job_id,
            timestamp=datetime.utcnow().isoformat(),
            level=level,
            message=message,
            stage_type=stage_type
        )
        self.repository.save_log(log)
