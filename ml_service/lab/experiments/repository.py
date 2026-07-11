"""Experiment Repository for CRUD operations.

Repository layer with transaction support for future orchestration.
Aligns with MoroQuant database abstraction patterns.
"""

from typing import List, Optional
from sqlite3 import Connection

from ml_service.lab.experiments.types import ExperimentContract
from ml_service.repositories.database import get_connection


class ExperimentRepository:
    """Repository for querying and persisting experiments.

    Supports dependency injection of database connections to enable
    transaction orchestration at higher levels.
    """

    def __init__(self, db_path: str = None, conn: Connection = None):
        """Initialize repository with optional connection injection.

        Args:
            db_path: Path to database file (used if conn not provided)
            conn: Optional injected connection for transaction support
        """
        self.db_path = db_path
        self._injected_conn = conn

    def _get_conn(self) -> Connection:
        """Get connection - injected or create new."""
        if self._injected_conn:
            return self._injected_conn
        return get_connection(self.db_path)

    def _should_close(self) -> bool:
        """Only close connections we created, not injected ones."""
        return self._injected_conn is None

    def _row_to_contract(self, row) -> ExperimentContract:
        """Convert database row to ExperimentContract."""
        return ExperimentContract(
            id=row['id'],
            experiment_id=row['experiment_id'],
            run_id=row['run_id'],
            status=row['status'],
            dataset_version=row['dataset_version'],
            feature_version=row['feature_version'],
            model_version=row['model_version'],
            hyperparameters=row['hyperparameters'],
            train_loss=row['train_loss'],
            validation_loss=row['validation_loss'],
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            notes=row['notes']
        )

    def create(self, experiment: ExperimentContract) -> int:
        """Insert a new experiment.

        Args:
            experiment: ExperimentContract to insert

        Returns:
            ID of the inserted experiment
        """
        query = """
            INSERT INTO experiments (
                experiment_id, run_id, status, dataset_version, feature_version,
                model_version, hyperparameters, train_loss, validation_loss,
                started_at, completed_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        conn = self._get_conn()
        try:
            cursor = conn.execute(query, (
                experiment.experiment_id,
                experiment.run_id,
                experiment.status,
                experiment.dataset_version,
                experiment.feature_version,
                experiment.model_version,
                experiment.hyperparameters,
                experiment.train_loss,
                experiment.validation_loss,
                experiment.started_at,
                experiment.completed_at,
                experiment.notes
            ))
            if not self._injected_conn:
                conn.commit()
            return cursor.lastrowid
        finally:
            if self._should_close():
                conn.close()

    def get_by_id(self, experiment_id: int) -> Optional[ExperimentContract]:
        """Get experiment by ID."""
        query = "SELECT * FROM experiments WHERE id = ?"

        conn = self._get_conn()
        try:
            cursor = conn.execute(query, (experiment_id,))
            row = cursor.fetchone()
            return self._row_to_contract(row) if row else None
        finally:
            if self._should_close():
                conn.close()

    def get_by_run_id(self, run_id: str) -> Optional[ExperimentContract]:
        """Get experiment by run_id."""
        query = "SELECT * FROM experiments WHERE run_id = ?"

        conn = self._get_conn()
        try:
            cursor = conn.execute(query, (run_id,))
            row = cursor.fetchone()
            return self._row_to_contract(row) if row else None
        finally:
            if self._should_close():
                conn.close()

    def get_by_experiment_id(self, experiment_id: str) -> List[ExperimentContract]:
        """Get all runs for a given experiment_id."""
        query = """
            SELECT * FROM experiments
            WHERE experiment_id = ?
            ORDER BY created_at DESC
        """

        conn = self._get_conn()
        try:
            cursor = conn.execute(query, (experiment_id,))
            return [self._row_to_contract(row) for row in cursor.fetchall()]
        finally:
            if self._should_close():
                conn.close()

    def list_all(self, limit: int = 100, offset: int = 0) -> List[ExperimentContract]:
        """List all experiments with pagination."""
        query = """
            SELECT * FROM experiments
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """

        conn = self._get_conn()
        try:
            cursor = conn.execute(query, (limit, offset))
            return [self._row_to_contract(row) for row in cursor.fetchall()]
        finally:
            if self._should_close():
                conn.close()

    def list_by_status(self, status: str) -> List[ExperimentContract]:
        """Get experiments by status."""
        query = """
            SELECT * FROM experiments
            WHERE status = ?
            ORDER BY created_at DESC
        """

        conn = self._get_conn()
        try:
            cursor = conn.execute(query, (status,))
            return [self._row_to_contract(row) for row in cursor.fetchall()]
        finally:
            if self._should_close():
                conn.close()

    def update_status(self, run_id: str, status: str) -> bool:
        """Update experiment status."""
        query = """
            UPDATE experiments
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE run_id = ?
        """

        conn = self._get_conn()
        try:
            cursor = conn.execute(query, (status, run_id))
            if not self._injected_conn:
                conn.commit()
            return cursor.rowcount > 0
        finally:
            if self._should_close():
                conn.close()

    def update_metrics(
        self,
        run_id: str,
        train_loss: Optional[float] = None,
        validation_loss: Optional[float] = None
    ) -> bool:
        """Update experiment training metrics."""
        updates = []
        values = []

        if train_loss is not None:
            updates.append("train_loss = ?")
            values.append(train_loss)
        if validation_loss is not None:
            updates.append("validation_loss = ?")
            values.append(validation_loss)

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(run_id)

        query = f"UPDATE experiments SET {', '.join(updates)} WHERE run_id = ?"

        conn = self._get_conn()
        try:
            cursor = conn.execute(query, values)
            if not self._injected_conn:
                conn.commit()
            return cursor.rowcount > 0
        finally:
            if self._should_close():
                conn.close()

    def delete(self, run_id: str) -> bool:
        """Delete experiment by run_id."""
        query = "DELETE FROM experiments WHERE run_id = ?"

        conn = self._get_conn()
        try:
            cursor = conn.execute(query, (run_id,))
            if not self._injected_conn:
                conn.commit()
            return cursor.rowcount > 0
        finally:
            if self._should_close():
                conn.close()

    def count_all(self) -> int:
        """Count total experiments."""
        query = "SELECT COUNT(*) as count FROM experiments"

        conn = self._get_conn()
        try:
            cursor = conn.execute(query)
            return cursor.fetchone()['count']
        finally:
            if self._should_close():
                conn.close()

    def count_by_status(self, status: str) -> int:
        """Count experiments by status."""
        query = "SELECT COUNT(*) as count FROM experiments WHERE status = ?"

        conn = self._get_conn()
        try:
            cursor = conn.execute(query, (status,))
            return cursor.fetchone()['count']
        finally:
            if self._should_close():
                conn.close()
