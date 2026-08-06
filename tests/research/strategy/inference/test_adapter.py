"""Tests for ML Inference Adapter - Sprint 3.9B-4A

Validates adapter integration with registry, validation, and backends.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from ml_service.research.model_registry.service import ModelRegistryService
from ml_service.research.model_registry.model_types import (
    ModelVersion,
    ArtifactMetadata,
    Model,
    ModelLifecycleState,
    CompositeFingerprint,
)
from ml_service.research.strategy.models import FeatureSnapshot
from ml_service.research.strategy.inference.adapter import MLInferenceAdapter
from ml_service.research.strategy.inference.interfaces import ModelInferenceBackend
from ml_service.research.strategy.inference.models import Prediction


class MockBackend(ModelInferenceBackend):
    """Mock backend for testing."""

    def __init__(self):
        self.loaded_path = None
        self.predict_calls = []

    def load_model(self, bundle_path: str) -> None:
        self.loaded_path = bundle_path

    def predict(self, features: FeatureSnapshot, model_version_id: str) -> Prediction:
        self.predict_calls.append((features, model_version_id))
        return Prediction(
            timestamp=features.timestamp,
            model_version_id=model_version_id,
            direction="LONG",
            probability=0.75
        )


class TestMLInferenceAdapter:
    """Verify adapter integration and workflow."""

    def test_deterministic_prediction(self):
        """Same FeatureSnapshot produces identical prediction."""
        registry_service = Mock(spec=ModelRegistryService)
        backend = MockBackend()

        adapter = MLInferenceAdapter(
            registry_service=registry_service,
            backends={"xgboost": backend}
        )

        # Mock registry responses
        version = ModelVersion(
            model_version_id="BTCUSD_v1.0.0",
            model_id="BTCUSD",
            version="1.0.0",
            lifecycle_state=ModelLifecycleState.PRODUCTION,
            composite_fingerprint=CompositeFingerprint("a" * 64),
            created_at=datetime.now()
        )

        artifact = ArtifactMetadata(
            model_version_id="BTCUSD_v1.0.0",
            bundle_path="/path/to/bundle",
            manifest_checksum="b" * 64,
            size_bytes=1000,
            permissions="444",
            is_frozen=True
        )

        registry_service.get_version.return_value = version
        registry_service.get_artifact.return_value = artifact

        snapshot = FeatureSnapshot(
            timestamp="2024-01-01T00:00:00Z",
            features=(
                ("feature_1", 1.0),
                ("feature_2", 2.0),
            )
        )

        # First prediction
        result1 = adapter.predict("BTCUSD_v1.0.0", snapshot)

        # Second prediction with same snapshot
        result2 = adapter.predict("BTCUSD_v1.0.0", snapshot)

        # Predictions should be identical (deterministic)
        assert result1.prediction.probability == result2.prediction.probability
        assert result1.prediction.direction == result2.prediction.direction
        assert result1.prediction.timestamp == result2.prediction.timestamp

    def test_model_version_not_found(self):
        """Adapter rejects unknown model version."""
        registry_service = Mock(spec=ModelRegistryService)
        registry_service.get_version.return_value = None

        backend = MockBackend()
        adapter = MLInferenceAdapter(
            registry_service=registry_service,
            backends={"xgboost": backend}
        )

        snapshot = FeatureSnapshot(
            timestamp="2024-01-01T00:00:00Z",
            features=(("feature_1", 1.0),)
        )

        with pytest.raises(ValueError, match="not found in registry"):
            adapter.predict("UNKNOWN_v1.0.0", snapshot)

    def test_invalid_lifecycle_state_rejected(self):
        """Adapter rejects DRAFT and CANDIDATE models."""
        registry_service = Mock(spec=ModelRegistryService)
        backend = MockBackend()

        adapter = MLInferenceAdapter(
            registry_service=registry_service,
            backends={"xgboost": backend}
        )

        version = ModelVersion(
            model_version_id="BTCUSD_v1.0.0",
            model_id="BTCUSD",
            version="1.0.0",
            lifecycle_state=ModelLifecycleState.DRAFT,
            composite_fingerprint=CompositeFingerprint("a" * 64),
            created_at=datetime.now()
        )

        registry_service.get_version.return_value = version

        snapshot = FeatureSnapshot(
            timestamp="2024-01-01T00:00:00Z",
            features=(("feature_1", 1.0),)
        )

        with pytest.raises(ValueError, match="lifecycle state"):
            adapter.predict("BTCUSD_v1.0.0", snapshot)

    def test_backend_selection(self):
        """Adapter resolves correct backend by framework."""
        registry_service = Mock(spec=ModelRegistryService)
        xgboost_backend = MockBackend()
        lightgbm_backend = MockBackend()

        adapter = MLInferenceAdapter(
            registry_service=registry_service,
            backends={
                "xgboost": xgboost_backend,
                "lightgbm": lightgbm_backend
            }
        )

        version = ModelVersion(
            model_version_id="BTCUSD_v1.0.0",
            model_id="BTCUSD",
            version="1.0.0",
            lifecycle_state=ModelLifecycleState.PRODUCTION,
            composite_fingerprint=CompositeFingerprint("a" * 64),
            created_at=datetime.now()
        )

        artifact = ArtifactMetadata(
            model_version_id="BTCUSD_v1.0.0",
            bundle_path="/path/to/bundle",
            manifest_checksum="b" * 64,
            size_bytes=1000,
            permissions="444"
        )

        registry_service.get_version.return_value = version
        registry_service.get_artifact.return_value = artifact

        snapshot = FeatureSnapshot(
            timestamp="2024-01-01T00:00:00Z",
            features=(("feature_1", 1.0),)
        )

        result = adapter.predict("BTCUSD_v1.0.0", snapshot)

        # Should use xgboost backend (default)
        assert xgboost_backend.loaded_path == "/path/to/bundle"
        assert len(xgboost_backend.predict_calls) == 1

    def test_backend_caching(self):
        """Adapter caches loaded models."""
        registry_service = Mock(spec=ModelRegistryService)
        backend = MockBackend()

        adapter = MLInferenceAdapter(
            registry_service=registry_service,
            backends={"xgboost": backend}
        )

        version = ModelVersion(
            model_version_id="BTCUSD_v1.0.0",
            model_id="BTCUSD",
            version="1.0.0",
            lifecycle_state=ModelLifecycleState.PRODUCTION,
            composite_fingerprint=CompositeFingerprint("a" * 64),
            created_at=datetime.now()
        )

        artifact = ArtifactMetadata(
            model_version_id="BTCUSD_v1.0.0",
            bundle_path="/path/to/bundle",
            manifest_checksum="b" * 64,
            size_bytes=1000,
            permissions="444"
        )

        registry_service.get_version.return_value = version
        registry_service.get_artifact.return_value = artifact

        snapshot = FeatureSnapshot(
            timestamp="2024-01-01T00:00:00Z",
            features=(("feature_1", 1.0),)
        )

        # First prediction - loads model
        adapter.predict("BTCUSD_v1.0.0", snapshot)
        first_load_path = backend.loaded_path

        # Second prediction - uses cached model
        backend.loaded_path = None
        adapter.predict("BTCUSD_v1.0.0", snapshot)

        # Model not reloaded
        assert backend.loaded_path is None
        assert len(backend.predict_calls) == 2


class TestAdapterIsolation:
    """Verify ADR-024 isolation constraints."""

    def test_no_portfolio_imports(self):
        """Adapter does not import portfolio or execution modules."""
        import ml_service.research.strategy.inference.adapter as adapter_module

        module_source = adapter_module.__file__
        with open(module_source, 'r') as f:
            source = f.read()

        # Verify no forbidden imports
        forbidden = [
            "from ml_service.portfolio",
            "import ml_service.portfolio",
            "from ml_service.simulation.execution",
            "import ml_service.simulation.execution",
        ]

        for forbidden_import in forbidden:
            assert forbidden_import not in source, \
                f"Adapter must not import portfolio/execution: {forbidden_import}"

    def test_no_database_writes(self):
        """Adapter does not perform database writes."""
        import ml_service.research.strategy.inference.adapter as adapter_module

        module_source = adapter_module.__file__
        with open(module_source, 'r') as f:
            source = f.read()

        # Verify no database write operations
        forbidden = [
            ".commit(",
            ".execute(",
            "INSERT INTO",
            "UPDATE ",
            "DELETE FROM",
        ]

        for forbidden_op in forbidden:
            assert forbidden_op not in source, \
                f"Adapter must not write to database: {forbidden_op}"
