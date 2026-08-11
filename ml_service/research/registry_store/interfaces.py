"""
Registry Store Interfaces
Sprint 3.9D-6

Abstract persistence interface for registry snapshots.
"""

from abc import ABC, abstractmethod
from ml_service.research.registry_snapshot import RegistrySnapshot
from .models import RegistrySnapshotRecord


class RegistrySnapshotStore(ABC):
    @abstractmethod
    def save(self, snapshot: RegistrySnapshot) -> str:
        """Save snapshot and return snapshot_id."""
        pass

    @abstractmethod
    def load(self, snapshot_id: str) -> RegistrySnapshot:
        """Load snapshot by ID."""
        pass

    @abstractmethod
    def list_snapshots(self) -> tuple[RegistrySnapshotRecord, ...]:
        """List all saved snapshots, sorted by created_at."""
        pass

    @abstractmethod
    def get_latest(self) -> RegistrySnapshot | None:
        """Get most recent snapshot, or None if empty."""
        pass
