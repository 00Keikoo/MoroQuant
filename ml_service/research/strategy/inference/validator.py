"""Feature Schema Validation - Sprint 3.9B-4A

Validates FeatureSnapshot alignment against Model Metadata feature schemas.
Solves historical MoroQuant issue: Model expected 49 features, runtime provided 33.
"""

from typing import Tuple, Set
import math
from ml_service.research.strategy.models import FeatureSnapshot


class FeatureSchemaMismatchError(Exception):
    """Raised when runtime features do not match trained model expectations."""
    pass


class FeatureSchemaValidator:
    """Validates FeatureSnapshot alignment against Model Metadata feature schemas."""

    @staticmethod
    def validate(model_schema: Tuple[str, ...], snapshot: FeatureSnapshot) -> None:
        """Compares required features against FeatureSnapshot features.

        Args:
            model_schema: Sequence of feature names required by model in exact order.
            snapshot: FeatureSnapshot generated at strategy runtime.

        Raises:
            FeatureSchemaMismatchError: If there is any mismatch in count, name, or indices.
        """
        if not model_schema:
            raise FeatureSchemaMismatchError("Model schema cannot be empty.")

        runtime_features: Set[str] = {name for name, _ in snapshot.features}
        model_features_set: Set[str] = set(model_schema)

        # 1. Check for missing features
        missing_features = model_features_set - runtime_features
        if missing_features:
            raise FeatureSchemaMismatchError(
                f"Missing features in FeatureSnapshot. "
                f"Model expected {len(model_schema)} features, "
                f"but FeatureSnapshot has {len(runtime_features)} features. "
                f"Missing: {sorted(list(missing_features))}"
            )

        # 2. Check for unexpected extra features
        extra_features = runtime_features - model_features_set
        if extra_features:
            raise FeatureSchemaMismatchError(
                f"Unexpected features in FeatureSnapshot. "
                f"Model expected {len(model_schema)} features, "
                f"but FeatureSnapshot has {len(runtime_features)} features. "
                f"Extra: {sorted(list(extra_features))}"
            )

        # 3. Check for NaN/Inf values
        snapshot_dict = dict(snapshot.features)
        for feature_name in model_schema:
            value = snapshot_dict[feature_name]
            if math.isnan(value) or math.isinf(value):
                raise FeatureSchemaMismatchError(
                    f"Invalid value for feature '{feature_name}': {value}. "
                    f"NaN and Inf values are not allowed."
                )

        # 4. Verify ordering matches model expectations
        snapshot_names = [name for name, _ in snapshot.features]
        for i, expected_name in enumerate(model_schema):
            if i >= len(snapshot_names) or snapshot_names[i] != expected_name:
                raise FeatureSchemaMismatchError(
                    f"Feature ordering mismatch at index {i}. "
                    f"Expected '{expected_name}' but found "
                    f"'{snapshot_names[i] if i < len(snapshot_names) else 'MISSING'}'. "
                    f"Model requires features in exact order."
                )
