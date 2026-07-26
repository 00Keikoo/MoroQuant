"""SHAP (SHapley Additive exPlanations) diagnostic provider."""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
import logging

from .base import BaseDiagnosticProvider

logger = logging.getLogger(__name__)


class ShapProvider(BaseDiagnosticProvider):
    """Computes Shapley additive explanations for model predictions."""

    def execute(
        self,
        model: Any,
        X: Any,
        y: Any,
        feature_names: List[str]
    ) -> Dict[str, Any]:
        """Execute SHAP value computation.

        Args:
            model: Trained model (tree-based or linear)
            X: Feature matrix (DataFrame or ndarray)
            y: Target vector (unused but required by interface)
            feature_names: List of feature names

        Returns:
            Dict containing SHAP values and feature importance

        Raises:
            ImportError: If shap library is not installed
            ValueError: If model type is unsupported
        """
        try:
            import shap
        except ImportError:
            raise ImportError(
                "SHAP library is required. Install with: pip install shap"
            )

        if isinstance(X, pd.DataFrame):
            X_array = X.values
        else:
            X_array = np.asarray(X)

        max_samples = self.config.get('max_shap_samples', 2500)
        if X_array.shape[0] > max_samples:
            logger.warning(
                f"Dataset has {X_array.shape[0]} samples, "
                f"subsampling to {max_samples}"
            )
            random_seed = self.config.get('random_seed', 42)
            np.random.seed(random_seed)
            indices = np.random.choice(
                X_array.shape[0],
                size=max_samples,
                replace=False
            )
            X_sampled = X_array[indices]
        else:
            X_sampled = X_array
            indices = np.arange(X_array.shape[0])

        explainer = self._get_explainer(model, X_sampled)
        shap_values = explainer.shap_values(X_sampled)

        if isinstance(shap_values, list):
            shap_values = shap_values[0]

        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        importance_scores = mean_abs_shap / mean_abs_shap.sum()

        shap_df = pd.DataFrame(
            shap_values,
            columns=[f'shap_val_{name}' for name in feature_names]
        )
        shap_df['observation_index'] = indices

        raw_df = pd.DataFrame(
            X_sampled,
            columns=[f'raw_val_{name}' for name in feature_names]
        )

        combined_df = pd.concat([shap_df, raw_df], axis=1)

        feature_importance = {
            name: float(score)
            for name, score in zip(feature_names, importance_scores)
        }

        return {
            'shap_values': shap_values,
            'shap_dataframe': combined_df,
            'feature_importance': feature_importance,
            'explainer_type': type(explainer).__name__
        }

    def _get_explainer(self, model: Any, X: np.ndarray):
        """Select appropriate SHAP explainer based on model type.

        Args:
            model: Trained model
            X: Feature matrix

        Returns:
            Configured SHAP explainer

        Raises:
            ValueError: If model type is not supported
        """
        import shap

        model_class = type(model).__name__
        model_module = type(model).__module__

        if 'xgboost' in model_module.lower() or 'XGB' in model_class:
            logger.info("Using TreeExplainer for XGBoost model")
            return shap.TreeExplainer(model)

        elif 'lightgbm' in model_module.lower() or 'LGB' in model_class:
            logger.info("Using TreeExplainer for LightGBM model")
            return shap.TreeExplainer(model)

        elif hasattr(model, 'tree_') or 'Tree' in model_class:
            logger.info(f"Using TreeExplainer for {model_class}")
            return shap.TreeExplainer(model)

        elif hasattr(model, 'coef_'):
            logger.info(f"Using LinearExplainer for {model_class}")
            return shap.LinearExplainer(model, X)

        else:
            logger.warning(
                f"Unknown model type {model_class}, falling back to KernelExplainer"
            )
            return shap.KernelExplainer(model.predict, X)
