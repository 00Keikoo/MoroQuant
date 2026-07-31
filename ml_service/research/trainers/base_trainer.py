"""Base Trainer Abstraction Layer for MoroQuant Research Platform."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple


@dataclass(frozen=True)
class TrainerConfig:
    """Immutable configuration for initializing/running a trainer."""
    model_type: str
    seed: int
    hyperparameters: Tuple[Tuple[str, Any], ...] = field(default_factory=tuple)
    training_parameters: Tuple[Tuple[str, Any], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TrainingMetrics:
    """Immutable metrics collected during training and evaluation."""
    loss_history: Tuple[float, ...]
    val_loss_history: Tuple[float, ...]
    sharpe: float
    ece: float
    brier: float
    drawdown: float


@dataclass(frozen=True)
class ArtifactMetadata:
    """Immutable metadata representing generated model artifacts."""
    checksum: str
    file_path: str
    size_bytes: int
    permissions: str


@dataclass(frozen=True)
class TrainingResult:
    """Immutable result combining status, metrics, and artifact metadata."""
    status: str  # e.g., SUCCESS, FAILED_TRAINING, CANCELLED, etc.
    metrics: TrainingMetrics
    artifacts: ArtifactMetadata
    error_message: Optional[str] = None


class BaseTrainer(ABC):
    """
    Abstract Base Class defining the contract for model trainers.
    All trainers (XGBoost, LightGBM, Neural Networks) must subclass this.
    """

    @abstractmethod
    def validate(self, dataset: Any, features: Any, config: TrainerConfig) -> None:
        """
        Validate inputs and configuration before starting the training process.
        Raises ValueError or TypeError if validation fails.
        """
        pass

    @abstractmethod
    def train(self, dataset: Any, features: Any, config: TrainerConfig) -> None:
        """
        Execute the primary model fitting process.
        """
        pass

    @abstractmethod
    def evaluate(self, dataset: Any) -> TrainingMetrics:
        """
        Evaluate the fitted model on validation or out-of-sample data.
        Returns the computed TrainingMetrics.
        """
        pass

    @abstractmethod
    def collect_metrics(self) -> TrainingMetrics:
        """
        Collect training history and final evaluation metrics.
        Returns the computed TrainingMetrics.
        """
        pass

    @abstractmethod
    def generate_artifact(self) -> ArtifactMetadata:
        """
        Serialize model weights and parameters to a deterministic artifact payload.
        Returns the generated ArtifactMetadata.
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """
        Release hardware resources (GPU/TPU) and sweep temporary files from memory/disk.
        """
        pass

    def prepare(self, dataset: Any, features: Any, config: TrainerConfig, run: Any = None) -> None:
        """
        Prepare the trainer by validating inputs and configuration.
        Subclasses can override this to perform additional setup.
        """
        self.validate(dataset, features, config)

    def save_artifacts(self) -> ArtifactMetadata:
        """
        Serialize and return generated model artifacts.
        Subclasses can override this to perform custom serialization.
        """
        return self.generate_artifact()

