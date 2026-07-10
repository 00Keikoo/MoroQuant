"""Repository layer for feature store."""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

from ml_service.research.feature_store.feature_types import (
    FeatureDefinition,
    FeatureVersion,
    FeatureDatasetMetadata,
    FeatureLifecycleState
)


class FeatureRepository:
    """SQLite repository for feature metadata."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent.parent / "storage" / "database.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_connection(self):
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        """Create feature store tables if they don't exist."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feature_definitions (
                    feature_name TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    formula_ref TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feature_versions (
                    feature_version_id TEXT PRIMARY KEY,
                    feature_name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    parameters_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (feature_name) REFERENCES feature_definitions(feature_name)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feature_datasets (
                    feature_dataset_id TEXT PRIMARY KEY,
                    source_dataset_id TEXT NOT NULL,
                    feature_version_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL UNIQUE,
                    storage_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    lifecycle_state TEXT NOT NULL,
                    is_frozen INTEGER DEFAULT 0,
                    FOREIGN KEY (feature_version_id) REFERENCES feature_versions(feature_version_id)
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feature_dataset_source
                ON feature_datasets(source_dataset_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feature_dataset_version
                ON feature_datasets(feature_version_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feature_dataset_fingerprint
                ON feature_datasets(fingerprint)
            """)

            conn.commit()
        finally:
            conn.close()

    def save_definition(self, definition: FeatureDefinition) -> None:
        """Save feature definition."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO feature_definitions (
                    feature_name, description, formula_ref, created_at
                ) VALUES (?, ?, ?, ?)
            """, (
                definition.feature_name,
                definition.description,
                definition.formula_ref,
                definition.created_at
            ))
            conn.commit()
        finally:
            conn.close()

    def find_definition(self, feature_name: str) -> Optional[FeatureDefinition]:
        """Find feature definition by name."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM feature_definitions WHERE feature_name = ?
            """, (feature_name,))
            row = cursor.fetchone()
            return self._row_to_definition(row) if row else None
        finally:
            conn.close()

    def save_version(self, version: FeatureVersion) -> None:
        """Save feature version."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO feature_versions (
                    feature_version_id, feature_name, version,
                    parameters_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                version.feature_version_id,
                version.feature_name,
                version.version,
                json.dumps(version.parameters),
                version.created_at
            ))
            conn.commit()
        finally:
            conn.close()

    def find_version(self, feature_version_id: str) -> Optional[FeatureVersion]:
        """Find feature version by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM feature_versions WHERE feature_version_id = ?
            """, (feature_version_id,))
            row = cursor.fetchone()
            return self._row_to_version(row) if row else None
        finally:
            conn.close()

    def save_dataset(self, metadata: FeatureDatasetMetadata) -> None:
        """Save feature dataset metadata."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO feature_datasets (
                    feature_dataset_id, source_dataset_id, feature_version_id,
                    fingerprint, storage_path, created_at, lifecycle_state, is_frozen
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.feature_dataset_id,
                metadata.source_dataset_id,
                metadata.feature_version_id,
                metadata.fingerprint,
                metadata.storage_path,
                metadata.created_at,
                metadata.lifecycle_state.value,
                1 if metadata.is_frozen else 0
            ))
            conn.commit()
        finally:
            conn.close()

    def find_dataset_by_id(self, feature_dataset_id: str) -> Optional[FeatureDatasetMetadata]:
        """Find feature dataset by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM feature_datasets WHERE feature_dataset_id = ?
            """, (feature_dataset_id,))
            row = cursor.fetchone()
            return self._row_to_dataset(row) if row else None
        finally:
            conn.close()

    def find_dataset_by_fingerprint(self, fingerprint: str) -> Optional[FeatureDatasetMetadata]:
        """Find feature dataset by fingerprint."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM feature_datasets WHERE fingerprint = ?
            """, (fingerprint,))
            row = cursor.fetchone()
            return self._row_to_dataset(row) if row else None
        finally:
            conn.close()

    def find_datasets_by_source(self, source_dataset_id: str) -> List[FeatureDatasetMetadata]:
        """Find all feature datasets derived from a source dataset."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM feature_datasets WHERE source_dataset_id = ?
            """, (source_dataset_id,))
            rows = cursor.fetchall()
            return [self._row_to_dataset(row) for row in rows]
        finally:
            conn.close()

    def update_state(self, feature_dataset_id: str, state: FeatureLifecycleState) -> None:
        """Update feature dataset lifecycle state."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE feature_datasets
                SET lifecycle_state = ?
                WHERE feature_dataset_id = ?
            """, (state.value, feature_dataset_id))
            conn.commit()
        finally:
            conn.close()

    def freeze(self, feature_dataset_id: str) -> None:
        """Freeze feature dataset to make it immutable."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE feature_datasets
                SET is_frozen = 1, lifecycle_state = ?
                WHERE feature_dataset_id = ?
            """, (FeatureLifecycleState.FROZEN.value, feature_dataset_id))
            conn.commit()
        finally:
            conn.close()

    def _row_to_definition(self, row) -> FeatureDefinition:
        """Convert database row to FeatureDefinition."""
        return FeatureDefinition(
            feature_name=row['feature_name'],
            description=row['description'],
            formula_ref=row['formula_ref'],
            created_at=row['created_at']
        )

    def _row_to_version(self, row) -> FeatureVersion:
        """Convert database row to FeatureVersion."""
        return FeatureVersion(
            feature_version_id=row['feature_version_id'],
            feature_name=row['feature_name'],
            version=row['version'],
            parameters=json.loads(row['parameters_json']),
            created_at=row['created_at']
        )

    def _row_to_dataset(self, row) -> FeatureDatasetMetadata:
        """Convert database row to FeatureDatasetMetadata."""
        return FeatureDatasetMetadata(
            feature_dataset_id=row['feature_dataset_id'],
            source_dataset_id=row['source_dataset_id'],
            feature_version_id=row['feature_version_id'],
            fingerprint=row['fingerprint'],
            created_at=row['created_at'],
            lifecycle_state=FeatureLifecycleState(row['lifecycle_state']),
            storage_path=row['storage_path'],
            is_frozen=bool(row['is_frozen'])
        )
