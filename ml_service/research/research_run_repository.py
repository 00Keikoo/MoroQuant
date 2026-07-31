import copy
from typing import List

from ml_service.research.models import ResearchRun


class ResearchRunRepository:
    """
    An in-memory repository responsible ONLY for ResearchRun persistence.
    
    Adheres strictly to storing data only, with no business logic, no SQL,
    no filesystem, no logging, no network, and deterministic sorting.
    """
    def __init__(self) -> None:
        self._runs = {}

    def save(self, run: ResearchRun) -> ResearchRun:
        if not isinstance(run, ResearchRun):
            raise TypeError("Expected a ResearchRun instance.")
        if run.run_id in self._runs:
            raise ValueError(f"ResearchRun with ID '{run.run_id}' already exists.")
        self._runs[run.run_id] = copy.deepcopy(run)
        return run

    def get(self, run_id: str) -> ResearchRun:
        if run_id not in self._runs:
            raise KeyError(f"ResearchRun with ID '{run_id}' not found.")
        return self._runs[run_id]

    def exists(self, run_id: str) -> bool:
        return run_id in self._runs

    def delete(self, run_id: str) -> None:
        if run_id not in self._runs:
            raise KeyError(f"ResearchRun with ID '{run_id}' not found.")
        del self._runs[run_id]

    def list(self) -> List[ResearchRun]:
        return sorted(self._runs.values(), key=lambda r: r.run_id)

    def list_by_experiment(self, experiment_id: str) -> List[ResearchRun]:
        runs = [r for r in self._runs.values() if r.experiment_id == experiment_id]
        return sorted(runs, key=lambda r: r.run_id)

    def list_by_session(self, session_id: str) -> List[ResearchRun]:
        runs = [r for r in self._runs.values() if r.session_id == session_id]
        return sorted(runs, key=lambda r: r.run_id)
