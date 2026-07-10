"""Repository layer for model registry."""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

from ml_service.research.model_registry.model_types import (
    ModelVersionMetadata,
    ModelLineage,
    ModelEvaluation,
    ModelLifecycleState
)


class ModelRegistryRepository:
    """SQLite repository for model metadata and lineage."""

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

    def save_model(self, model_id: str, name: str, description: str, created_at: str) -> None:
        """Save base model identifier."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO models (model_id, name, description, created_at)
                VALUES (?, ?, ?, ?)
            """, (model_id, name, description, created_at))
            conn.commit()
        finally:
            conn.close()

    def model_exists(self, model_id: str) -> bool:
        """Check if model exists."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM models WHERE model_id = ?", (model_id,))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def save_version(self, metadata: ModelVersionMetadata) -> None:
        """Save model version metadata."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO model_versions (
                    model_version_id, model_id, version, lifecycle_state,
                    fingerprint, storage_path, hyperparameters_json,
                    symbol, timeframe, algorithm,
                    created_at, promoted_at, promoted_by,
                    git_commit, git_tag, is_frozen
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.model_version_id,
                metadata.model_id,
                metadata.version,
                metadata.lifecycle_state.value,
                metadata.fingerprint,
                metadata.storage_path,
                json.dumps(metadata.hyperparameters),
                metadata.symbol,
                metadata.timeframe,
                metadata.algorithm,
                metadata.created_at,
                metadata.promoted_at,
                metadata.promoted_by,
                metadata.git_commit,
                metadata.git_tag,
                1 if metadata.is_frozen else 0
            ))
            conn.commit()
        finally:
            conn.close()

    def save_lineage(self, model_version_id: str, lineage: ModelLineage) -> None:
        """Save model lineage."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO model_lineage (
                    model_version_id, snapshot_id, dataset_id,
                    feature_dataset_id, experiment_id, best_config_id
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                model_version_id,
                lineage.snapshot_id,
                lineage.dataset_id,
                lineage.feature_dataset_id,
                lineage.experiment_id,
                lineage.best_config_id
            ))
            conn.commit()
        finally:
            conn.close()

    def save_evaluation(self, model_version_id: str, evaluation: ModelEvaluation) -> None:
        """Save model evaluation metrics."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO model_evaluations (
                    model_version_id, sharpe_ratio, max_drawdown, ece,
                    brier_score, win_rate, profit_factor, sortino_ratio,
                    trade_count, is_approved, approved_by, approved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                model_version_id,
                evaluation.sharpe_ratio,
                evaluation.max_drawdown,
                evaluation.ece,
                evaluation.brier_score,
                evaluation.win_rate,
                evaluation.profit_factor,
                evaluation.sortino_ratio,
                evaluation.trade_count,
                1 if evaluation.is_approved else 0,
                evaluation.approved_by,
                evaluation.approved_at
            ))
            conn.commit()
        finally:
            conn.close()

    def get_version(self, model_version_id: str) -> Optional[ModelVersionMetadata]:
        """Retrieve model version with lineage and evaluation."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT mv.*, ml.snapshot_id, ml.dataset_id, ml.feature_dataset_id,
                       ml.experiment_id, ml.best_config_id,
                       me.sharpe_ratio, me.max_drawdown, me.ece, me.brier_score,
                       me.win_rate, me.profit_factor, me.sortino_ratio, me.trade_count,
                       me.is_approved, me.approved_by, me.approved_at
                FROM model_versions mv
                LEFT JOIN model_lineage ml ON mv.model_version_id = ml.model_version_id
                LEFT JOIN model_evaluations me ON mv.model_version_id = me.model_version_id
                WHERE mv.model_version_id = ?
            """, (model_version_id,))

            row = cursor.fetchone()
            if not row:
                return None

            lineage = ModelLineage(
                snapshot_id=row['snapshot_id'],
                dataset_id=row['dataset_id'],
                feature_dataset_id=row['feature_dataset_id'],
                experiment_id=row['experiment_id'],
                best_config_id=row['best_config_id']
            ) if row['snapshot_id'] else None

            evaluation = ModelEvaluation(
                sharpe_ratio=row['sharpe_ratio'],
                max_drawdown=row['max_drawdown'],
                ece=row['ece'],
                brier_score=row['brier_score'],
                win_rate=row['win_rate'],
                profit_factor=row['profit_factor'],
                sortino_ratio=row['sortino_ratio'],
                trade_count=row['trade_count'],
                is_approved=bool(row['is_approved']),
                approved_by=row['approved_by'],
                approved_at=row['approved_at']
            ) if row['sharpe_ratio'] is not None else None

            return ModelVersionMetadata(
                model_version_id=row['model_version_id'],
                model_id=row['model_id'],
                version=row['version'],
                lifecycle_state=ModelLifecycleState(row['lifecycle_state']),
                fingerprint=row['fingerprint'],
                storage_path=row['storage_path'],
                hyperparameters=json.loads(row['hyperparameters_json']),
                lineage=lineage,
                created_at=row['created_at'],
                symbol=row['symbol'],
                timeframe=row['timeframe'],
                algorithm=row['algorithm'],
                evaluation=evaluation,
                is_frozen=bool(row['is_frozen']),
                promoted_at=row['promoted_at'],
                promoted_by=row['promoted_by'],
                git_commit=row['git_commit'],
                git_tag=row['git_tag']
            )
        finally:
            conn.close()

    def update_lifecycle_state(
        self,
        model_version_id: str,
        new_state: ModelLifecycleState,
        promoted_by: Optional[str] = None,
        promoted_at: Optional[str] = None
    ) -> None:
        """Update model lifecycle state."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE model_versions
                SET lifecycle_state = ?, promoted_at = ?, promoted_by = ?
                WHERE model_version_id = ?
            """, (new_state.value, promoted_at, promoted_by, model_version_id))
            conn.commit()
        finally:
            conn.close()

    def set_frozen(self, model_version_id: str, is_frozen: bool) -> None:
        """Set frozen state of model."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE model_versions
                SET is_frozen = ?
                WHERE model_version_id = ?
            """, (1 if is_frozen else 0, model_version_id))
            conn.commit()
        finally:
            conn.close()

    def get_production_model(
        self,
        symbol: str,
        timeframe: str,
        algorithm: str
    ) -> Optional[ModelVersionMetadata]:
        """Get current production model for symbol/timeframe/algorithm."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT model_version_id FROM model_versions
                WHERE symbol = ? AND timeframe = ? AND algorithm = ?
                  AND lifecycle_state = ?
            """, (symbol, timeframe, algorithm, ModelLifecycleState.PRODUCTION.value))

            row = cursor.fetchone()
            if not row:
                return None

            return self.get_version(row['model_version_id'])
        finally:
            conn.close()

    def list_versions_by_model(self, model_id: str) -> List[ModelVersionMetadata]:
        """List all versions for a model."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT model_version_id FROM model_versions
                WHERE model_id = ?
                ORDER BY created_at DESC
            """, (model_id,))

            return [self.get_version(row['model_version_id']) for row in cursor.fetchall()]
        finally:
            conn.close()

    def list_by_state(self, state: ModelLifecycleState) -> List[ModelVersionMetadata]:
        """List all models in a specific lifecycle state."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT model_version_id FROM model_versions
                WHERE lifecycle_state = ?
                ORDER BY created_at DESC
            """, (state.value,))

            return [self.get_version(row['model_version_id']) for row in cursor.fetchall()]
        finally:
            conn.close()

    def fingerprint_exists(self, fingerprint: str) -> bool:
        """Check if fingerprint already exists."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM model_versions WHERE fingerprint = ?
            """, (fingerprint,))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def get_lineage_chain(self, model_version_id: str) -> Dict[str, Any]:
        """Get complete lineage chain for a model version."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ml.*, mv.model_id, mv.version, mv.symbol, mv.timeframe, mv.algorithm
                FROM model_lineage ml
                JOIN model_versions mv ON ml.model_version_id = mv.model_version_id
                WHERE ml.model_version_id = ?
            """, (model_version_id,))

            row = cursor.fetchone()
            if not row:
                return {}

            return {
                'model_version_id': row['model_version_id'],
                'model_id': row['model_id'],
                'version': row['version'],
                'symbol': row['symbol'],
                'timeframe': row['timeframe'],
                'algorithm': row['algorithm'],
                'snapshot_id': row['snapshot_id'],
                'dataset_id': row['dataset_id'],
                'feature_dataset_id': row['feature_dataset_id'],
                'experiment_id': row['experiment_id'],
                'best_config_id': row['best_config_id']
            }
        finally:
            conn.close()

    def find_models_by_dataset(self, dataset_id: str) -> List[str]:
        """Find all model versions using a specific dataset."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT model_version_id FROM model_lineage
                WHERE dataset_id = ?
            """, (dataset_id,))
            return [row['model_version_id'] for row in cursor.fetchall()]
        finally:
            conn.close()

    def find_models_by_feature_dataset(self, feature_dataset_id: str) -> List[str]:
        """Find all model versions using a specific feature dataset."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT model_version_id FROM model_lineage
                WHERE feature_dataset_id = ?
            """, (feature_dataset_id,))
            return [row['model_version_id'] for row in cursor.fetchall()]
        finally:
            conn.close()

    def find_models_by_experiment(self, experiment_id: str) -> List[str]:
        """Find all model versions from a specific experiment."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT model_version_id FROM model_lineage
                WHERE experiment_id = ?
            """, (experiment_id,))
            return [row['model_version_id'] for row in cursor.fetchall()]
        finally:
            conn.close()
