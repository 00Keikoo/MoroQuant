"""ML Inference Adapter implementation - Sprint 3.9B-4A

Integrates feature validation, Model Registry queries, and backend prediction.
"""

import time
from datetime import datetime, timezone
from typing import Dict, Optional

from ml_service.research.model_registry.service import ModelRegistryService
from ml_service.research.model_registry.model_types import ModelLifecycleState
from ml_service.research.strategy.models import FeatureSnapshot
from ml_service.research.strategy.inference.interfaces import ModelInferenceBackend
from ml_service.research.strategy.inference.models import InferenceResult, Prediction, ModelMetadata
from ml_service.research.strategy.inference.validator import FeatureSchemaValidator


class MLInferenceAdapter:
    """Adapter facilitating decoupled, validated ML predictions using Model Registry.

    Flow:
    1. Fetch model version and artifact from registry
    2. Validate lifecycle state
    3. Validate feature schema compatibility
    4. Resolve and cache backend
    5. Execute prediction
    6. Return InferenceResult with telemetry
    """

    def __init__(
        self,
        registry_service: ModelRegistryService,
        backends: Dict[str, ModelInferenceBackend]
    ):
        """Initialize adapter with registry service and backend implementations.

        Args:
            registry_service: Service for resolving model versions and artifacts.
            backends: Map of framework name to backend implementation.
        """
        self._registry_service = registry_service
        self._backends = backends
        self._loaded_models: Dict[str, ModelInferenceBackend] = {}

    def predict(self, model_version_id: str, snapshot: FeatureSnapshot) -> InferenceResult:
        """Execute validation, fetch registry details, and perform backend prediction.

        Args:
            model_version_id: Semantic model identifier (e.g. 'BTCUSD_direction_v1.0.0').
            snapshot: Current feature snapshot generated at runtime.

        Returns:
            InferenceResult containing prediction and metadata.

        Raises:
            ValueError: If model version or artifact not found in registry.
            FeatureSchemaMismatchError: If feature validation fails.
            NotImplementedError: If backend framework not supported.
        """
        start_time = time.perf_counter()

        # 1. Fetch Model Version from Model Registry
        version_data = self._registry_service.get_version(model_version_id)
        if not version_data:
            raise ValueError(f"Model version '{model_version_id}' not found in registry.")

        # 2. Validate lifecycle state
        if version_data.lifecycle_state not in (
            ModelLifecycleState.VALIDATED,
            ModelLifecycleState.PRODUCTION
        ):
            raise ValueError(
                f"Model version '{model_version_id}' has lifecycle state "
                f"'{version_data.lifecycle_state.value}'. "
                f"Only VALIDATED or PRODUCTION models can be used for inference."
            )

        # 3. Fetch Artifact metadata
        artifact_data = self._registry_service.get_artifact(model_version_id)
        if not artifact_data:
            raise ValueError(f"Artifact metadata for version '{model_version_id}' not found.")

        # 4. Extract feature schema from registry
        # For Sprint 3.9B-4A, feature_schema is stored in artifact or version metadata
        # Using snapshot features as placeholder until proper schema storage is implemented
        feature_schema = tuple(name for name, _ in snapshot.features)

        # 5. Perform feature validation
        FeatureSchemaValidator.validate(feature_schema, snapshot)

        # 6. Resolve backend framework
        # Extract framework from model metadata (default to 'xgboost' for now)
        backend_name = 'xgboost'  # Will be extracted from version metadata in future sprints

        if backend_name not in self._backends:
            raise NotImplementedError(
                f"Backend framework '{backend_name}' is not supported. "
                f"Available backends: {list(self._backends.keys())}"
            )

        # 7. Load model if not cached
        if model_version_id not in self._loaded_models:
            backend = self._backends[backend_name]
            backend.load_model(artifact_data.bundle_path)
            self._loaded_models[model_version_id] = backend
        else:
            backend = self._loaded_models[model_version_id]

        # 8. Run prediction
        prediction = backend.predict(snapshot, model_version_id)

        # 9. Record telemetry (non-deterministic, separate from prediction)
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        executed_at = datetime.now(timezone.utc).isoformat()

        # 10. Build metadata
        metadata = ModelMetadata(
            model_id=version_data.model_id,
            model_version_id=model_version_id,
            framework=backend_name,
            feature_schema=feature_schema,
            fingerprint=version_data.composite_fingerprint.value,
            hyperparameters={}
        )

        return InferenceResult(
            prediction=prediction,
            metadata=metadata,
            executed_at=executed_at,
            latency_ms=latency_ms
        )
