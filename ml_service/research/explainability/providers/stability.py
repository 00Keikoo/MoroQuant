"""Feature importance stability diagnostic provider."""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
import logging

from .base import BaseDiagnosticProvider

logger = logging.getLogger(__name__)


class StabilityProvider(BaseDiagnosticProvider):
    """Analyzes feature importance stability across validation folds."""

    def execute(
        self,
        model: Any,
        X: Any,
        y: Any,
        feature_names: List[str]
    ) -> Dict[str, Any]:
        """Execute stability analysis.

        Args:
            model: Trained model (unused in this provider)
            X: Feature importance matrix across folds (ndarray or list)
            y: Target vector (unused but required by interface)
            feature_names: List of feature names

        Returns:
            Dict containing stability metrics

        Raises:
            ValueError: If importance matrix format is invalid
        """
        importance_matrix = self._parse_importance_matrix(X)

        if importance_matrix.shape[1] != len(feature_names):
            raise ValueError(
                f"Number of features in importance matrix ({importance_matrix.shape[1]}) "
                f"does not match feature_names length ({len(feature_names)})"
            )

        mean_importances = importance_matrix.mean(axis=0)
        std_importances = importance_matrix.std(axis=0)

        rank_matrix = self._compute_rank_matrix(importance_matrix)
        rank_variances = rank_matrix.var(axis=0)

        stability_metrics = {}
        for i, feature_name in enumerate(feature_names):
            stability_metrics[feature_name] = {
                'mean_importance': float(mean_importances[i]),
                'std_deviation': float(std_importances[i]),
                'rank_variance': float(rank_variances[i]),
                'coefficient_of_variation': float(
                    std_importances[i] / (mean_importances[i] + 1e-10)
                )
            }

        overall_stability_score = float(1.0 / (1.0 + rank_variances.mean()))

        return {
            'stability_metrics': stability_metrics,
            'overall_stability_score': overall_stability_score,
            'n_folds': importance_matrix.shape[0],
            'mean_rank_variance': float(rank_variances.mean())
        }

    def _parse_importance_matrix(self, X: Any) -> np.ndarray:
        """Parse importance matrix from various input formats.

        Args:
            X: Importance matrix (ndarray, DataFrame, or list of arrays)

        Returns:
            2D numpy array where rows are folds, columns are features

        Raises:
            ValueError: If input format is invalid
        """
        if isinstance(X, pd.DataFrame):
            return X.values

        elif isinstance(X, np.ndarray):
            if X.ndim == 1:
                return X.reshape(1, -1)
            elif X.ndim == 2:
                return X
            else:
                raise ValueError(f"Invalid importance matrix shape: {X.shape}")

        elif isinstance(X, list):
            return np.array(X)

        else:
            raise ValueError(f"Unsupported importance matrix type: {type(X)}")

    def _compute_rank_matrix(self, importance_matrix: np.ndarray) -> np.ndarray:
        """Compute ranking positions for each fold.

        Args:
            importance_matrix: 2D array (folds x features)

        Returns:
            2D array of ranks (folds x features)
        """
        rank_matrix = np.zeros_like(importance_matrix, dtype=int)

        for fold_idx in range(importance_matrix.shape[0]):
            sorted_indices = np.argsort(-importance_matrix[fold_idx, :])
            ranks = np.empty_like(sorted_indices)
            ranks[sorted_indices] = np.arange(len(sorted_indices))
            rank_matrix[fold_idx, :] = ranks

        return rank_matrix
