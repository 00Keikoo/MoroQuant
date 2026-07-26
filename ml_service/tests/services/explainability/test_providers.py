"""Unit tests for diagnostic providers."""

import pytest
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification, make_regression

from research.explainability.providers import (
    ShapProvider,
    CorrelationProvider,
    PermutationProvider,
    StabilityProvider,
)


class TestShapProvider:
    """Test suite for ShapProvider."""

    @pytest.fixture
    def provider(self):
        """Create ShapProvider instance."""
        return ShapProvider(config={'max_shap_samples': 100, 'random_seed': 42})

    @pytest.fixture
    def tree_model_and_data(self):
        """Create tree-based model and dataset."""
        X, y = make_classification(
            n_samples=150,
            n_features=6,
            n_informative=4,
            n_redundant=1,
            random_state=42
        )
        model = RandomForestClassifier(n_estimators=10, random_state=42, max_depth=3)
        model.fit(X, y)
        feature_names = [f'feature_{i}' for i in range(6)]
        return model, X, y, feature_names

    @pytest.fixture
    def linear_model_and_data(self):
        """Create linear model and dataset."""
        X, y = make_regression(
            n_samples=100,
            n_features=5,
            n_informative=4,
            random_state=42
        )
        model = LinearRegression()
        model.fit(X, y)
        feature_names = [f'linear_feature_{i}' for i in range(5)]
        return model, X, y, feature_names

    def test_shap_tree_model(self, provider, tree_model_and_data):
        """Test SHAP computation on tree-based model."""
        model, X, y, feature_names = tree_model_and_data

        result = provider.execute(model, X, y, feature_names)

        assert 'shap_values' in result
        assert 'feature_importance' in result
        assert 'shap_dataframe' in result
        assert len(result['feature_importance']) == len(feature_names)
        assert result['explainer_type'] == 'TreeExplainer'

    def test_shap_linear_model(self, provider, linear_model_and_data):
        """Test SHAP computation on linear model."""
        model, X, y, feature_names = linear_model_and_data

        result = provider.execute(model, X, y, feature_names)

        assert 'shap_values' in result
        assert 'feature_importance' in result
        assert result['explainer_type'] == 'LinearExplainer'

    def test_shap_importance_sums_to_one(self, provider, tree_model_and_data):
        """Test feature importances sum to approximately 1.0."""
        model, X, y, feature_names = tree_model_and_data

        result = provider.execute(model, X, y, feature_names)

        importance_sum = sum(result['feature_importance'].values())
        assert importance_sum == pytest.approx(1.0, abs=0.01)

    def test_shap_subsampling(self, provider, tree_model_and_data):
        """Test that SHAP subsamples large datasets."""
        model, X, y, feature_names = tree_model_and_data
        provider.config['max_shap_samples'] = 50

        result = provider.execute(model, X, y, feature_names)

        assert 'shap_dataframe' in result
        assert len(result['shap_dataframe']) == 50

    def test_shap_pandas_input(self, provider, tree_model_and_data):
        """Test SHAP with pandas DataFrame input."""
        model, X, y, feature_names = tree_model_and_data
        X_df = pd.DataFrame(X, columns=feature_names)

        result = provider.execute(model, X_df, y, feature_names)

        assert 'feature_importance' in result
        assert len(result['feature_importance']) == len(feature_names)

    def test_shap_dataframe_structure(self, provider, tree_model_and_data):
        """Test SHAP dataframe contains both SHAP values and raw values."""
        model, X, y, feature_names = tree_model_and_data

        result = provider.execute(model, X, y, feature_names)

        shap_df = result['shap_dataframe']
        assert 'observation_index' in shap_df.columns

        for name in feature_names:
            assert f'shap_val_{name}' in shap_df.columns
            assert f'raw_val_{name}' in shap_df.columns


class TestCorrelationProvider:
    """Test suite for CorrelationProvider."""

    @pytest.fixture
    def provider(self):
        """Create CorrelationProvider instance."""
        return CorrelationProvider(config={})

    def test_correlation_perfect_linear(self, provider):
        """Test detection of perfect linear correlation."""
        X = np.array([[1, 2], [2, 4], [3, 6], [4, 8]])
        feature_names = ['feature_a', 'feature_b']

        result = provider.execute(None, X, None, feature_names)

        assert 'pearson_matrix' in result
        assert 'spearman_matrix' in result
        pearson = np.array(result['pearson_matrix'])
        assert pearson[0, 1] == pytest.approx(1.0, abs=0.01)

    def test_correlation_independent_features(self, provider):
        """Test uncorrelated features have low correlation."""
        np.random.seed(42)
        X = np.random.randn(100, 3)
        feature_names = ['f1', 'f2', 'f3']

        result = provider.execute(None, X, None, feature_names)

        pearson = np.array(result['pearson_matrix'])
        for i in range(3):
            for j in range(3):
                if i != j:
                    assert abs(pearson[i, j]) < 0.3

    def test_correlation_high_threshold_detection(self, provider):
        """Test high correlation pair detection."""
        provider.config['high_correlation_threshold'] = 0.9
        X = np.array([[1, 1.01], [2, 2.02], [3, 3.01]])
        feature_names = ['feature_x', 'feature_y']

        result = provider.execute(None, X, None, feature_names)

        assert len(result['high_correlation_pairs']) > 0
        assert result['max_correlation'] > 0.9

    def test_correlation_handles_nan_columns(self, provider):
        """Test provider handles constant columns gracefully."""
        X = np.array([[1, 5], [2, 5], [3, 5]])
        feature_names = ['varying', 'constant']

        result = provider.execute(None, X, None, feature_names)

        assert 'pearson_matrix' in result
        assert len(result['feature_names']) == 2


class TestPermutationProvider:
    """Test suite for PermutationProvider."""

    @pytest.fixture
    def provider(self):
        """Create PermutationProvider instance."""
        return PermutationProvider(config={
            'permutation_repetitions': 5,
            'random_seed': 42
        })

    @pytest.fixture
    def classification_model_and_data(self):
        """Create classification model and dataset."""
        X, y = make_classification(
            n_samples=100,
            n_features=5,
            n_informative=3,
            n_redundant=0,
            random_state=42
        )
        model = DecisionTreeClassifier(random_state=42)
        model.fit(X, y)
        feature_names = [f'feature_{i}' for i in range(5)]
        return model, X, y, feature_names

    @pytest.fixture
    def regression_model_and_data(self):
        """Create regression model and dataset."""
        X, y = make_regression(
            n_samples=100,
            n_features=4,
            n_informative=3,
            random_state=42
        )
        model = LinearRegression()
        model.fit(X, y)
        feature_names = [f'reg_feature_{i}' for i in range(4)]
        return model, X, y, feature_names

    def test_permutation_classification(self, provider, classification_model_and_data):
        """Test permutation importance on classification model."""
        model, X, y, feature_names = classification_model_and_data

        result = provider.execute(model, X, y, feature_names)

        assert 'importances' in result
        assert 'feature_importance' in result
        assert len(result['importances']) == len(feature_names)
        assert result['baseline_score'] > 0

    def test_permutation_regression(self, provider, regression_model_and_data):
        """Test permutation importance on regression model."""
        provider.config['metric_type'] = 'regression'
        model, X, y, feature_names = regression_model_and_data

        result = provider.execute(model, X, y, feature_names)

        assert 'importances' in result
        assert len(result['feature_importance']) == len(feature_names)

    def test_permutation_degradation(self, provider, classification_model_and_data):
        """Test that permutation causes performance degradation."""
        model, X, y, feature_names = classification_model_and_data

        result = provider.execute(model, X, y, feature_names)

        importances = result['importances']
        assert any(item['importance'] > 0 for item in importances)

    def test_permutation_pandas_input(self, provider, classification_model_and_data):
        """Test permutation with pandas DataFrame input."""
        model, X, y, feature_names = classification_model_and_data
        X_df = pd.DataFrame(X, columns=feature_names)
        y_series = pd.Series(y)

        result = provider.execute(model, X_df, y_series, feature_names)

        assert 'feature_importance' in result
        assert len(result['feature_importance']) == len(feature_names)


class TestStabilityProvider:
    """Test suite for StabilityProvider."""

    @pytest.fixture
    def provider(self):
        """Create StabilityProvider instance."""
        return StabilityProvider(config={})

    def test_stability_consistent_importances(self, provider):
        """Test stability with highly consistent importances across folds."""
        importance_matrix = np.array([
            [0.5, 0.3, 0.2],
            [0.51, 0.29, 0.2],
            [0.49, 0.31, 0.2]
        ])
        feature_names = ['f1', 'f2', 'f3']

        result = provider.execute(None, importance_matrix, None, feature_names)

        assert 'stability_metrics' in result
        assert result['overall_stability_score'] > 0.8
        assert result['n_folds'] == 3

    def test_stability_unstable_rankings(self, provider):
        """Test stability with inconsistent feature rankings."""
        importance_matrix = np.array([
            [0.5, 0.3, 0.2],
            [0.2, 0.5, 0.3],
            [0.3, 0.2, 0.5]
        ])
        feature_names = ['f1', 'f2', 'f3']

        result = provider.execute(None, importance_matrix, None, feature_names)

        assert result['overall_stability_score'] < 0.7
        assert result['mean_rank_variance'] > 0

    def test_stability_single_fold(self, provider):
        """Test stability with single fold (edge case)."""
        importance_matrix = np.array([[0.4, 0.3, 0.3]])
        feature_names = ['f1', 'f2', 'f3']

        result = provider.execute(None, importance_matrix, None, feature_names)

        assert result['n_folds'] == 1
        for feature in feature_names:
            assert result['stability_metrics'][feature]['std_deviation'] == 0.0

    def test_stability_dataframe_input(self, provider):
        """Test stability with DataFrame input."""
        importance_df = pd.DataFrame({
            'feature_a': [0.5, 0.48, 0.52],
            'feature_b': [0.3, 0.32, 0.28],
            'feature_c': [0.2, 0.2, 0.2]
        })
        feature_names = ['feature_a', 'feature_b', 'feature_c']

        result = provider.execute(None, importance_df, None, feature_names)

        assert 'stability_metrics' in result
        assert len(result['stability_metrics']) == 3
