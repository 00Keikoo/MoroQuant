from typing import List, Optional, Any
from ml_service.research.models import DatasetSnapshot
from ml_service.research.dataset_snapshot import DatasetSnapshotManager
from ml_service.research.dataset_repository import DatasetRepository

class DatasetService:
    """
    Business-level service that orchestrates DatasetSnapshotManager and DatasetRepository.
    Exposes operations for snapshot creation, retrieval, deletion, existence checking,
    and validation, keeping the manager and repository state in sync.
    """
    def __init__(
        self,
        repository: DatasetRepository,
        snapshot_manager: DatasetSnapshotManager
    ) -> None:
        self.repository = repository
        self.snapshot_manager = snapshot_manager

    def create_snapshot(
        self,
        dataset_version_id: str,
        fingerprint: str,
        file_path: str,
        is_frozen: bool = True,
        created_at: Optional[str] = None
    ) -> DatasetSnapshot:
        """
        Creates a new dataset snapshot, validates it, registers it in the manager,
        and persists it to the repository. Rejects duplicates.
        """
        if self.repository.exists(dataset_version_id):
            raise ValueError(f"Dataset snapshot with version ID '{dataset_version_id}' already exists.")

        snapshot = self.snapshot_manager.create_snapshot(
            dataset_version_id=dataset_version_id,
            fingerprint=fingerprint,
            file_path=file_path,
            is_frozen=is_frozen,
            created_at=created_at
        )
        self.repository.save(snapshot)
        return snapshot

    def get_snapshot(self, dataset_version_id: str) -> DatasetSnapshot:
        """Retrieves a dataset snapshot from the repository."""
        return self.repository.get(dataset_version_id)

    def has_snapshot(self, dataset_version_id: str) -> bool:
        """Checks if a dataset snapshot exists in the repository."""
        return self.repository.exists(dataset_version_id)

    def delete_snapshot(self, dataset_version_id: str) -> None:
        """Deletes a dataset snapshot from both the manager and the repository."""
        if dataset_version_id in self.snapshot_manager._snapshots:
            del self.snapshot_manager._snapshots[dataset_version_id]
        self.repository.delete(dataset_version_id)

    def list_snapshots(self) -> List[DatasetSnapshot]:
        """Lists all snapshots in deterministic order (sorted by version ID)."""
        return self.repository.list()

    def verify_hash(self, snapshot: DatasetSnapshot, data: Any) -> bool:
        """Verifies if the data matches the snapshot's fingerprint hash."""
        return self.snapshot_manager.verify_hash(snapshot, data)

    def calculate_canonical_hash(self, data: Any) -> str:
        """Calculates a deterministic canonical SHA-256 hash for raw data structure."""
        return self.snapshot_manager.calculate_canonical_hash(data)

    def serialize(self, snapshot: DatasetSnapshot) -> str:
        """Exposes deterministic JSON serialization for a snapshot."""
        return self.snapshot_manager.serialize(snapshot)
