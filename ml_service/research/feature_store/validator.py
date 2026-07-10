"""Validator layer for feature store quality and leakage checks."""

import pandas as pd
import numpy as np
from typing import Optional
from datetime import datetime

from ml_service.research.feature_store.feature_types import ValidationResult


class FeatureValidator:
    """Validates feature datasets for leakage, quality, and integrity."""

    def validate_feature_dataset(
        self,
        source_df: pd.DataFrame,
        feature_df: pd.DataFrame,
        feature_name: str
    ) -> ValidationResult:
        """Comprehensive validation of feature dataset.

        Args:
            source_df: Source dataset with (timestamp, symbol) index
            feature_df: Computed feature dataset
            feature_name: Name of feature for error messages

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        try:
            self._validate_index_integrity(source_df, feature_df, errors)
            self._validate_leakage_protection(source_df, feature_df, errors)
            self._validate_quality_checks(feature_df, feature_name, errors, warnings)
        except Exception as e:
            errors.append(f"Validation exception: {str(e)}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _validate_index_integrity(
        self,
        source_df: pd.DataFrame,
        feature_df: pd.DataFrame,
        errors: list
    ) -> None:
        """Validate timestamp and symbol alignment."""
        if len(source_df) != len(feature_df):
            errors.append(
                f"Row count mismatch: source={len(source_df)}, features={len(feature_df)}"
            )
            return

        if not all(source_df['timestamp'] == feature_df['timestamp']):
            errors.append("Timestamp alignment mismatch between source and features")

        if not all(source_df['symbol'] == feature_df['symbol']):
            errors.append("Symbol alignment mismatch between source and features")

        if not self._is_sorted_chronologically(feature_df):
            errors.append("Feature dataset not sorted chronologically by timestamp")

    def _validate_leakage_protection(
        self,
        source_df: pd.DataFrame,
        feature_df: pd.DataFrame,
        errors: list
    ) -> None:
        """Validate no future data leakage."""
        source_max_ts = source_df['timestamp'].max()
        feature_max_ts = feature_df['timestamp'].max()

        if feature_max_ts > source_max_ts:
            errors.append(
                f"Future data leakage detected: feature timestamp {feature_max_ts} > "
                f"source maximum {source_max_ts}"
            )

    def _validate_quality_checks(
        self,
        feature_df: pd.DataFrame,
        feature_name: str,
        errors: list,
        warnings: list
    ) -> None:
        """Validate statistical quality of features."""
        feature_cols = [col for col in feature_df.columns
                       if col not in ['timestamp', 'symbol']]

        for col in feature_cols:
            values = feature_df[col]

            if values.isnull().all():
                errors.append(f"Feature column '{col}' is entirely null")
                continue

            missing_ratio = values.isnull().sum() / len(values)
            if missing_ratio > 0.95:
                warnings.append(
                    f"Feature column '{col}' has {missing_ratio:.1%} missing values"
                )

            non_null_values = values.dropna()
            if len(non_null_values) > 0:
                if np.isinf(non_null_values).any():
                    errors.append(f"Feature column '{col}' contains infinite values")

                if non_null_values.std() == 0 and len(non_null_values) > 1:
                    warnings.append(
                        f"Feature column '{col}' has zero variance (constant value)"
                    )

    def _is_sorted_chronologically(self, df: pd.DataFrame) -> bool:
        """Check if dataframe is sorted by timestamp then symbol."""
        if 'timestamp' not in df.columns:
            return False
        return (df['timestamp'].diff().dropna() >= 0).all()
