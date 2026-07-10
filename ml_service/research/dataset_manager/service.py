"""Service layer for dataset manager."""

import hashlib
import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd

from ml_service.research.dataset_manager.types import (
    DatasetMetadata,
    TimeBounds,
    DatasetSchema,
    LifecycleState,
    ValidationResult
)
from ml_service.research.dataset_manager.repository import DatasetRepository
from ml_service.research.dataset_manager.validator import DatasetValidator
from ml_service.research.snapshot_engine.types import Snapshot


class DatasetService:
    """Service for managing datasets."""

    def __init__(self, db_path: Optional[str] = None, storage_dir: Optional[str] = None):
        """Initialize dataset service.

        Args:
            db_path: Optional database path
            storage_dir: Optional storage directory for dataset payloads
        """
        self.repository = DatasetRepository(db_path)
        self.validator = DatasetValidator()

        if storage_dir is None:
            storage_dir = Path(__file__).parent.parent.parent.parent / "storage" / "datasets"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def create_dataset(
        self,
        snapshot: Snapshot,
        version: str = "1.0.0",
        symbol_filter: Optional[str] = None
    ) -> Tuple[DatasetMetadata, pd.DataFrame]:
        """Create dataset from snapshot.

        Args:
            snapshot: Source snapshot
            version: Semantic version string
            symbol_filter: Optional symbol filter

        Returns:
            Tuple of (DatasetMetadata, DataFrame payload)
        """
        df = self._snapshot_to_dataframe(snapshot, symbol_filter)

        schema = self._infer_schema(df)
        time_bounds = self._extract_time_bounds(df)

        fingerprint = self._compute_fingerprint(df)

        existing = self.repository.find_by_fingerprint(fingerprint)
        if existing:
            raise ValueError(f"Dataset with fingerprint {fingerprint} already exists: {existing.dataset_id}")

        symbol_part = symbol_filter.lower() if symbol_filter else "all"
        dataset_id = f"ds_{symbol_part}_v{version}"

        storage_path = str(self.storage_dir / f"{dataset_id}.parquet")

        metadata = DatasetMetadata(
            dataset_id=dataset_id,
            version=version,
            fingerprint=fingerprint,
            snapshot_id=snapshot.snapshot_id,
            created_at=datetime.utcnow().isoformat(),
            time_bounds=time_bounds,
            schema=schema,
            lifecycle_state=LifecycleState.DRAFT,
            storage_path=storage_path,
            is_frozen=False
        )

        validation_result = self.validator.validate(df, schema)
        if not validation_result.is_valid:
            raise ValueError(f"Dataset validation failed: {validation_result.errors}")

        metadata = replace(metadata, lifecycle_state=LifecycleState.VALIDATED)

        df.to_parquet(storage_path, index=False, compression='gzip')

        self.repository.save(metadata)

        return metadata, df

    def get_dataset(self, dataset_id: str) -> Tuple[DatasetMetadata, pd.DataFrame]:
        """Get dataset by ID and verify integrity.

        Args:
            dataset_id: Dataset identifier

        Returns:
            Tuple of (DatasetMetadata, DataFrame payload)
        """
        metadata = self.repository.find_by_id(dataset_id)
        if not metadata:
            raise ValueError(f"Dataset not found: {dataset_id}")

        df = pd.read_parquet(metadata.storage_path)

        current_fingerprint = self._compute_fingerprint(df)
        if current_fingerprint != metadata.fingerprint:
            raise ValueError(
                f"Fingerprint mismatch for {dataset_id}. "
                f"Expected {metadata.fingerprint}, got {current_fingerprint}. "
                f"Dataset may have been tampered with."
            )

        return metadata, df

    def freeze_dataset(self, dataset_id: str) -> None:
        """Freeze dataset to make it immutable.

        Args:
            dataset_id: Dataset identifier
        """
        metadata = self.repository.find_by_id(dataset_id)
        if not metadata:
            raise ValueError(f"Dataset not found: {dataset_id}")

        if metadata.lifecycle_state != LifecycleState.VALIDATED:
            raise ValueError(f"Can only freeze VALIDATED datasets. Current state: {metadata.lifecycle_state.value}")

        self.repository.freeze(dataset_id)

        import os
        os.chmod(metadata.storage_path, 0o444)

    def _snapshot_to_dataframe(self, snapshot: Snapshot, symbol_filter: Optional[str]) -> pd.DataFrame:
        """Convert snapshot to tabular dataframe."""
        records = []

        for signal in snapshot.signals:
            if symbol_filter and signal.get('symbol') != symbol_filter:
                continue

            record = {
                'timestamp': signal.get('timestamp', 0),
                'symbol': signal.get('symbol', ''),
                'direction': signal.get('direction', 'neutral'),
                'confidence': signal.get('confidence', 0)
            }

            if signal.get('features_json'):
                features = json.loads(signal['features_json']) if isinstance(signal['features_json'], str) else signal['features_json']
                record.update(features)

            records.append(record)

        if not records:
            raise ValueError("No records to create dataset from")

        df = pd.DataFrame(records)

        df = df.sort_values('timestamp').reset_index(drop=True)

        return df

    def _infer_schema(self, df: pd.DataFrame) -> DatasetSchema:
        """Infer schema from dataframe."""
        feature_cols = [col for col in df.columns
                       if col not in ['timestamp', 'symbol', 'direction', 'confidence']]
        target_cols = ['direction']

        data_types = {}
        for col in df.columns:
            dtype = str(df[col].dtype)
            if 'float' in dtype:
                data_types[col] = 'float64'
            elif 'int' in dtype:
                data_types[col] = 'int32'
            else:
                data_types[col] = 'string'

        return DatasetSchema(
            features=sorted(feature_cols),
            targets=target_cols,
            data_types=data_types
        )

    def _extract_time_bounds(self, df: pd.DataFrame) -> TimeBounds:
        """Extract time bounds from dataframe."""
        start_time = str(df['timestamp'].min())
        end_time = str(df['timestamp'].max())
        return TimeBounds(start_time=start_time, end_time=end_time)

    def _compute_fingerprint(self, df: pd.DataFrame) -> str:
        """Compute SHA256 fingerprint of dataset.

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
