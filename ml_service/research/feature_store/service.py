"""Service layer for feature store."""

import hashlib
import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, Callable
import pandas as pd

from ml_service.research.feature_store.feature_types import (
    FeatureDefinition,
    FeatureVersion,
    FeatureDatasetMetadata,
    FeatureLifecycleState,
    ValidationResult
)
from ml_service.research.feature_store.repository import FeatureRepository
from ml_service.research.feature_store.validator import FeatureValidator
from ml_service.research.dataset_manager.types import DatasetMetadata


class FeatureService:
    """Service for computing and managing versioned features."""

    def __init__(self, db_path: Optional[str] = None, storage_dir: Optional[str] = None):
        """Initialize feature service.

        Args:
            db_path: Optional database path
            storage_dir: Optional storage directory for feature payloads
        """
        self.repository = FeatureRepository(db_path)
        self.validator = FeatureValidator()

        if storage_dir is None:
            storage_dir = Path(__file__).parent.parent.parent.parent / "storage" / "features"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def register_definition(
        self,
        feature_name: str,
        description: str,
        formula_ref: str
    ) -> FeatureDefinition:
        """Register a feature definition.

        Args:
            feature_name: Unique feature name (e.g., 'rsi_14')
            description: Human-readable description
            formula_ref: Formula reference or code pointer

        Returns:
            FeatureDefinition metadata
        """
        existing = self.repository.find_definition(feature_name)
        if existing:
            raise ValueError(f"Feature definition already exists: {feature_name}")

        definition = FeatureDefinition(
            feature_name=feature_name,
            description=description,
            formula_ref=formula_ref,
            created_at=datetime.utcnow().isoformat()
        )

        self.repository.save_definition(definition)
        return definition

    def register_version(
        self,
        feature_name: str,
        version: str,
        parameters: Dict[str, Any]
    ) -> FeatureVersion:
        """Register a feature version with specific parameters.

        Args:
            feature_name: Feature name (must exist in definitions)
            version: Semantic version (e.g., '1.0.0')
            parameters: Feature parameters dict

        Returns:
            FeatureVersion metadata
        """
        definition = self.repository.find_definition(feature_name)
        if not definition:
            raise ValueError(f"Feature definition not found: {feature_name}")

        feature_version_id = f"{feature_name}_v{version}"

        existing = self.repository.find_version(feature_version_id)
        if existing:
            raise ValueError(f"Feature version already exists: {feature_version_id}")

        feature_version = FeatureVersion(
            feature_version_id=feature_version_id,
            feature_name=feature_name,
            version=version,
            parameters=parameters,
            created_at=datetime.utcnow().isoformat()
        )

        self.repository.save_version(feature_version)
        return feature_version

    def compute_feature_dataset(
        self,
        source_dataset_metadata: DatasetMetadata,
        source_df: pd.DataFrame,
        feature_version_id: str,
        compute_fn: Callable[[pd.DataFrame, Dict[str, Any]], pd.DataFrame]
    ) -> Tuple[FeatureDatasetMetadata, pd.DataFrame]:
        """Compute feature dataset from source dataset.

        Args:
            source_dataset_metadata: Source dataset metadata
            source_df: Source dataset DataFrame
            feature_version_id: Feature version to compute
            compute_fn: Function that computes features given (df, parameters)

        Returns:
            Tuple of (FeatureDatasetMetadata, feature DataFrame)
        """
        if not source_dataset_metadata.is_frozen:
            raise ValueError(
                f"Source dataset must be FROZEN. Current state: {source_dataset_metadata.lifecycle_state.value}"
            )

        feature_version = self.repository.find_version(feature_version_id)
        if not feature_version:
            raise ValueError(f"Feature version not found: {feature_version_id}")

        feature_df = compute_fn(source_df.copy(), feature_version.parameters)

        if 'timestamp' not in feature_df.columns or 'symbol' not in feature_df.columns:
            raise ValueError("Feature DataFrame must contain 'timestamp' and 'symbol' columns")

        validation_result = self.validator.validate_feature_dataset(
            source_df, feature_df, feature_version.feature_name
        )
        if not validation_result.is_valid:
            raise ValueError(f"Feature validation failed: {validation_result.errors}")

        fingerprint = self._compute_fingerprint(feature_df)

        existing = self.repository.find_dataset_by_fingerprint(fingerprint)
        if existing:
            raise ValueError(
                f"Feature dataset with fingerprint {fingerprint} already exists: {existing.feature_dataset_id}"
            )

        feature_dataset_id = f"fds_{feature_version_id}_ds_{source_dataset_metadata.dataset_id}"

        storage_path = str(self.storage_dir / f"{feature_dataset_id}.parquet")

        metadata = FeatureDatasetMetadata(
            feature_dataset_id=feature_dataset_id,
            source_dataset_id=source_dataset_metadata.dataset_id,
            feature_version_id=feature_version_id,
            fingerprint=fingerprint,
            created_at=datetime.utcnow().isoformat(),
            lifecycle_state=FeatureLifecycleState.COMPUTED,
            storage_path=storage_path,
            is_frozen=False
        )

        metadata = replace(metadata, lifecycle_state=FeatureLifecycleState.VALIDATED)

        feature_df.to_parquet(storage_path, index=False, compression='gzip')

        self.repository.save_dataset(metadata)

        return metadata, feature_df

    def get_feature_dataset(
        self, feature_dataset_id: str
    ) -> Tuple[FeatureDatasetMetadata, pd.DataFrame]:
        """Get feature dataset by ID and verify integrity.

        Args:
            feature_dataset_id: Feature dataset identifier

        Returns:
            Tuple of (FeatureDatasetMetadata, feature DataFrame)
        """
        metadata = self.repository.find_dataset_by_id(feature_dataset_id)
        if not metadata:
            raise ValueError(f"Feature dataset not found: {feature_dataset_id}")

        df = pd.read_parquet(metadata.storage_path)

        current_fingerprint = self._compute_fingerprint(df)
        if current_fingerprint != metadata.fingerprint:
            raise ValueError(
                f"Fingerprint mismatch for {feature_dataset_id}. "
                f"Expected {metadata.fingerprint}, got {current_fingerprint}. "
                f"Feature dataset may have been tampered with."
            )

        return metadata, df

    def freeze_feature_dataset(self, feature_dataset_id: str) -> None:
        """Freeze feature dataset to make it immutable.

        Args:
            feature_dataset_id: Feature dataset identifier
        """
        metadata = self.repository.find_dataset_by_id(feature_dataset_id)
        if not metadata:
            raise ValueError(f"Feature dataset not found: {feature_dataset_id}")

        if metadata.lifecycle_state != FeatureLifecycleState.VALIDATED:
            raise ValueError(
                f"Can only freeze VALIDATED feature datasets. Current state: {metadata.lifecycle_state.value}"
            )

        self.repository.freeze(feature_dataset_id)

        import os
        os.chmod(metadata.storage_path, 0o444)

    def merge_dataset_features(
        self,
        source_df: pd.DataFrame,
        feature_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Merge source dataset with computed features.

        Args:
            source_df: Source dataset DataFrame
            feature_df: Feature dataset DataFrame

        Returns:
            Merged DataFrame
        """
        if len(source_df) != len(feature_df):
            raise ValueError(
                f"Row count mismatch: source={len(source_df)}, features={len(feature_df)}"
            )

        merged = pd.merge(
            source_df,
            feature_df,
            on=['timestamp', 'symbol'],
            how='inner'
        )

        if len(merged) != len(source_df):
            raise ValueError("Index alignment mismatch in feature merge")

        return merged

    def _compute_fingerprint(self, df: pd.DataFrame) -> str:
        """Compute SHA256 fingerprint of feature dataset.

        Canonicalization:
        - Rows sorted by (timestamp, symbol) for determinism
        - Columns sorted alphabetically
        - Numeric values formatted with fixed precision
        """
        df_sorted = df.copy()
        sort_keys = ['timestamp', 'symbol'] if 'symbol' in df.columns else ['timestamp']
        df_sorted = df_sorted.sort_values(sort_keys).reset_index(drop=True)
        df_sorted = df_sorted[sorted(df_sorted.columns)]

        for col in df_sorted.columns:
            if pd.api.types.is_float_dtype(df_sorted[col]):
                df_sorted[col] = df_sorted[col].apply(lambda x: f"{x:.8f}" if pd.notna(x) else "NaN")

        payload = df_sorted.to_json(orient='records', lines=True)

        return hashlib.sha256(payload.encode('utf-8')).hexdigest()
