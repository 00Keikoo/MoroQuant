"""Repository for querying paper account and equity history."""

from typing import List, Optional
from dataclasses import dataclass

from ml_service.repositories.database import get_connection


@dataclass
class PaperAccount:
    """Represents the paper trading account."""
    id: int
    balance: float
    equity: float
    unrealized_pnl: float
    updated_at: str


@dataclass
class EquitySnapshot:
    """Represents an equity history snapshot."""
    id: int
    equity: float
    balance: float
    unrealized_pnl: float
    snapshot_time: str


class EquityRepository:
    """Repository for querying paper_account and paper_equity_history tables."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path

    def _row_to_account(self, row) -> PaperAccount:
        """Convert database row to PaperAccount."""
        return PaperAccount(
            id=row['id'],
            balance=row['balance'],
            equity=row['equity'],
            unrealized_pnl=row['unrealized_pnl'],
            updated_at=row['updated_at']
        )

    def _row_to_snapshot(self, row) -> EquitySnapshot:
        """Convert database row to EquitySnapshot."""
        return EquitySnapshot(
            id=row['id'],
            equity=row['equity'],
            balance=row['balance'],
            unrealized_pnl=row['unrealized_pnl'],
            snapshot_time=row['snapshot_time']
        )

    def get_account(self) -> Optional[PaperAccount]:
        """Get the paper account singleton (id=1).

        Returns:
            PaperAccount if exists, None otherwise
        """
        query = """
            SELECT
                id, balance, equity, unrealized_pnl, updated_at
            FROM paper_account
            WHERE id = 1
        """

        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(query)
            row = cursor.fetchone()
            return self._row_to_account(row) if row else None
        finally:
            conn.close()

    def get_equity_history(
        self,
        limit: int = 1000,
        offset: int = 0
    ) -> List[EquitySnapshot]:
        """Get equity history snapshots.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of EquitySnapshot objects ordered by snapshot_time descending
        """
        query = """
            SELECT
                id, equity, balance, unrealized_pnl, snapshot_time
            FROM paper_equity_history
            ORDER BY snapshot_time DESC
            LIMIT ? OFFSET ?
        """

        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(query, (limit, offset))
            return [self._row_to_snapshot(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_equity_history_range(
        self,
        start_time: str,
        end_time: str
    ) -> List[EquitySnapshot]:
        """Get equity history within a time range.

        Args:
            start_time: Start timestamp (ISO format or timestamp)
            end_time: End timestamp (ISO format or timestamp)

        Returns:
            List of EquitySnapshot objects ordered by snapshot_time ascending
        """
        query = """
            SELECT
                id, equity, balance, unrealized_pnl, snapshot_time
            FROM paper_equity_history
            WHERE snapshot_time >= ? AND snapshot_time <= ?
            ORDER BY snapshot_time ASC
        """

        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(query, (start_time, end_time))
            return [self._row_to_snapshot(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_latest_snapshot(self) -> Optional[EquitySnapshot]:
        """Get the most recent equity snapshot.

        Returns:
            EquitySnapshot if exists, None otherwise
        """
        query = """
            SELECT
                id, equity, balance, unrealized_pnl, snapshot_time
            FROM paper_equity_history
            ORDER BY snapshot_time DESC
            LIMIT 1
        """

        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(query)
            row = cursor.fetchone()
            return self._row_to_snapshot(row) if row else None
        finally:
            conn.close()

    def count_snapshots(self) -> int:
        """Count total equity snapshots.

        Returns:
            Count of snapshots
        """
        query = "SELECT COUNT(*) as count FROM paper_equity_history"

        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(query)
            return cursor.fetchone()['count']
        finally:
            conn.close()
