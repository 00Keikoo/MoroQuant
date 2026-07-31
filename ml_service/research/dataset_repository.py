import copy
from typing import List

from ml_service.research.models import DatasetSnapshot


class DatasetRepository:
    """
    An in-memory repository responsible ONLY for storing and retrieving
    immutable DatasetSnapshot instances.
    
    Adheres strictly to storing data only, with no business logic, no SQL,
    no filesystem, no logging, no network, and deterministic sorting.
    """
    def __init__(self) -> None:
        self._snapshots = {}

    def save(self, snapshot: DatasetSnapshot) -> DatasetSnapshot:
        if not isinstance(snapshot, DatasetSnapshot):
            raise TypeError("Expected a DatasetSnapshot instance.")
        if snapshot.dataset_version_id in self._snapshots:
            raise ValueError(f"Dataset snapshot with ID '{snapshot.dataset_version_id}' already exists.")
        self._snapshots[snapshot.dataset_version_id] = copy.deepcopy(snapshot)
        return snapshot

    def get(self, dataset_version_id: str) -> DatasetSnapshot:
        if dataset_version_id not in self._snapshots:
            raise KeyError(f"Dataset snapshot with ID '{dataset_version_id}' not found.")
        return self._snapshots[dataset_version_id]

    def exists(self, dataset_version_id: str) -> bool:
        return dataset_version_id in self._snapshots

    def delete(self, dataset_version_id: str) -> None:
        if dataset_version_id not in self._snapshots:
            raise KeyError(f"Dataset snapshot with ID '{dataset_version_id}' not found.")
        del self._snapshots[dataset_version_id]

    def list(self) -> List[DatasetSnapshot]:
        return sorted(self._snapshots.values(), key=lambda s: s.dataset_version_id)
