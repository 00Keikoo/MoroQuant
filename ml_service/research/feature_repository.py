import copy
from typing import List

from ml_service.research.models import FeatureSnapshot


class FeatureRepository:
    """
    An in-memory repository responsible ONLY for storing and retrieving
    immutable FeatureSnapshot instances.
    
    Adheres strictly to storing data only, with no business logic, no SQL,
    no filesystem, no logging, no network, and deterministic sorting.
    """
    def __init__(self) -> None:
        self._snapshots = {}

    def save(self, snapshot: FeatureSnapshot) -> FeatureSnapshot:
        if not isinstance(snapshot, FeatureSnapshot):
            raise TypeError("Expected a FeatureSnapshot instance.")
        if snapshot.feature_dataset_id in self._snapshots:
            raise ValueError(f"Feature snapshot with ID '{snapshot.feature_dataset_id}' already exists.")
        self._snapshots[snapshot.feature_dataset_id] = copy.deepcopy(snapshot)
        return snapshot

    def get(self, feature_dataset_id: str) -> FeatureSnapshot:
        if feature_dataset_id not in self._snapshots:
            raise KeyError(f"Feature snapshot with ID '{feature_dataset_id}' not found.")
        return self._snapshots[feature_dataset_id]

    def exists(self, feature_dataset_id: str) -> bool:
        return feature_dataset_id in self._snapshots

    def delete(self, feature_dataset_id: str) -> None:
        if feature_dataset_id not in self._snapshots:
            raise KeyError(f"Feature snapshot with ID '{feature_dataset_id}' not found.")
        del self._snapshots[feature_dataset_id]

    def list(self) -> List[FeatureSnapshot]:
        return sorted(self._snapshots.values(), key=lambda s: s.feature_dataset_id)
