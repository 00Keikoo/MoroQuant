"""Repository layer for dataset manager."""

import sqlite3
import json
from pathlib import Path
from typing import Optional

from ml_service.research.dataset_manager.types import (
    DatasetMetadata,
    TimeBounds,
    DatasetSchema,
    LifecycleState
)


class DatasetRepository:
    """SQLite repository for dataset metadata."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent.parent / "storage" / "database.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self):
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def save(self, metadata: DatasetMetadata) -> None:
        """Save dataset metadata to database."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO dataset_metadata (
                    dataset_id, version, fingerprint, snapshot_id,
                    created_at, start_time, end_time, lifecycle_state,
                    storage_path, is_frozen, schema_json, preprocessing_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.dataset_id,
                metadata.version,
                metadata.fingerprint,
                metadata.snapshot_id,
                metadata.created_at,
                metadata.time_bounds.start_time,
                metadata.time_bounds.end_time,
                metadata.lifecycle_state.value,
                metadata.storage_path,
                1 if metadata.is_frozen else 0,
                json.dumps({
                    'features': metadata.schema.features,
                    'targets': metadata.schema.targets,
                    'data_types': metadata.schema.data_types
                }),
                json.dumps(metadata.preprocessing) if metadata.preprocessing else None
            ))
            conn.commit()
        finally:
            conn.close()

    def find_by_id(self, dataset_id: str) -> Optional[DatasetMetadata]:
        """Find dataset by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM dataset_metadata WHERE dataset_id = ?
            """, (dataset_id,))
            row = cursor.fetchone()
            return self._row_to_metadata(row) if row else None
        finally:
            conn.close()

    def find_by_fingerprint(self, fingerprint: str) -> Optional[DatasetMetadata]:
        """Find dataset by fingerprint."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM dataset_metadata WHERE fingerprint = ?
            """, (fingerprint,))
            row = cursor.fetchone()
            return self._row_to_metadata(row) if row else None
        finally:
            conn.close()

    def update_state(self, dataset_id: str, state: LifecycleState) -> None:
        """Update dataset lifecycle state."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE dataset_metadata
                SET lifecycle_state = ?
                WHERE dataset_id = ?
            """, (state.value, dataset_id))
            conn.commit()
        finally:
            conn.close()

    def freeze(self, dataset_id: str) -> None:
        """Freeze dataset to make it immutable."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE dataset_metadata
                SET is_frozen = 1, lifecycle_state = ?
                WHERE dataset_id = ?
            """, (LifecycleState.FROZEN.value, dataset_id))
            conn.commit()
        finally:
            conn.close()

    def _row_to_metadata(self, row) -> DatasetMetadata:
        """Convert database row to DatasetMetadata."""
        schema_json = json.loads(row['schema_json'])
        preprocessing_json = json.loads(row['preprocessing_json']) if row['preprocessing_json'] else None

        return DatasetMetadata(
            dataset_id=row['dataset_id'],
            version=row['version'],
            fingerprint=row['fingerprint'],
            snapshot_id=row['snapshot_id'],
            created_at=row['created_at'],
            time_bounds=TimeBounds(
                start_time=row['start_time'],
                end_time=row['end_time']
            ),
            schema=DatasetSchema(
                features=schema_json['features'],
                targets=schema_json['targets'],
                data_types=schema_json['data_types']
            ),
            lifecycle_state=LifecycleState(row['lifecycle_state']),
            storage_path=row['storage_path'],
            preprocessing=preprocessing_json,
            is_frozen=bool(row['is_frozen'])
        )
