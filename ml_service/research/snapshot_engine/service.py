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
        self.db_path = db_path

    def create_snapshot(self, symbol: Optional[str] = None) -> Snapshot:
        """Create a new snapshot of current system state.

        Args:
            symbol: Optional symbol filter

        Returns:
            Snapshot object
        """
        return capture_snapshot(symbol=symbol, db_path=self.db_path)

    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """Retrieve snapshot by ID.

        Args:
            snapshot_id: Snapshot identifier

        Returns:
            None (persistence not yet implemented)
        """
        return None
