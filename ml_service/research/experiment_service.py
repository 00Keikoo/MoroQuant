from typing import List, Optional, Any, Union, Tuple, Dict
from ml_service.research.models import ResearchExperiment, ResearchRun
from ml_service.research.research_experiment import ResearchExperimentManager
from ml_service.research.experiment_repository import ExperimentRepository

class ExperimentService:
    """
    Business-level service that orchestrates ResearchExperimentManager and ExperimentRepository.
    Exposes operations for experiment creation, retrieval, deletion, existence checking,
    filtering, and lifecycle transitions, keeping state synchronized.
    """
    def __init__(
        self,
        repository: ExperimentRepository,
        experiment_manager: ResearchExperimentManager
    ) -> None:
        self.repository = repository
        self.experiment_manager = experiment_manager

    def create_experiment(
        self,
        session_id: str,
        hypothesis_config: Union[Dict[str, Any], Tuple[Tuple[str, Union[str, int, float, bool, None]], ...]],
        experiment_id: Optional[str] = None,
        created_at: Optional[str] = None
    ) -> ResearchExperiment:
        """
        Creates a new experiment, validates it, registers it in the manager,
        and persists it to the repository. Rejects duplicates.
        """
        if experiment_id is not None and self.repository.exists(experiment_id):
            raise ValueError(f"Experiment with ID '{experiment_id}' already exists.")

        experiment = self.experiment_manager.create_experiment(
            session_id=session_id,
            hypothesis_config=hypothesis_config,
            experiment_id=experiment_id,
            created_at=created_at
        )
        self.repository.save(experiment)
        return experiment

    def get_experiment(self, experiment_id: str) -> ResearchExperiment:
        """Retrieves an experiment from the repository."""
        return self.repository.get(experiment_id)

    def has_experiment(self, experiment_id: str) -> bool:
        """Checks if an experiment exists in the repository."""
        return self.repository.exists(experiment_id)

    def delete_experiment(self, experiment_id: str) -> None:
        """Deletes an experiment from both the manager and the repository."""
        if experiment_id in self.experiment_manager._experiments:
            del self.experiment_manager._experiments[experiment_id]
        self.repository.delete(experiment_id)

    def list_experiments(self) -> List[ResearchExperiment]:
        """Lists all experiments sorted by ID."""
        return self.repository.list()

    def list_experiments_by_session(self, session_id: str) -> List[ResearchExperiment]:
        """Lists all experiments belonging to a session sorted by ID."""
        return self.repository.list_by_session(session_id)

    def start_experiment(self, experiment_id: str) -> ResearchExperiment:
        """Transitions an experiment to ACTIVE."""
        experiment = self.get_experiment(experiment_id)
        if experiment_id not in self.experiment_manager._experiments:
            self.experiment_manager._experiments[experiment_id] = experiment

        updated = self.experiment_manager.start_experiment(experiment_id)
        self.repository.delete(experiment_id)
        self.repository.save(updated)
        return updated

    def complete_experiment(
        self,
        experiment_id: str,
        runs: Tuple[ResearchRun, ...] = (),
        completed_at: Optional[str] = None
    ) -> ResearchExperiment:
        """Transitions an experiment to EVALUATED."""
        experiment = self.get_experiment(experiment_id)
        if experiment_id not in self.experiment_manager._experiments:
            self.experiment_manager._experiments[experiment_id] = experiment

        updated = self.experiment_manager.complete_experiment(
            experiment_id=experiment_id,
            runs=runs,
            completed_at=completed_at
        )
        self.repository.delete(experiment_id)
        self.repository.save(updated)
        return updated

    def fail_experiment(
        self,
        experiment_id: str,
        runs: Tuple[ResearchRun, ...] = (),
        completed_at: Optional[str] = None
    ) -> ResearchExperiment:
        """Transitions an experiment to FAILED."""
        experiment = self.get_experiment(experiment_id)
        if experiment_id not in self.experiment_manager._experiments:
            self.experiment_manager._experiments[experiment_id] = experiment

        updated = self.experiment_manager.fail_experiment(
            experiment_id=experiment_id,
            runs=runs,
            completed_at=completed_at
        )
        self.repository.delete(experiment_id)
        self.repository.save(updated)
        return updated

    def cancel_experiment(self, experiment_id: str, completed_at: Optional[str] = None) -> ResearchExperiment:
        """Transitions an experiment to CANCELLED."""
        experiment = self.get_experiment(experiment_id)
        if experiment_id not in self.experiment_manager._experiments:
            self.experiment_manager._experiments[experiment_id] = experiment

        updated = self.experiment_manager.cancel_experiment(experiment_id, completed_at=completed_at)
        self.repository.delete(experiment_id)
        self.repository.save(updated)
        return updated
