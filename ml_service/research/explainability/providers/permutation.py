"""Permutation importance diagnostic provider."""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Callable
import logging

from .base import BaseDiagnosticProvider

logger = logging.getLogger(__name__)


class PermutationProvider(BaseDiagnosticProvider):
    """Computes feature importance via permutation degradation analysis."""

    def execute(
        self,
        model: Any,
        X: Any,
        y: Any,
        feature_names: List[str]
    ) -> Dict[str, Any]:
        """Execute permutation importance computation.

        Args:
            model: Trained model with predict method
            X: Feature matrix (DataFrame or ndarray)
            y: Target vector (Series or ndarray)
            feature_names: List of feature names

        Returns:
            Dict containing permutation importances and degradation metrics

        Raises:
            ValueError: If model lacks predict method
        """
        if not hasattr(model, 'predict'):
            raise ValueError("Model must have a 'predict' method")

        if isinstance(X, pd.DataFrame):
            X_array = X.values
        else:
            X_array = np.asarray(X)

        if isinstance(y, pd.Series):
            y_array = y.values
        else:
            y_array = np.asarray(y)

        baseline_predictions = model.predict(X_array)
        baseline_score = self._compute_score(y_array, baseline_predictions)

        n_repetitions = self.config.get('permutation_repetitions', 10)
        random_seed = self.config.get('random_seed', 42)

        importances = []

        for feature_idx in range(X_array.shape[1]):
            feature_degradations = []

            for rep in range(n_repetitions):
                X_permuted = X_array.copy()

                np.random.seed(random_seed + rep + feature_idx * 1000)
                permuted_indices = np.random.permutation(X_array.shape[0])
                X_permuted[:, feature_idx] = X_array[permuted_indices, feature_idx]

                permuted_predictions = model.predict(X_permuted)
                permuted_score = self._compute_score(y_array, permuted_predictions)

                degradation = baseline_score - permuted_score
                feature_degradations.append(degradation)

            mean_degradation = np.mean(feature_degradations)
            std_degradation = np.std(feature_degradations)

            importances.append({
                'feature': feature_names[feature_idx],
                'importance': float(mean_degradation),
                'std': float(std_degradation)
            })

        importances_sorted = sorted(
            importances,
            key=lambda x: x['importance'],
            reverse=True
        )

        feature_importance = {
            item['feature']: item['importance']
            for item in importances_sorted
        }

        return {
            'importances': importances_sorted,
            'feature_importance': feature_importance,
            'baseline_score': float(baseline_score),
            'metric_type': self._get_metric_type()
        }

    def _compute_score(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Compute performance score based on problem type.

        Args:
            y_true: True target values
            y_pred: Predicted values

        Returns:
            Performance score (higher is better)
        """
        metric_type = self.config.get('metric_type', 'auto')

        if metric_type == 'auto':
            metric_type = self._infer_metric_type(y_true)

        if metric_type == 'classification':
            return self._accuracy_score(y_true, y_pred)
        elif metric_type == 'regression':
            return -self._mean_squared_error(y_true, y_pred)
        else:
            return self._accuracy_score(y_true, y_pred)

    def _infer_metric_type(self, y: np.ndarray) -> str:
        """Infer whether problem is classification or regression.

        Args:
            y: Target vector

        Returns:
            'classification' or 'regression'
        """
        unique_values = np.unique(y)

        if len(unique_values) <= 10 and np.all(y == y.astype(int)):
            return 'classification'
        else:
            return 'regression'

    def _accuracy_score(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Compute classification accuracy.

        Args:
            y_true: True labels
            y_pred: Predicted labels

        Returns:
            Accuracy score
        """
        return float(np.mean(y_true == y_pred))

    def _mean_squared_error(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Compute mean squared error.

        Args:
            y_true: True values
            y_pred: Predicted values

        Returns:
            MSE score
        """
        return float(np.mean((y_true - y_pred) ** 2))

    def _get_metric_type(self) -> str:
        """Get the metric type used for scoring."""
        return self.config.get('metric_type', 'auto')
