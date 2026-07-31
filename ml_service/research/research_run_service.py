from typing import List, Optional, Any, Union, Tuple, Dict
from ml_service.research.models import ResearchRun
from ml_service.research.research_run import ResearchRunManager
from ml_service.research.research_run_repository import ResearchRunRepository


class ResearchRunService:
    """
    Business-level service that orchestrates ResearchRunManager and ResearchRunRepository.
    Exposes operations for run creation, retrieval, deletion, existence checking,
    filtering, and lifecycle transitions, keeping state synchronized.
    """
    def __init__(
        self,
        repository: ResearchRunRepository,
        run_manager: ResearchRunManager
    ) -> None:
        self.repository = repository
        self.run_manager = run_manager

    def create_run(
        self,
        experiment_id: str,
        hyperparameters: Union[Dict[str, Any], Tuple[Tuple[str, Union[str, int, float, bool, None]], ...]] = (),
        run_id: Optional[str] = None,
        created_at: Optional[str] = None,
        session_id: str = ""
    ) -> ResearchRun:
        """
        Creates a new run, validates it, registers it in the manager,
        and persists it to the repository. Rejects duplicates.
        """
        if run_id is not None and self.repository.exists(run_id):
            raise ValueError(f"Run with ID '{run_id}' already exists.")

        run = self.run_manager.create_run(
            experiment_id=experiment_id,
            hyperparameters=hyperparameters,
            run_id=run_id,
            created_at=created_at,
            session_id=session_id
        )
        self.repository.save(run)
        return run

    def get_run(self, run_id: str) -> ResearchRun:
        """Retrieves a run from the repository."""
        return self.repository.get(run_id)

    def exists(self, run_id: str) -> bool:
        """Checks if a run exists in the repository."""
        return self.repository.exists(run_id)

    def delete_run(self, run_id: str) -> None:
        """Deletes a run from both the manager and the repository."""
        if run_id in self.run_manager._runs:
            del self.run_manager._runs[run_id]
        self.repository.delete(run_id)

    def list_runs(self) -> List[ResearchRun]:
        """Lists all runs sorted by ID."""
        return self.repository.list()

    def list_by_experiment(self, experiment_id: str) -> List[ResearchRun]:
        """Lists all runs belonging to an experiment sorted by ID."""
        return self.repository.list_by_experiment(experiment_id)

    def list_by_session(self, session_id: str) -> List[ResearchRun]:
        """Lists all runs belonging to a session sorted by ID."""
        return self.repository.list_by_session(session_id)

    def start_run(self, run_id: str) -> ResearchRun:
        """Transitions a run to RUNNING."""
        run = self.get_run(run_id)
        if run_id not in self.run_manager._runs:
            self.run_manager._runs[run_id] = run

        updated = self.run_manager.start_run(run_id)
        self.repository.delete(run_id)
        self.repository.save(updated)
        return updated

    def complete_run(
        self,
        run_id: str,
        metrics: Union[Dict[str, float], Tuple[Tuple[str, float], ...]] = (),
        model_binary_path: Optional[str] = None,
        completed_at: Optional[str] = None
    ) -> ResearchRun:
        """Transitions a run to COMPLETED."""
        run = self.get_run(run_id)
        if run_id not in self.run_manager._runs:
            self.run_manager._runs[run_id] = run

        updated = self.run_manager.complete_run(
            run_id=run_id,
            metrics=metrics,
            model_binary_path=model_binary_path,
            completed_at=completed_at
        )
        self.repository.delete(run_id)
        self.repository.save(updated)
        return updated

    def fail_run(self, run_id: str, completed_at: Optional[str] = None) -> ResearchRun:
        """Transitions a run to FAILED."""
        run = self.get_run(run_id)
        if run_id not in self.run_manager._runs:
            self.run_manager._runs[run_id] = run

        updated = self.run_manager.fail_run(run_id=run_id, completed_at=completed_at)
        self.repository.delete(run_id)
        self.repository.save(updated)
        return updated

    def cancel_run(self, run_id: str, completed_at: Optional[str] = None) -> ResearchRun:
        """Transitions a run to CANCELLED."""
        run = self.get_run(run_id)
        if run_id not in self.run_manager._runs:
            self.run_manager._runs[run_id] = run

        updated = self.run_manager.cancel_run(run_id=run_id, completed_at=completed_at)
        self.repository.delete(run_id)
        self.repository.save(updated)
        return updated
