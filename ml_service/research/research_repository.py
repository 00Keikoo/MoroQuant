import copy
from typing import List

from ml_service.research.models import (
    ResearchSession,
    ResearchExperiment,
    DatasetSnapshot,
    FeatureSnapshot,
)

class ResearchRepository:
    """
    An in-memory repository responsible ONLY for storing and retrieving
    immutable research objects (ResearchSession, ResearchExperiment,
    DatasetSnapshot, FeatureSnapshot).
    
    Adheres strictly to storing data only, with no business logic, no SQLite,
    no filesystem, and deterministic sorting.
    """
    def __init__(self) -> None:
        self._sessions = {}
        self._experiments = {}
        self._dataset_snapshots = {}
        self._feature_snapshots = {}

    def create_session(self, session: ResearchSession) -> ResearchSession:
        if not isinstance(session, ResearchSession):
            raise TypeError("Expected a ResearchSession instance.")
        if session.session_id in self._sessions:
            raise ValueError(f"Session with ID '{session.session_id}' already exists.")
        self._sessions[session.session_id] = copy.deepcopy(session)
        return session

    def get_session(self, session_id: str) -> ResearchSession:
        if session_id not in self._sessions:
            raise KeyError(f"Session with ID '{session_id}' not found.")
        return self._sessions[session_id]

    def list_sessions(self) -> List[ResearchSession]:
        return sorted(self._sessions.values(), key=lambda s: s.session_id)

    def save_experiment(self, experiment: ResearchExperiment) -> ResearchExperiment:
        if not isinstance(experiment, ResearchExperiment):
            raise TypeError("Expected a ResearchExperiment instance.")
        if experiment.experiment_id in self._experiments:
            raise ValueError(f"Experiment with ID '{experiment.experiment_id}' already exists.")
        self._experiments[experiment.experiment_id] = copy.deepcopy(experiment)
        return experiment

    def get_experiment(self, experiment_id: str) -> ResearchExperiment:
        if experiment_id not in self._experiments:
            raise KeyError(f"Experiment with ID '{experiment_id}' not found.")
        return self._experiments[experiment_id]

    def list_experiments(self, session_id: str) -> List[ResearchExperiment]:
        experiments = [e for e in self._experiments.values() if e.session_id == session_id]
        return sorted(experiments, key=lambda e: e.experiment_id)

    def save_dataset_snapshot(self, snapshot: DatasetSnapshot) -> DatasetSnapshot:
        if not isinstance(snapshot, DatasetSnapshot):
            raise TypeError("Expected a DatasetSnapshot instance.")
        if snapshot.dataset_version_id in self._dataset_snapshots:
            raise ValueError(f"Dataset snapshot with ID '{snapshot.dataset_version_id}' already exists.")
        self._dataset_snapshots[snapshot.dataset_version_id] = copy.deepcopy(snapshot)
        return snapshot

    def get_dataset_snapshot(self, dataset_version_id: str) -> DatasetSnapshot:
        if dataset_version_id not in self._dataset_snapshots:
            raise KeyError(f"Dataset snapshot with ID '{dataset_version_id}' not found.")
        return self._dataset_snapshots[dataset_version_id]

    def save_feature_snapshot(self, snapshot: FeatureSnapshot) -> FeatureSnapshot:
        if not isinstance(snapshot, FeatureSnapshot):
            raise TypeError("Expected a FeatureSnapshot instance.")
        if snapshot.feature_dataset_id in self._feature_snapshots:
            raise ValueError(f"Feature snapshot with ID '{snapshot.feature_dataset_id}' already exists.")
        self._feature_snapshots[snapshot.feature_dataset_id] = copy.deepcopy(snapshot)
        return snapshot

    def get_feature_snapshot(self, feature_dataset_id: str) -> FeatureSnapshot:
        if feature_dataset_id not in self._feature_snapshots:
            raise KeyError(f"Feature snapshot with ID '{feature_dataset_id}' not found.")
        return self._feature_snapshots[feature_dataset_id]

    def delete_session(self, session_id: str) -> None:
        if session_id not in self._sessions:
            raise KeyError(f"Session with ID '{session_id}' not found.")
        del self._sessions[session_id]

    def delete_experiment(self, experiment_id: str) -> None:
        if experiment_id not in self._experiments:
            raise KeyError(f"Experiment with ID '{experiment_id}' not found.")
        del self._experiments[experiment_id]
