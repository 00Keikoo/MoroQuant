"""Tests for feature schema validator - Sprint 3.9B-4A

Validates schema compatibility checking between model and runtime features.
"""

import pytest
import math
from ml_service.research.strategy.models import FeatureSnapshot
from ml_service.research.strategy.inference.validator import (
    FeatureSchemaValidator,
    FeatureSchemaMismatchError,
)


class TestFeatureSchemaValidator:
    """Verify feature schema validation catches all mismatch scenarios."""

    def test_correct_schema_passes(self):
        """Valid schema with matching features passes validation."""
        snapshot = FeatureSnapshot(
            timestamp="2024-01-01T00:00:00Z",
            features=(
                ("feature_1", 1.0),
                ("feature_2", 2.0),
                ("feature_3", 3.0),
            )
        )
        model_schema = ("feature_1", "feature_2", "feature_3")

        # Should not raise
        FeatureSchemaValidator.validate(model_schema, snapshot)

    def test_missing_feature_rejected(self):
        """Model expects 49 features, runtime provides 33 - historical MoroQuant issue."""
        snapshot = FeatureSnapshot(
            timestamp="2024-01-01T00:00:00Z",
            features=(
                ("feature_1", 1.0),
                ("feature_2", 2.0),
            )
        )
        model_schema = ("feature_1", "feature_2", "feature_3")

        with pytest.raises(FeatureSchemaMismatchError, match="Missing features"):
            FeatureSchemaValidator.validate(model_schema, snapshot)

    def test_extra_feature_rejected(self):
        """Runtime provides features not in model schema."""
        snapshot = FeatureSnapshot(
            timestamp="2024-01-01T00:00:00Z",
            features=(
                ("feature_1", 1.0),
                ("feature_2", 2.0),
                ("feature_3", 3.0),
                ("feature_4", 4.0),
            )
        )
        model_schema = ("feature_1", "feature_2", "feature_3")

        with pytest.raises(FeatureSchemaMismatchError, match="Unexpected features"):
            FeatureSchemaValidator.validate(model_schema, snapshot)

    def test_ordering_mismatch_rejected(self):
        """Features present but in wrong order."""
        snapshot = FeatureSnapshot(
            timestamp="2024-01-01T00:00:00Z",
            features=(
                ("feature_2", 2.0),
                ("feature_1", 1.0),
                ("feature_3", 3.0),
            )
        )
        model_schema = ("feature_1", "feature_2", "feature_3")

        with pytest.raises(FeatureSchemaMismatchError, match="ordering mismatch"):
            FeatureSchemaValidator.validate(model_schema, snapshot)

    def test_nan_value_rejected(self):
        """NaN values in features are rejected."""
        snapshot = FeatureSnapshot(
            timestamp="2024-01-01T00:00:00Z",
            features=(
                ("feature_1", 1.0),
                ("feature_2", math.nan),
                ("feature_3", 3.0),
            )
        )
        model_schema = ("feature_1", "feature_2", "feature_3")

        with pytest.raises(FeatureSchemaMismatchError, match="Invalid value"):
            FeatureSchemaValidator.validate(model_schema, snapshot)

    def test_inf_value_rejected(self):
        """Inf values in features are rejected."""
        snapshot = FeatureSnapshot(
            timestamp="2024-01-01T00:00:00Z",
            features=(
                ("feature_1", 1.0),
                ("feature_2", math.inf),
                ("feature_3", 3.0),
            )
        )
        model_schema = ("feature_1", "feature_2", "feature_3")

        with pytest.raises(FeatureSchemaMismatchError, match="Invalid value"):
            FeatureSchemaValidator.validate(model_schema, snapshot)

    def test_empty_model_schema_rejected(self):
        """Empty model schema is invalid."""
        snapshot = FeatureSnapshot(
            timestamp="2024-01-01T00:00:00Z",
            features=(("feature_1", 1.0),)
        )
        model_schema = tuple()

        with pytest.raises(FeatureSchemaMismatchError, match="Model schema cannot be empty"):
            FeatureSchemaValidator.validate(model_schema, snapshot)

    def test_large_feature_count(self):
        """Validate with 49 features as per historical requirement."""
        features = tuple((f"feature_{i}", float(i)) for i in range(49))
        snapshot = FeatureSnapshot(
            timestamp="2024-01-01T00:00:00Z",
            features=features
        )
        model_schema = tuple(f"feature_{i}" for i in range(49))

        # Should not raise
        FeatureSchemaValidator.validate(model_schema, snapshot)
