"""Service layer for replay engine."""

from typing import Optional

from ml_service.research.snapshot_engine import SnapshotService
from ml_service.research.snapshot_engine.types import Snapshot
from ml_service.research.replay_engine.types import ReplayResult
from ml_service.research.replay_engine.replay import run_replay


class ReplayService:
    """Service for managing replay operations."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize replay service.

        Args:
            db_path: Optional database path for snapshot service
        """
        self.snapshot_service = SnapshotService(db_path=db_path)

    def run(self, snapshot: Snapshot, threshold_long: float = 0.5, threshold_short: float = 0.5) -> ReplayResult:
        """Run replay on a snapshot using Decision Truth Layer.

        Args:
            snapshot: Snapshot object to replay
            threshold_long: Threshold for LONG decisions (default 0.5)
            threshold_short: Threshold for SHORT decisions (default 0.5)

        Returns:
            ReplayResult with decision reconstruction
        """
        return run_replay(snapshot, threshold_long=threshold_long, threshold_short=threshold_short)

    def run_from_snapshot_id(self, snapshot_id: str, threshold_long: float = 0.5, threshold_short: float = 0.5) -> Optional[ReplayResult]:
        """Run replay from snapshot ID using Decision Truth Layer.

        Args:
            snapshot_id: Snapshot identifier
            threshold_long: Threshold for LONG decisions (default 0.5)
            threshold_short: Threshold for SHORT decisions (default 0.5)

        Returns:
            ReplayResult if snapshot exists, None otherwise
        """
        snapshot = self.snapshot_service.get_snapshot(snapshot_id)
        if snapshot is None:
            return None
        return run_replay(snapshot, threshold_long=threshold_long, threshold_short=threshold_short)

    def get_replay(self, snapshot_id: str) -> Optional[ReplayResult]:
        """Retrieve replay result by snapshot ID.

        Args:
            snapshot_id: Snapshot identifier

        Returns:
            None (persistence not yet implemented)
        """
        return None
