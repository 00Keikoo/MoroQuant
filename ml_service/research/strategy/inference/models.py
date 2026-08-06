"""Domain models for ML Inference - Sprint 3.9B-4A

Immutable inference domain objects following ADR-024.
No runtime timestamps in deterministic output.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Tuple


@dataclass(frozen=True)
class Prediction:
    """Immutable prediction output.

    Uses FeatureSnapshot.timestamp as event time for deterministic replay.
    Does NOT include runtime execution timestamps.
    """
    timestamp: str
    model_version_id: str
    direction: str
    probability: float
    outputs: Tuple[Tuple[str, float], ...] = field(default_factory=tuple)

    def __post_init__(self):
        if not self.timestamp:
            raise ValueError("timestamp cannot be empty")
        if not self.model_version_id:
            raise ValueError("model_version_id cannot be empty")
        if not (0.0 <= self.probability <= 1.0):
            raise ValueError(f"probability must be between 0.0 and 1.0, got {self.probability}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "model_version_id": self.model_version_id,
            "direction": self.direction,
            "probability": self.probability,
            "outputs": [list(x) for x in self.outputs]
        }


@dataclass(frozen=True)
class ModelMetadata:
    """Immutable model execution metadata."""
    model_id: str
    model_version_id: str
    framework: str
    feature_schema: Tuple[str, ...]
    fingerprint: str
    hyperparameters: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.model_id:
            raise ValueError("model_id cannot be empty")
        if not self.model_version_id:
            raise ValueError("model_version_id cannot be empty")
        if not self.framework:
            raise ValueError("framework cannot be empty")
        if not self.feature_schema:
            raise ValueError("feature_schema cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_version_id": self.model_version_id,
            "framework": self.framework,
            "feature_schema": list(self.feature_schema),
            "fingerprint": self.fingerprint,
            "hyperparameters": self.hyperparameters,
        }


@dataclass(frozen=True)
class InferenceResult:
    """Consolidated immutable container returned after inference execution.

    Separates deterministic inference (prediction) from telemetry (executed_at, latency_ms).
    """
    prediction: Prediction
    metadata: ModelMetadata
    executed_at: str
    latency_ms: float

    def __post_init__(self):
        if not isinstance(self.prediction, Prediction):
            raise TypeError("prediction must be a Prediction instance")
        if not isinstance(self.metadata, ModelMetadata):
            raise TypeError("metadata must be a ModelMetadata instance")
        if self.latency_ms < 0:
            raise ValueError("latency_ms cannot be negative")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction": self.prediction.to_dict(),
            "metadata": self.metadata.to_dict(),
            "executed_at": self.executed_at,
            "latency_ms": self.latency_ms,
        }
