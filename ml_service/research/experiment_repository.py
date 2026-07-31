import copy
from typing import List

from ml_service.research.models import ResearchExperiment


class ExperimentRepository:
    """
    An in-memory repository responsible ONLY for ResearchExperiment persistence.
    
    Adheres strictly to storing data only, with no business logic, no SQL,
    no filesystem, no logging, no network, and deterministic sorting.
    """
    def __init__(self) -> None:
        self._experiments = {}

    def save(self, experiment: ResearchExperiment) -> ResearchExperiment:
        if not isinstance(experiment, ResearchExperiment):
            raise TypeError("Expected a ResearchExperiment instance.")
        if experiment.experiment_id in self._experiments:
            raise ValueError(f"Experiment with ID '{experiment.experiment_id}' already exists.")
        self._experiments[experiment.experiment_id] = copy.deepcopy(experiment)
        return experiment

    def get(self, experiment_id: str) -> ResearchExperiment:
        if experiment_id not in self._experiments:
            raise KeyError(f"Experiment with ID '{experiment_id}' not found.")
        return self._experiments[experiment_id]

    def exists(self, experiment_id: str) -> bool:
        return experiment_id in self._experiments

    def delete(self, experiment_id: str) -> None:
        if experiment_id not in self._experiments:
            raise KeyError(f"Experiment with ID '{experiment_id}' not found.")
        del self._experiments[experiment_id]

    def list(self) -> List[ResearchExperiment]:
        return sorted(self._experiments.values(), key=lambda e: e.experiment_id)

    def list_by_session(self, session_id: str) -> List[ResearchExperiment]:
        experiments = [e for e in self._experiments.values() if e.session_id == session_id]
        return sorted(experiments, key=lambda e: e.experiment_id)
