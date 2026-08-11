"""Model Lifecycle Management - Sprint 3.9D-7

Deterministic lifecycle state management for model artifacts.
ADR-024 compliant: research layer only, no database, no execution dependencies.

Exports:
    - LifecycleState: Enum of lifecycle states
    - ModelLifecycleRecord: Immutable state transition record
    - LifecyclePolicy: Asset-specific transition rules
    - LifecycleManager: State evaluation and transition manager
"""

from ml_service.research.model_lifecycle.models import LifecycleState, ModelLifecycleRecord
from ml_service.research.model_lifecycle.policy import LifecyclePolicy
from ml_service.research.model_lifecycle.lifecycle import LifecycleManager
from ml_service.research.model_lifecycle.interfaces import LifecycleManager as ILifecycleManager

__all__ = [
    "LifecycleState",
    "ModelLifecycleRecord",
    "LifecyclePolicy",
    "LifecycleManager",
    "ILifecycleManager",
]
