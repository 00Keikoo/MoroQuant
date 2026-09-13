"""Governance audit extraction for promotion engine.

Provides governance readiness assessment from lifecycle state for single-model promotion.
"""

from ml_service.research.model_lifecycle.models import ModelLifecycleRecord, LifecycleState


def governance_audit_from_lifecycle(lifecycle_record: ModelLifecycleRecord) -> dict:
    """Extract governance audit from model lifecycle state.

    Single-model promotion requires only governance readiness flag.
    This is derived from lifecycle state, not from benchmark performance.

    Args:
        lifecycle_record: Model lifecycle evaluation result

    Returns:
        Audit report dict with governance_ready flag for promotion evaluation
    """
    governance_ready = lifecycle_record.current_state == LifecycleState.GOVERNANCE_READY

    return {
        "governance_ready": governance_ready,
    }
