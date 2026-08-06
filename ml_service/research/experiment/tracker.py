from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from ml_service.research.experiment.models import ExperimentRun

class ExperimentTracker(ABC):
    """
    Interface for the experiment tracking layer.
    Enforces ADR-024 principles: immutability, determinism, isolation, and no database writes.
    """
    @abstractmethod
    def log_run(self, run: ExperimentRun) -> None:
        """
        Track/log a research experiment run.
        Must raise ValueError if a run with the same experiment_id already exists.
        """
        pass

    @abstractmethod
    def get_run(self, experiment_id: str) -> Optional[ExperimentRun]:
        """Retrieve a specific run by experiment_id."""
        pass

    @abstractmethod
    def list_runs(self) -> List[ExperimentRun]:
        """List all tracked runs, sorted deterministically by experiment_id."""
        pass


class DefaultExperimentTracker(ExperimentTracker):
    """
    In-memory, dependency-free implementation of ExperimentTracker.
    Maintains complete isolation, does not perform database writes, and is decoupled from execution.
    """
    def __init__(self) -> None:
        self._runs: Dict[str, ExperimentRun] = {}

    def log_run(self, run: ExperimentRun) -> None:
        if not isinstance(run, ExperimentRun):
            raise TypeError("Value to log must be an instance of ExperimentRun")
        
        # Enforce immutability: runs cannot be overwritten or altered once tracked
        if run.experiment_id in self._runs:
            raise ValueError(f"Experiment run with ID '{run.experiment_id}' has already been tracked.")
        
        self._runs[run.experiment_id] = run

    def get_run(self, experiment_id: str) -> Optional[ExperimentRun]:
        return self._runs.get(experiment_id)

    def list_runs(self) -> List[ExperimentRun]:
        # Return list sorted by experiment_id to ensure deterministic output ordering
        return sorted(self._runs.values(), key=lambda r: r.experiment_id)
