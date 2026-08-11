"""Model Lifecycle Interfaces - Sprint 3.9D-7

Abstract interfaces for model lifecycle management.
ADR-024 compliant: research layer only, no database, no execution dependencies.
"""

from abc import ABC, abstractmethod
from ml_service.research.model_identity.models import ModelIdentity
from ml_service.research.model_lifecycle.models import LifecycleState, ModelLifecycleRecord


class LifecycleManager(ABC):
    """Abstract interface for model lifecycle state management.

    Provides deterministic evaluation and transition logic for model artifacts
    through their lifecycle stages.
    """

    @abstractmethod
    def evaluate(self, model: ModelIdentity) -> ModelLifecycleRecord:
        """Evaluate model and determine appropriate lifecycle state.

        Args:
            model: ModelIdentity to evaluate

        Returns:
            ModelLifecycleRecord with determined state
        """
        pass

    @abstractmethod
    def transition(
        self,
        model: ModelIdentity,
        target_state: LifecycleState
    ) -> ModelLifecycleRecord:
        """Attempt to transition model to target state.

        Args:
            model: ModelIdentity to transition
            target_state: Desired lifecycle state

        Returns:
            ModelLifecycleRecord documenting the transition

        Raises:
            ValueError: If transition is not allowed
        """
        pass

    @abstractmethod
    def validate_transition(
        self,
        model: ModelIdentity,
        current_state: LifecycleState,
        target_state: LifecycleState
    ) -> tuple[bool, str]:
        """Validate if transition is allowed.

        Args:
            model: ModelIdentity to check
            current_state: Current lifecycle state
            target_state: Desired lifecycle state

        Returns:
            (is_valid, reason) tuple
        """
        pass
