"""Correlation analysis diagnostic provider."""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
import logging

from .base import BaseDiagnosticProvider

logger = logging.getLogger(__name__)


class CorrelationProvider(BaseDiagnosticProvider):
    """Computes feature correlation matrices for multicollinearity detection."""

    def execute(
        self,
        model: Any,
        X: Any,
        y: Any,
        feature_names: List[str]
    ) -> Dict[str, Any]:
        """Execute correlation analysis.

        Args:
            model: Trained model (unused but required by interface)
            X: Feature matrix (DataFrame or ndarray)
            y: Target vector (unused but required by interface)
            feature_names: List of feature names

        Returns:
            Dict containing Pearson and Spearman correlation matrices

        Raises:
            ValueError: If feature matrix is invalid
        """
        if isinstance(X, pd.DataFrame):
            df = X.copy()
            df.columns = feature_names[:X.shape[1]]
        else:
            X_array = np.array(X, copy=True)
            df = pd.DataFrame(X_array, columns=feature_names[:X_array.shape[1]])

        pearson_corr = df.corr(method='pearson')
        spearman_corr = df.corr(method='spearman')

        pearson_corr = self._handle_nan_correlation(pearson_corr)
        spearman_corr = self._handle_nan_correlation(spearman_corr)

        high_corr_threshold = self.config.get('high_correlation_threshold', 0.85)
        high_corr_pairs = self._find_high_correlations(
            pearson_corr,
            threshold=high_corr_threshold
        )

        return {
            'pearson_matrix': pearson_corr.values.tolist(),
            'spearman_matrix': spearman_corr.values.tolist(),
            'feature_names': list(df.columns),
            'high_correlation_pairs': high_corr_pairs,
            'max_correlation': float(self._get_max_offdiag_corr(pearson_corr))
        }

    def _handle_nan_correlation(self, corr_matrix: pd.DataFrame) -> pd.DataFrame:
        """Replace NaN values in correlation matrix with 0.0.

        Args:
            corr_matrix: Correlation matrix potentially containing NaN

        Returns:
            Correlation matrix with NaN replaced by 0.0
        """
        corr_filled = corr_matrix.fillna(0.0)

        if corr_filled.isna().any().any():
            logger.warning("NaN values detected in correlation matrix after fillna")

        return corr_filled

    def _find_high_correlations(
        self,
        corr_matrix: pd.DataFrame,
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Find feature pairs with correlation above threshold.

        Args:
            corr_matrix: Correlation matrix
            threshold: Absolute correlation threshold

        Returns:
            List of high correlation pairs with values
        """
        high_corr = []

        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                corr_value = corr_matrix.iloc[i, j]

                if abs(corr_value) >= threshold:
                    high_corr.append({
                        'feature_1': corr_matrix.columns[i],
                        'feature_2': corr_matrix.columns[j],
                        'correlation': float(corr_value)
                    })

        return high_corr

    def _get_max_offdiag_corr(self, corr_matrix: pd.DataFrame) -> float:
        """Get maximum absolute off-diagonal correlation.

        Args:
            corr_matrix: Correlation matrix

        Returns:
            Maximum absolute correlation excluding diagonal
        """
        values = corr_matrix.values.copy()
        np.fill_diagonal(values, 0.0)
        return float(np.abs(values).max())
