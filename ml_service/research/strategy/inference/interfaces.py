"""Abstract contracts for ML Inference Backends - Sprint 3.9B-4A

Backend interface decouples inference adapter from framework implementations.
"""

from abc import ABC, abstractmethod
from ml_service.research.strategy.models import FeatureSnapshot
from ml_service.research.strategy.inference.models import Prediction


class ModelInferenceBackend(ABC):
    """Abstract contract for model execution engines.

    Implementations: XGBoost, LightGBM, PyTorch, ONNX, etc.
    """

    @abstractmethod
    def load_model(self, bundle_path: str) -> None:
        """Load and initialize model weights from artifact store bundle.

        Args:
            bundle_path: Path to model registry's locked bundle directory.
        """
        pass

    @abstractmethod
    def predict(self, features: FeatureSnapshot, model_version_id: str) -> Prediction:
        """Run inference over features snapshot.

        Args:
            features: FeatureSnapshot containing inputs.
            model_version_id: Active model version identifier.

        Returns:
            Immutable Prediction domain object.
        """
        pass
