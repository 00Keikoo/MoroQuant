"""Registry Event Ledger Service - Sprint 3.9D-10

Immutable append-only event ledger for PromotionEvent history.
ADR-024 compliant: research layer only, no database, deterministic ordering.
"""

from typing import Optional
from ml_service.research.registry_event_ledger.models import RegistryEventRecord
from ml_service.research.registry_event_ledger.json_ledger import JsonEventStorage
from ml_service.research.promotion_workflow.models import PromotionEvent


class RegistryEventLedger:
    """Append-only event ledger for registry promotion events.

    Features:
    - Immutable event records
    - Deterministic chronological ordering
    - Model-specific event history
    - JSON storage (no database)
    """

    def __init__(self, storage_path: str):
        self.storage = JsonEventStorage(storage_path)

    def append(self, event: PromotionEvent) -> RegistryEventRecord:
        """Append PromotionEvent to ledger.

        Args:
            event: Immutable PromotionEvent from workflow

        Returns:
            RegistryEventRecord confirming append
        """
        payload = event.to_dict()
        payload_hash = RegistryEventRecord.compute_payload_hash(payload)

        record = RegistryEventRecord(
            event_id=event.event_id,
            model_id=event.model_id,
            event_type=event.decision,
            created_at=event.created_at,
            payload_hash=payload_hash,
        )

        self.storage.append(record, payload)
        return record

    def get_events(self) -> list[RegistryEventRecord]:
        """Get all events in chronological order.

        Returns:
            List of event records sorted by created_at
        """
        events_with_payloads = self.storage.read_all()
        return [record for record, _ in events_with_payloads]

    def get_model_history(self, model_id: str) -> list[RegistryEventRecord]:
        """Get event history for specific model.

        Args:
            model_id: Model artifact identifier

        Returns:
            List of event records for model in chronological order
        """
        all_events = self.get_events()
        return [event for event in all_events if event.model_id == model_id]

    def latest_event(self, model_id: str) -> Optional[RegistryEventRecord]:
        """Get most recent event for model.

        Args:
            model_id: Model artifact identifier

        Returns:
            Latest event record or None if no events exist
        """
        history = self.get_model_history(model_id)
        return history[-1] if history else None
