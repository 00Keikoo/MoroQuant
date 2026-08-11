"""Model Lifecycle Manager - Sprint 3.9D-7

Deterministic lifecycle state evaluation and transition management.
ADR-024 compliant: research layer only, no database, no execution dependencies.
"""

from datetime import datetime, UTC
from ml_service.research.model_identity.models import ModelIdentity
from ml_service.research.model_lifecycle.interfaces import LifecycleManager as ILifecycleManager
from ml_service.research.model_lifecycle.models import LifecycleState, ModelLifecycleRecord
from ml_service.research.model_lifecycle.policy import LifecyclePolicy


class LifecycleManager(ILifecycleManager):
    """Concrete implementation of model lifecycle state management.

    Provides deterministic evaluation and transition logic based on LifecyclePolicy.
    All operations are stateless and produce immutable records.
    """

    def evaluate(self, model: ModelIdentity) -> ModelLifecycleRecord:
        """Evaluate model and determine appropriate lifecycle state.

        Determines the highest state the model can reach based on its properties
        and asset class.

        Args:
            model: ModelIdentity to evaluate

        Returns:
            ModelLifecycleRecord with determined state
        """
        current_state = self._parse_lifecycle_status(model.lifecycle_status)

        if model.asset_class.lower() == "proxy":
            target_state = self._evaluate_proxy_model(model, current_state)
        elif model.asset_class.lower() == "crypto":
            target_state = self._evaluate_crypto_model(model, current_state)
        else:
            target_state = LifecycleState.DISCOVERED
            reason = f"unknown asset class: {model.asset_class}"
            return self._create_record(model, target_state, current_state, reason)

        return self._create_record(model, target_state, current_state, "evaluation complete")

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
        current_state = self._parse_lifecycle_status(model.lifecycle_status)

        is_valid, reason = self.validate_transition(model, current_state, target_state)

        if not is_valid:
            raise ValueError(f"Invalid transition: {reason}")

        return self._create_record(model, target_state, current_state, reason)

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
        return LifecyclePolicy.can_evaluate_transition(model, current_state, target_state)

    def _evaluate_crypto_model(self, model: ModelIdentity, current_state: LifecycleState) -> LifecycleState:
        """Evaluate crypto model to determine highest achievable state.

        Args:
            model: ModelIdentity to evaluate
            current_state: Current lifecycle state

        Returns:
            Highest achievable LifecycleState
        """
        if not model.validation_available:
            return LifecycleState.DISCOVERED

        if not model.calibration_available:
            return LifecycleState.VALIDATED

        return LifecycleState.GOVERNANCE_READY

    def _evaluate_proxy_model(self, model: ModelIdentity, current_state: LifecycleState) -> LifecycleState:
        """Evaluate proxy model to determine highest achievable state.

        Proxy models are blocked from APPROVED and PRODUCTION states.

        Args:
            model: ModelIdentity to evaluate
            current_state: Current lifecycle state

        Returns:
            Highest achievable LifecycleState
        """
        if not model.validation_available:
            return LifecycleState.DISCOVERED

        if not model.calibration_available:
            return LifecycleState.VALIDATED

        return LifecycleState.GOVERNANCE_READY

    def _parse_lifecycle_status(self, status: str) -> LifecycleState:
        """Parse lifecycle status string to LifecycleState enum.

        Args:
            status: Status string from ModelIdentity

        Returns:
            LifecycleState enum value
        """
        try:
            return LifecycleState(status.upper())
        except (ValueError, AttributeError):
            return LifecycleState.DISCOVERED

    def _create_record(
        self,
        model: ModelIdentity,
        current_state: LifecycleState,
        previous_state: LifecycleState,
        reason: str
    ) -> ModelLifecycleRecord:
        """Create immutable lifecycle record.

        Args:
            model: ModelIdentity
            current_state: New lifecycle state
            previous_state: Previous lifecycle state
            reason: Reason for state or transition

        Returns:
            Immutable ModelLifecycleRecord
        """
        timestamp = datetime.now(UTC).isoformat().replace('+00:00', 'Z')

        return ModelLifecycleRecord(
            artifact_path=model.artifact_path,
            symbol=model.symbol,
            asset_class=model.asset_class,
            current_state=current_state,
            previous_state=previous_state if current_state != previous_state else None,
            reason=reason,
            timestamp=timestamp
        )
