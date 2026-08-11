"""Registry Event Ledger Interfaces - Sprint 3.9D-10

Protocol definitions for event ledger components.
ADR-024 compliant: research layer only, no database dependencies.
"""

from typing import Protocol, Optional
from ml_service.research.registry_event_ledger.models import RegistryEventRecord
from ml_service.research.promotion_workflow.models import PromotionEvent


class IEventStorage(Protocol):
    """Protocol for event storage backend."""

    def append(self, record: RegistryEventRecord, payload: dict) -> None:
        """Append event record and payload to storage."""
        ...

    def read_all(self) -> list[tuple[RegistryEventRecord, dict]]:
        """Read all events with payloads."""
        ...


class IRegistryEventLedger(Protocol):
    """Protocol for registry event ledger."""

    def append(self, event: PromotionEvent) -> RegistryEventRecord:
        """Append PromotionEvent to ledger."""
        ...

    def get_events(self) -> list[RegistryEventRecord]:
        """Get all events in chronological order."""
        ...

    def get_model_history(self, model_id: str) -> list[RegistryEventRecord]:
        """Get event history for specific model."""
        ...

    def latest_event(self, model_id: str) -> Optional[RegistryEventRecord]:
        """Get most recent event for model."""
        ...
