"""Read-only repository for Research Dashboard."""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any


class ResearchDashboardRepository:
    """Read-only repository accessing experiment, dataset, and feature metadata."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent.parent / "storage" / "database.db"
        self.db_path = Path(db_path)

    def _get_connection(self):
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_experiments(
        self,
        strategy_filter: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all experiments with optional filters."""
        conn = self._get_connection()
        try:
            query = """
                SELECT
                    e.experiment_id,
                    e.snapshot_id,
                    e.created_at,
                    GROUP_CONCAT(DISTINCT ec.config_id) as config_ids
                FROM experiments e
                LEFT JOIN experiment_configs ec ON e.experiment_id = ec.experiment_id
                GROUP BY e.experiment_id, e.snapshot_id, e.created_at
                ORDER BY e.created_at DESC
            """
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment metadata by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT experiment_id, snapshot_id, created_at
                FROM experiments
                WHERE experiment_id = ?
            """, (experiment_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_experiment_configs(self, experiment_id: str) -> List[Dict[str, Any]]:
        """Get all strategy configs for an experiment."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT config_id, threshold_long, threshold_short, regime_filter
                FROM experiment_configs
                WHERE experiment_id = ?
            """, (experiment_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_experiment_results(self, experiment_id: str) -> List[Dict[str, Any]]:
        """Get all results for an experiment."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT config_id, pnl, winrate, sharpe, max_drawdown,
                       consistency_score, trade_count
                FROM experiment_results
                WHERE experiment_id = ?
            """, (experiment_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_dataset_by_dataset_id(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Get dataset metadata by dataset_id."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT dataset_id, version, fingerprint, snapshot_id,
                       created_at, start_time, end_time, lifecycle_state,
                       storage_path, is_frozen
                FROM dataset_metadata
                WHERE dataset_id = ?
            """, (dataset_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_dataset_by_snapshot_id(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Get dataset metadata by snapshot_id."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT dataset_id, version, fingerprint, snapshot_id,
                       created_at, start_time, end_time, lifecycle_state,
                       storage_path, is_frozen
                FROM dataset_metadata
                WHERE snapshot_id = ?
            """, (snapshot_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_feature_datasets_by_source(self, source_dataset_id: str) -> List[Dict[str, Any]]:
        """Get all feature datasets derived from a source dataset."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT feature_dataset_id, source_dataset_id, feature_version_id,
                       fingerprint, storage_path, created_at, lifecycle_state, is_frozen
                FROM feature_datasets
                WHERE source_dataset_id = ?
            """, (source_dataset_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_feature_dataset(self, feature_dataset_id: str) -> Optional[Dict[str, Any]]:
        """Get feature dataset metadata by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT feature_dataset_id, source_dataset_id, feature_version_id,
                       fingerprint, storage_path, created_at, lifecycle_state, is_frozen
                FROM feature_datasets
                WHERE feature_dataset_id = ?
            """, (feature_dataset_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_feature_version(self, feature_version_id: str) -> Optional[Dict[str, Any]]:
        """Get feature version by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT feature_version_id, feature_name, version, parameters_json, created_at
                FROM feature_versions
                WHERE feature_version_id = ?
            """, (feature_version_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
