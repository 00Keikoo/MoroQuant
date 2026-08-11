"""Model Lifecycle Models - Sprint 3.9D-7

Immutable data models for deterministic model lifecycle state tracking.
ADR-024 compliant: research layer only, no database, no execution dependencies.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class LifecycleState(Enum):
    """Lifecycle states for model artifacts.

    State progression:
    - DISCOVERED: Initial detection by ModelArtifactScanner
    - VALIDATED: Has validation metrics available
    - GOVERNANCE_READY: Has calibration metrics, ready for audit
    - APPROVED: Passed governance audit, ready for production
    - PRODUCTION: Deployed and active
    - REJECTED: Failed governance or validation checks
    """
    DISCOVERED = "DISCOVERED"
    VALIDATED = "VALIDATED"
    GOVERNANCE_READY = "GOVERNANCE_READY"
    APPROVED = "APPROVED"
    PRODUCTION = "PRODUCTION"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class ModelLifecycleRecord:
    """Immutable record of a model lifecycle state transition.

    Captures the complete context of a state change for audit trail purposes.
    """
    artifact_path: str
    symbol: str
    asset_class: str
    current_state: LifecycleState
    previous_state: Optional[LifecycleState]
    reason: str
    timestamp: str

    def __post_init__(self):
        if not isinstance(self.current_state, LifecycleState):
            raise TypeError(f"current_state must be LifecycleState, got {type(self.current_state)}")
        if self.previous_state is not None and not isinstance(self.previous_state, LifecycleState):
            raise TypeError(f"previous_state must be LifecycleState or None, got {type(self.previous_state)}")
        if not self.artifact_path:
            raise ValueError("artifact_path cannot be empty")
        if not self.symbol:
            raise ValueError("symbol cannot be empty")
        if not self.asset_class:
            raise ValueError("asset_class cannot be empty")
        if not self.reason:
            raise ValueError("reason cannot be empty")
        if not self.timestamp:
            raise ValueError("timestamp cannot be empty")
