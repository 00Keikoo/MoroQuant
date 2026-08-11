"""Model Lifecycle Policy - Sprint 3.9D-7

Asset-specific transition rules for model lifecycle state management.
ADR-024 compliant: deterministic, stateless, no database dependencies.
"""

from typing import Dict, Tuple, Callable
from ml_service.research.model_identity.models import ModelIdentity
from ml_service.research.model_lifecycle.models import LifecycleState


class LifecyclePolicy:
    """Deterministic policy engine for model lifecycle state transitions.

    Implements asset-specific rules:
    - Crypto: Full lifecycle path to PRODUCTION
    - Proxy assets: Blocked from PRODUCTION
    """

    CRYPTO_TRANSITIONS: Dict[LifecycleState, Tuple[LifecycleState, ...]] = {
        LifecycleState.DISCOVERED: (LifecycleState.VALIDATED, LifecycleState.REJECTED),
        LifecycleState.VALIDATED: (LifecycleState.GOVERNANCE_READY, LifecycleState.REJECTED),
        LifecycleState.GOVERNANCE_READY: (LifecycleState.APPROVED, LifecycleState.REJECTED),
        LifecycleState.APPROVED: (LifecycleState.PRODUCTION, LifecycleState.REJECTED),
        LifecycleState.PRODUCTION: (LifecycleState.REJECTED,),
        LifecycleState.REJECTED: (),
    }

    PROXY_TRANSITIONS: Dict[LifecycleState, Tuple[LifecycleState, ...]] = {
        LifecycleState.DISCOVERED: (LifecycleState.VALIDATED, LifecycleState.REJECTED),
        LifecycleState.VALIDATED: (LifecycleState.GOVERNANCE_READY, LifecycleState.REJECTED),
        LifecycleState.GOVERNANCE_READY: (LifecycleState.REJECTED,),
        LifecycleState.APPROVED: (LifecycleState.REJECTED,),
        LifecycleState.PRODUCTION: (),
        LifecycleState.REJECTED: (),
    }

    @staticmethod
    def get_allowed_transitions(asset_class: str, current_state: LifecycleState) -> Tuple[LifecycleState, ...]:
        """Get allowed target states from current state for given asset class.

        Args:
            asset_class: Asset class (crypto, proxy, etc.)
            current_state: Current lifecycle state

        Returns:
            Tuple of allowed target states
        """
        if asset_class.lower() == "crypto":
            return LifecyclePolicy.CRYPTO_TRANSITIONS.get(current_state, ())
        elif asset_class.lower() == "proxy":
            return LifecyclePolicy.PROXY_TRANSITIONS.get(current_state, ())
        else:
            return ()

    @staticmethod
    def is_transition_allowed(asset_class: str, current_state: LifecycleState, target_state: LifecycleState) -> bool:
        """Check if transition is allowed for given asset class.

        Args:
            asset_class: Asset class (crypto, proxy, etc.)
            current_state: Current lifecycle state
            target_state: Desired target state

        Returns:
            True if transition is allowed, False otherwise
        """
        allowed = LifecyclePolicy.get_allowed_transitions(asset_class, current_state)
        return target_state in allowed

    @staticmethod
    def validate_discovered_to_validated(model: ModelIdentity) -> Tuple[bool, str]:
        """Validate transition from DISCOVERED to VALIDATED.

        Args:
            model: ModelIdentity to evaluate

        Returns:
            (is_valid, reason)
        """
        if not model.validation_available:
            return False, "validation metrics not available"
        return True, "validation metrics available"

    @staticmethod
    def validate_validated_to_governance_ready(model: ModelIdentity) -> Tuple[bool, str]:
        """Validate transition from VALIDATED to GOVERNANCE_READY.

        Args:
            model: ModelIdentity to evaluate

        Returns:
            (is_valid, reason)
        """
        if not model.calibration_available:
            return False, "calibration metrics not available"
        return True, "calibration metrics available"

    @staticmethod
    def validate_governance_ready_to_approved(model: ModelIdentity) -> Tuple[bool, str]:
        """Validate transition from GOVERNANCE_READY to APPROVED.

        Requires explicit audit pass (simulated here as always passing for research layer).

        Args:
            model: ModelIdentity to evaluate

        Returns:
            (is_valid, reason)
        """
        return True, "governance audit passed"

    @staticmethod
    def validate_approved_to_production(model: ModelIdentity) -> Tuple[bool, str]:
        """Validate transition from APPROVED to PRODUCTION.

        Proxy assets are blocked from production.

        Args:
            model: ModelIdentity to evaluate

        Returns:
            (is_valid, reason)
        """
        if model.asset_class.lower() == "proxy":
            return False, "proxy assets blocked from production"
        return True, "explicit approval for production"

    @staticmethod
    def can_evaluate_transition(
        model: ModelIdentity,
        current_state: LifecycleState,
        target_state: LifecycleState
    ) -> Tuple[bool, str]:
        """Evaluate if transition is valid based on model properties and policy rules.

        Args:
            model: ModelIdentity to evaluate
            current_state: Current lifecycle state
            target_state: Desired target state

        Returns:
            (is_valid, reason)
        """
        if not LifecyclePolicy.is_transition_allowed(model.asset_class, current_state, target_state):
            return False, f"transition {current_state.value} -> {target_state.value} not allowed for {model.asset_class}"

        validators: Dict[Tuple[LifecycleState, LifecycleState], Callable[[ModelIdentity], Tuple[bool, str]]] = {
            (LifecycleState.DISCOVERED, LifecycleState.VALIDATED): LifecyclePolicy.validate_discovered_to_validated,
            (LifecycleState.VALIDATED, LifecycleState.GOVERNANCE_READY): LifecyclePolicy.validate_validated_to_governance_ready,
            (LifecycleState.GOVERNANCE_READY, LifecycleState.APPROVED): LifecyclePolicy.validate_governance_ready_to_approved,
            (LifecycleState.APPROVED, LifecycleState.PRODUCTION): LifecyclePolicy.validate_approved_to_production,
        }

        validator = validators.get((current_state, target_state))
        if validator:
            return validator(model)

        if target_state == LifecycleState.REJECTED:
            return True, "explicit rejection"

        return True, f"transition {current_state.value} -> {target_state.value} allowed"
