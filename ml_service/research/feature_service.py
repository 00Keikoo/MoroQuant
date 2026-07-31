from typing import List, Optional, Any
from ml_service.research.models import FeatureSnapshot
from ml_service.research.feature_snapshot import FeatureSnapshotManager
from ml_service.research.feature_repository import FeatureRepository

class FeatureService:
    """
    Business-level service that orchestrates FeatureSnapshotManager and FeatureRepository.
    Exposes operations for snapshot creation, retrieval, deletion, existence checking,
    and validation, keeping the manager and repository state in sync.
    """
    def __init__(
        self,
        repository: FeatureRepository,
        snapshot_manager: FeatureSnapshotManager
    ) -> None:
        self.repository = repository
        self.snapshot_manager = snapshot_manager

    def create_snapshot(
        self,
        feature_dataset_id: str,
        source_dataset_id: str,
        fingerprint: str,
        file_path: str,
        is_frozen: bool = True,
        created_at: Optional[str] = None
    ) -> FeatureSnapshot:
        """
        Creates a new feature snapshot, validates it, registers it in the manager,
        and persists it to the repository. Rejects duplicates.
        """
        if self.repository.exists(feature_dataset_id):
            raise ValueError(f"Feature snapshot with ID '{feature_dataset_id}' already exists.")

        snapshot = self.snapshot_manager.create_snapshot(
            feature_dataset_id=feature_dataset_id,
            source_dataset_id=source_dataset_id,
            fingerprint=fingerprint,
            file_path=file_path,
            is_frozen=is_frozen,
            created_at=created_at
        )
        self.repository.save(snapshot)
        return snapshot

    def get_snapshot(self, feature_dataset_id: str) -> FeatureSnapshot:
        """Retrieves a feature snapshot from the repository."""
        return self.repository.get(feature_dataset_id)

    def has_snapshot(self, feature_dataset_id: str) -> bool:
        """Checks if a feature snapshot exists in the repository."""
        return self.repository.exists(feature_dataset_id)

    def delete_snapshot(self, feature_dataset_id: str) -> None:
        """Deletes a feature snapshot from both the manager and the repository."""
        if feature_dataset_id in self.snapshot_manager._snapshots:
            del self.snapshot_manager._snapshots[feature_dataset_id]
        self.repository.delete(feature_dataset_id)

    def list_snapshots(self) -> List[FeatureSnapshot]:
        """Lists all snapshots in deterministic order (sorted by version ID)."""
        return self.repository.list()

    def verify_hash(self, snapshot: FeatureSnapshot, data: Any) -> bool:
        """Verifies if the data matches the snapshot's fingerprint hash."""
        return self.snapshot_manager.verify_hash(snapshot, data)

    def canonical_json(self, data: Any) -> str:
        """Computes deterministic canonical JSON string representation of data."""
        return self.snapshot_manager.canonical_json(data)
