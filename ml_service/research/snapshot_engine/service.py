"""Service layer for snapshot engine."""

from typing import Optional

from ml_service.research.snapshot_engine.types import Snapshot
from ml_service.research.snapshot_engine.capture import capture_snapshot


class SnapshotService:
    """Service for managing snapshots."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize snapshot service.

        Args:
            db_path: Optional database path for repositories
        """
        from ml_service.repositories.snapshot_repository import SnapshotRepository

        self.db_path = db_path
        self.repository = SnapshotRepository(db_path=db_path)

    def create_snapshot(self, symbol: Optional[str] = None) -> Snapshot:
        """Create a new snapshot of current system state.

        Args:
            symbol: Optional symbol filter

        Returns:
            Snapshot object
        """
        snapshot = capture_snapshot(symbol=symbol, db_path=self.db_path)
        self.repository.save(snapshot)
        return snapshot

    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """Retrieve snapshot by ID.

        Args:
            snapshot_id: Snapshot identifier

        Returns:
            Snapshot object if found, None otherwise
        """
        return self.repository.get(snapshot_id)
