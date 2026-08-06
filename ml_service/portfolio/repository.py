"""
Portfolio Snapshot Repository

Persistence layer for portfolio snapshots.
In-memory implementation for deterministic research simulations.
"""

from datetime import datetime
from typing import Dict, List, Optional

from ml_service.portfolio.snapshot import PortfolioSnapshot


class PortfolioSnapshotRepository:
    """
    Abstract repository interface for portfolio snapshots.

    Defines contract for snapshot persistence operations.
    """

    def save(self, snapshot: PortfolioSnapshot) -> None:
        """Save a snapshot to storage."""
        raise NotImplementedError

    def get(self, snapshot_id: str) -> Optional[PortfolioSnapshot]:
        """Retrieve a snapshot by ID."""
        raise NotImplementedError

    def get_latest(self, portfolio_id: str) -> Optional[PortfolioSnapshot]:
        """Retrieve the most recent snapshot for a portfolio."""
        raise NotImplementedError

    def get_history(
        self,
        portfolio_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[PortfolioSnapshot]:
        """
        Retrieve all snapshots for a portfolio within a time range.

        Returns snapshots in chronological order (oldest first).
        """
        raise NotImplementedError

    def delete(self, snapshot_id: str) -> bool:
        """
        Delete a snapshot by ID.

        Returns True if deleted, False if not found.
        """
        raise NotImplementedError

    def clear(self) -> None:
        """Clear all snapshots (for testing)."""
        raise NotImplementedError


class InMemorySnapshotRepository(PortfolioSnapshotRepository):
    """
    In-memory implementation of snapshot repository.

    Suitable for:
    - Simulation and backtesting
    - Research experiments
    - Testing
    - Single-process deterministic replay

    Not suitable for:
    - Multi-process applications
    - Long-term persistence
    - Production trading systems
    """

    def __init__(self):
        self._snapshots: Dict[str, PortfolioSnapshot] = {}
        self._portfolio_index: Dict[str, List[str]] = {}

    def save(self, snapshot: PortfolioSnapshot) -> None:
        """Save snapshot to in-memory storage."""
        if snapshot.snapshot_id in self._snapshots:
            raise ValueError(f"Snapshot {snapshot.snapshot_id} already exists")

        self._snapshots[snapshot.snapshot_id] = snapshot

        if snapshot.portfolio_id not in self._portfolio_index:
            self._portfolio_index[snapshot.portfolio_id] = []

        self._portfolio_index[snapshot.portfolio_id].append(snapshot.snapshot_id)
        self._portfolio_index[snapshot.portfolio_id].sort(
            key=lambda sid: self._snapshots[sid].timestamp
        )

    def get(self, snapshot_id: str) -> Optional[PortfolioSnapshot]:
        """Retrieve snapshot by ID."""
        return self._snapshots.get(snapshot_id)

    def get_latest(self, portfolio_id: str) -> Optional[PortfolioSnapshot]:
        """Retrieve most recent snapshot for portfolio."""
        snapshot_ids = self._portfolio_index.get(portfolio_id, [])
        if not snapshot_ids:
            return None

        latest_id = snapshot_ids[-1]
        return self._snapshots[latest_id]

    def get_history(
        self,
        portfolio_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[PortfolioSnapshot]:
        """
        Retrieve snapshots within time range in chronological order.
        """
        snapshot_ids = self._portfolio_index.get(portfolio_id, [])

        snapshots = [
            self._snapshots[sid]
            for sid in snapshot_ids
            if start_time <= self._snapshots[sid].timestamp <= end_time
        ]

        return snapshots

    def delete(self, snapshot_id: str) -> bool:
        """Delete snapshot by ID."""
        if snapshot_id not in self._snapshots:
            return False

        snapshot = self._snapshots[snapshot_id]
        del self._snapshots[snapshot_id]

        if snapshot.portfolio_id in self._portfolio_index:
            self._portfolio_index[snapshot.portfolio_id].remove(snapshot_id)
            if not self._portfolio_index[snapshot.portfolio_id]:
                del self._portfolio_index[snapshot.portfolio_id]

        return True

    def clear(self) -> None:
        """Clear all snapshots."""
        self._snapshots.clear()
        self._portfolio_index.clear()

    def count(self) -> int:
        """Return total number of snapshots."""
        return len(self._snapshots)

    def count_for_portfolio(self, portfolio_id: str) -> int:
        """Return number of snapshots for a specific portfolio."""
        return len(self._portfolio_index.get(portfolio_id, []))
