"""Experiment Service for managing experiment lifecycle.

Service layer supporting flexible state machine transitions.
Removed coupled metrics - those belong to their respective registries.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from ml_service.lab.experiments.types import ExperimentContract
from ml_service.lab.experiments.repository import ExperimentRepository


class ExperimentService:
    """Service layer for experiment lifecycle management."""

    def __init__(self, repository: ExperimentRepository = None):
        self.repository = repository or ExperimentRepository()

    def create_experiment(
        self,
        experiment_id: str,
        dataset_version: Optional[str] = None,
        feature_version: Optional[str] = None,
        model_version: Optional[str] = None,
        hyperparameters: Optional[str] = None,
        notes: Optional[str] = None
    ) -> ExperimentContract:
        """Create a new experiment run.

        Args:
            experiment_id: Experiment identifier (groups multiple runs)
            dataset_version: Dataset version used
            feature_version: Feature version used
            model_version: Model version used
            hyperparameters: JSON string of hyperparameters
            notes: Optional notes

        Returns:
            Created ExperimentContract
        """
        run_id = str(uuid4())
        started_at = datetime.now(timezone.utc).isoformat()

        experiment = ExperimentContract(
            id=None,
            experiment_id=experiment_id,
            run_id=run_id,
            status='CREATED',
            dataset_version=dataset_version,
            feature_version=feature_version,
            model_version=model_version,
            hyperparameters=hyperparameters,
            train_loss=None,
            validation_loss=None,
            started_at=started_at,
            completed_at=None,
            created_at=None,
            updated_at=None,
            notes=notes
        )

        experiment_id_db = self.repository.create(experiment)
        return self.repository.get_by_id(experiment_id_db)

    def transition_to(self, run_id: str, status: str) -> bool:
        """Transition experiment to a new status.

        Supports flexible lifecycle:
        CREATED -> TRAINING -> VALIDATING -> CALIBRATING -> PAPER ->
        PROMOTION -> PRODUCTION -> ARCHIVED

        Or FAILED at any point.

        Args:
            run_id: Run identifier
            status: Target status

        Returns:
            True if updated successfully
        """
        return self.repository.update_status(run_id, status)

    def start_training(self, run_id: str) -> bool:
        """Mark experiment as TRAINING."""
        return self.transition_to(run_id, 'TRAINING')

    def complete_training(
        self,
        run_id: str,
        train_loss: Optional[float] = None,
        validation_loss: Optional[float] = None
    ) -> bool:
        """Complete training phase and update loss metrics.

        Args:
            run_id: Run identifier
            train_loss: Final training loss
            validation_loss: Final validation loss

        Returns:
            True if updated successfully
        """
        metrics_updated = self.repository.update_metrics(
            run_id=run_id,
            train_loss=train_loss,
            validation_loss=validation_loss
        )
        if not metrics_updated and (train_loss is None and validation_loss is None):
            return False
        return self.transition_to(run_id, 'COMPLETED')

    def fail_run(self, run_id: str) -> bool:
        """Mark experiment as FAILED."""
        return self.transition_to(run_id, 'FAILED')

    def update_training_metrics(
        self,
        run_id: str,
        train_loss: Optional[float] = None,
        validation_loss: Optional[float] = None
    ) -> bool:
        """Update training metrics during experiment execution."""
        return self.repository.update_metrics(
            run_id=run_id,
            train_loss=train_loss,
            validation_loss=validation_loss
        )

    def get_run(self, run_id: str) -> Optional[ExperimentContract]:
        """Get experiment by run_id."""
        return self.repository.get_by_run_id(run_id)

    def get_experiment_runs(self, experiment_id: str) -> List[ExperimentContract]:
        """Get all runs for an experiment."""
        return self.repository.get_by_experiment_id(experiment_id)

    def list_all_runs(self, limit: int = 100, offset: int = 0) -> List[ExperimentContract]:
        """List all experiments with pagination."""
        return self.repository.list_all(limit=limit, offset=offset)

    def list_by_status(self, status: str) -> List[ExperimentContract]:
        """Get experiments by status."""
        return self.repository.list_by_status(status)

    def delete_run(self, run_id: str) -> bool:
        """Delete an experiment run."""
        return self.repository.delete(run_id)

    def get_run_count(self) -> int:
        """Get total run count."""
        return self.repository.count_all()

    def get_status_count(self, status: str) -> int:
        """Get count of runs by status."""
        return self.repository.count_by_status(status)
