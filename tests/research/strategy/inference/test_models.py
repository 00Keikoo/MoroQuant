"""Tests for inference domain models - Sprint 3.9B-4A

Validates immutability and validation rules.
"""

import pytest
from dataclasses import FrozenInstanceError
from ml_service.research.strategy.inference.models import (
    Prediction,
    ModelMetadata,
    InferenceResult,
)


class TestPredictionImmutability:
    """Verify Prediction immutability following ADR-024."""

    def test_prediction_is_frozen(self):
        prediction = Prediction(
            timestamp="2024-01-01T00:00:00Z",
            model_version_id="BTCUSD_v1.0.0",
            direction="LONG",
            probability=0.75
        )

        with pytest.raises(FrozenInstanceError):
            prediction.probability = 0.5

    def test_prediction_requires_timestamp(self):
        with pytest.raises(ValueError, match="timestamp cannot be empty"):
            Prediction(
                timestamp="",
                model_version_id="BTCUSD_v1.0.0",
                direction="LONG",
                probability=0.75
            )

    def test_prediction_requires_model_version_id(self):
        with pytest.raises(ValueError, match="model_version_id cannot be empty"):
            Prediction(
                timestamp="2024-01-01T00:00:00Z",
                model_version_id="",
                direction="LONG",
                probability=0.75
            )

    def test_prediction_probability_bounds(self):
        with pytest.raises(ValueError, match="probability must be between 0.0 and 1.0"):
            Prediction(
                timestamp="2024-01-01T00:00:00Z",
                model_version_id="BTCUSD_v1.0.0",
                direction="LONG",
                probability=1.5
            )

        with pytest.raises(ValueError, match="probability must be between 0.0 and 1.0"):
            Prediction(
                timestamp="2024-01-01T00:00:00Z",
                model_version_id="BTCUSD_v1.0.0",
                direction="LONG",
                probability=-0.1
            )

    def test_prediction_to_dict(self):
        prediction = Prediction(
            timestamp="2024-01-01T00:00:00Z",
            model_version_id="BTCUSD_v1.0.0",
            direction="LONG",
            probability=0.75,
            outputs=(("class_0", 0.25), ("class_1", 0.75))
        )

        result = prediction.to_dict()
        assert result["timestamp"] == "2024-01-01T00:00:00Z"
        assert result["model_version_id"] == "BTCUSD_v1.0.0"
        assert result["direction"] == "LONG"
        assert result["probability"] == 0.75
        assert result["outputs"] == [["class_0", 0.25], ["class_1", 0.75]]


class TestModelMetadataImmutability:
    """Verify ModelMetadata immutability following ADR-024."""

    def test_model_metadata_is_frozen(self):
        metadata = ModelMetadata(
            model_id="BTCUSD_direction",
            model_version_id="BTCUSD_direction_v1.0.0",
            framework="xgboost",
            feature_schema=("feature_1", "feature_2"),
            fingerprint="abc123"
        )

        with pytest.raises(FrozenInstanceError):
            metadata.framework = "lightgbm"

    def test_model_metadata_requires_all_fields(self):
        with pytest.raises(ValueError, match="model_id cannot be empty"):
            ModelMetadata(
                model_id="",
                model_version_id="BTCUSD_direction_v1.0.0",
                framework="xgboost",
                feature_schema=("feature_1",),
                fingerprint="abc123"
            )

        with pytest.raises(ValueError, match="model_version_id cannot be empty"):
            ModelMetadata(
                model_id="BTCUSD_direction",
                model_version_id="",
                framework="xgboost",
                feature_schema=("feature_1",),
                fingerprint="abc123"
            )

        with pytest.raises(ValueError, match="framework cannot be empty"):
            ModelMetadata(
                model_id="BTCUSD_direction",
                model_version_id="BTCUSD_direction_v1.0.0",
                framework="",
                feature_schema=("feature_1",),
                fingerprint="abc123"
            )

        with pytest.raises(ValueError, match="feature_schema cannot be empty"):
            ModelMetadata(
                model_id="BTCUSD_direction",
                model_version_id="BTCUSD_direction_v1.0.0",
                framework="xgboost",
                feature_schema=tuple(),
                fingerprint="abc123"
            )


class TestInferenceResultImmutability:
    """Verify InferenceResult immutability following ADR-024."""

    def test_inference_result_is_frozen(self):
        prediction = Prediction(
            timestamp="2024-01-01T00:00:00Z",
            model_version_id="BTCUSD_v1.0.0",
            direction="LONG",
            probability=0.75
        )

        metadata = ModelMetadata(
            model_id="BTCUSD_direction",
            model_version_id="BTCUSD_direction_v1.0.0",
            framework="xgboost",
            feature_schema=("feature_1", "feature_2"),
            fingerprint="abc123"
        )

        result = InferenceResult(
            prediction=prediction,
            metadata=metadata,
            executed_at="2024-01-01T00:00:00.123Z",
            latency_ms=10.5
        )

        with pytest.raises(FrozenInstanceError):
            result.latency_ms = 20.0

    def test_inference_result_type_validation(self):
        metadata = ModelMetadata(
            model_id="BTCUSD_direction",
            model_version_id="BTCUSD_direction_v1.0.0",
            framework="xgboost",
            feature_schema=("feature_1",),
            fingerprint="abc123"
        )

        with pytest.raises(TypeError, match="prediction must be a Prediction instance"):
            InferenceResult(
                prediction="not a prediction",
                metadata=metadata,
                executed_at="2024-01-01T00:00:00Z",
                latency_ms=10.0
            )

    def test_inference_result_latency_validation(self):
        prediction = Prediction(
            timestamp="2024-01-01T00:00:00Z",
            model_version_id="BTCUSD_v1.0.0",
            direction="LONG",
            probability=0.75
        )

        metadata = ModelMetadata(
            model_id="BTCUSD_direction",
            model_version_id="BTCUSD_direction_v1.0.0",
            framework="xgboost",
            feature_schema=("feature_1",),
            fingerprint="abc123"
        )

        with pytest.raises(ValueError, match="latency_ms cannot be negative"):
            InferenceResult(
                prediction=prediction,
                metadata=metadata,
                executed_at="2024-01-01T00:00:00Z",
                latency_ms=-5.0
            )
