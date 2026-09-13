"""Repository for snapshot persistence."""

import json
import sqlite3
from datetime import datetime
from typing import Optional

from ml_service.repositories.database import get_connection
from ml_service.research.snapshot_engine.types import Snapshot


class SnapshotRepository:
    """Repository for persisting and retrieving research snapshots."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize snapshot repository.

        Args:
            db_path: Optional database path for testing
        """
        self.db_path = db_path

    def save(self, snapshot: Snapshot) -> Snapshot:
        """Persist snapshot to database (idempotent).

        Args:
            snapshot: Snapshot object to persist

        Returns:
            The same snapshot object
        """
        conn = get_connection(self.db_path)
        try:
            snapshot_data = json.dumps(snapshot.to_dict(), sort_keys=True)
            created_at = datetime.utcnow().isoformat()

            conn.execute("""
                INSERT INTO snapshots (snapshot_id, timestamp, snapshot_data, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(snapshot_id) DO NOTHING
            """, (snapshot.snapshot_id, snapshot.timestamp, snapshot_data, created_at))

            conn.commit()
            return snapshot
        finally:
            conn.close()

    def get(self, snapshot_id: str) -> Optional[Snapshot]:
        """Retrieve snapshot by ID.

        Args:
            snapshot_id: Snapshot identifier

        Returns:
            Snapshot object if found, None otherwise
        """
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT snapshot_data FROM snapshots WHERE snapshot_id = ?",
                (snapshot_id,)
            )
            row = cursor.fetchone()

            if row is None:
                return None

            data = json.loads(row['snapshot_data'])
            return Snapshot(
                snapshot_id=data['snapshot_id'],
                timestamp=data['timestamp'],
                trades=data['trades'],
                signals=data['signals'],
                account_state=data.get('account_state'),
                market_state=data.get('market_state'),
                model_state=data.get('model_state'),
                signal_state=data.get('signal_state'),
                feature_state=data.get('feature_state'),
                regime_state=data.get('regime_state'),
                risk_state=data.get('risk_state'),
                execution_state=data.get('execution_state'),
                position_state=data.get('position_state'),
                execution_constraints=data.get('execution_constraints'),
                regime_statistics=data.get('regime_statistics')
            )
        finally:
            conn.close()
