"""Base class and interface contract for diagnostic providers."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import time
import logging

logger = logging.getLogger(__name__)


class BaseDiagnosticProvider(ABC):
    """Abstract contract for all Explainability providers."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize provider with configuration.

        Args:
            config: Provider-specific configuration parameters
        """
        self.config = config
        self._execution_time: float = 0.0

    @abstractmethod
    def execute(
        self,
        model: Any,
        X: Any,
        y: Any,
        feature_names: List[str]
    ) -> Dict[str, Any]:
        """Execute the explainability provider computation.

        Args:
            model: The trained model binary wrapper object
            X: Matrix of features (pandas.DataFrame or numpy.ndarray)
            y: Vector of targets (pandas.Series or numpy.ndarray)
            feature_names: List of column names mapping to index order

        Returns:
            Dict containing output metrics/matrices

        Raises:
            ValueError: If inputs are invalid or incompatible
            RuntimeError: If computation fails
        """
        pass

    def execute_with_telemetry(
        self,
        model: Any,
        X: Any,
        y: Any,
        feature_names: List[str]
    ) -> Dict[str, Any]:
        """Execute with timing and error handling wrapper.

        Args:
            model: The trained model binary wrapper object
            X: Matrix of features (pandas.DataFrame or numpy.ndarray)
            y: Vector of targets (pandas.Series or numpy.ndarray)
            feature_names: List of column names mapping to index order

        Returns:
            Dict containing output metrics/matrices and telemetry
        """
        start_time = time.time()

        try:
            result = self.execute(model, X, y, feature_names)
            self._execution_time = time.time() - start_time

            logger.info(
                f"{self.__class__.__name__} completed in "
                f"{self._execution_time:.2f}s"
            )

            return result

        except Exception as e:
            self._execution_time = time.time() - start_time
            logger.error(
                f"{self.__class__.__name__} failed after "
                f"{self._execution_time:.2f}s: {str(e)}"
            )
            raise

    @property
    def execution_time(self) -> float:
        """Get last execution time in seconds."""
        return self._execution_time

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return self.__class__.__name__
