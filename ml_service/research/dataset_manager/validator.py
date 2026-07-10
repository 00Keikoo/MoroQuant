"""Validation logic for datasets."""

import pandas as pd
from datetime import datetime, UTC
from typing import List, Optional

from ml_service.research.dataset_manager.types import ValidationResult, DatasetSchema


class DatasetValidator:
    """Validates dataset structure and data quality."""

    def __init__(self, nan_threshold: float = 0.01):
        """Initialize validator.

        Args:
            nan_threshold: Maximum allowed missing value ratio (default 1%)
        """
        self.nan_threshold = nan_threshold

    def validate(self, df: pd.DataFrame, schema: DatasetSchema) -> ValidationResult:
        """Run full validation suite on dataset.

        Args:
            df: Dataset dataframe
            schema: Expected schema

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        errors.extend(self._validate_structure(df, schema))
        errors.extend(self._validate_data_quality(df))
        errors.extend(self._validate_scientific_integrity(df))

        warnings.extend(self._check_warnings(df))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _validate_structure(self, df: pd.DataFrame, schema: DatasetSchema) -> List[str]:
        """Validate structural requirements."""
        errors = []

        if 'timestamp' not in df.columns:
            errors.append("Missing required column: timestamp")

        if 'symbol' not in df.columns:
            errors.append("Missing required column: symbol")

        for feature in schema.features:
            if feature not in df.columns:
                errors.append(f"Missing feature column: {feature}")

        for target in schema.targets:
            if target not in df.columns:
                errors.append(f"Missing target column: {target}")

        if 'timestamp' in df.columns:
            if not pd.api.types.is_numeric_dtype(df['timestamp']):
                errors.append("timestamp column must be numeric")

            if not df['timestamp'].is_monotonic_increasing:
                errors.append("Timestamps must be strictly increasing")

        for col, expected_dtype in schema.data_types.items():
            if col in df.columns:
                actual_dtype = str(df[col].dtype)
                if expected_dtype == 'float64' and actual_dtype not in ['float64', 'float32']:
                    errors.append(f"Column {col} expected {expected_dtype}, got {actual_dtype}")
                elif expected_dtype == 'int32' and actual_dtype not in ['int32', 'int64']:
                    errors.append(f"Column {col} expected {expected_dtype}, got {actual_dtype}")

        return errors

    def _validate_data_quality(self, df: pd.DataFrame) -> List[str]:
        """Validate data quality requirements."""
        errors = []

        if 'timestamp' in df.columns and 'symbol' in df.columns:
            duplicates = df.duplicated(subset=['timestamp', 'symbol'])
            if duplicates.any():
                errors.append(f"Found {duplicates.sum()} duplicate (timestamp, symbol) pairs")

        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                nan_ratio = df[col].isna().sum() / len(df)
                if nan_ratio > self.nan_threshold:
                    errors.append(f"Column {col} has {nan_ratio:.2%} missing values (threshold: {self.nan_threshold:.2%})")

                if (df[col] == float('inf')).any() or (df[col] == float('-inf')).any():
                    errors.append(f"Column {col} contains infinite values")

                if col not in ['timestamp', 'symbol', 'confidence'] and df[col].var() == 0:
                    errors.append(f"Column {col} has zero variance (dead feature)")

        return errors

    def _validate_scientific_integrity(self, df: pd.DataFrame) -> List[str]:
        """Validate scientific integrity (leakage prevention).

        Checks:
        - Future leakage: timestamps must not exceed current time
        - Time gap validation: detect unrealistic gaps in time series
        """
        errors = []

        if 'timestamp' not in df.columns:
            return errors

        errors.extend(self._validate_future_leakage(df))
        errors.extend(self._validate_time_gaps(df))

        return errors

    def _validate_future_leakage(self, df: pd.DataFrame) -> List[str]:
        """Prevent future timestamps that indicate data leakage."""
        errors = []

        current_time = datetime.now(UTC).timestamp()
        max_timestamp = df['timestamp'].max()

        if max_timestamp > current_time:
            future_count = (df['timestamp'] > current_time).sum()
            errors.append(
                f"Future leakage detected: {future_count} timestamps exceed current time "
                f"(max: {max_timestamp}, current: {current_time})"
            )

        return errors

    def _validate_time_gaps(self, df: pd.DataFrame, max_gap_multiplier: float = 100.0) -> List[str]:
        """Detect unrealistic gaps in time series continuity.

        Args:
            df: Dataset with timestamp column
            max_gap_multiplier: Maximum allowed gap as multiple of median interval
        """
        errors = []

        if len(df) < 3:
            return errors

        timestamps = df['timestamp'].sort_values()
        time_diffs = timestamps.diff().dropna()

        if len(time_diffs) == 0:
            return errors

        median_interval = time_diffs.median()

        if median_interval == 0:
            return errors

        max_allowed_gap = median_interval * max_gap_multiplier
        large_gaps = time_diffs[time_diffs > max_allowed_gap]

        if len(large_gaps) > 0:
            errors.append(
                f"Time continuity violation: {len(large_gaps)} gaps exceed {max_gap_multiplier}x "
                f"median interval (median: {median_interval}s, max gap: {large_gaps.max()}s)"
            )

        return errors

    def _check_warnings(self, df: pd.DataFrame) -> List[str]:
        """Generate non-critical warnings."""
        warnings = []

        if len(df) < 100:
            warnings.append(f"Dataset has only {len(df)} rows (small sample size)")

        return warnings
