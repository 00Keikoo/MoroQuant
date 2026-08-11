"""Registry Event Ledger - Sprint 3.9D-10

Immutable append-only event ledger for PromotionEvent history.
ADR-024 compliant: research layer only, no database, JSON storage.

Exports:
    - RegistryEventRecord: Immutable event record with payload hash
    - RegistryEventLedger: Append-only event ledger service
"""

from ml_service.research.registry_event_ledger.models import RegistryEventRecord
from ml_service.research.registry_event_ledger.service import RegistryEventLedger

__all__ = [
    "RegistryEventRecord",
    "RegistryEventLedger",
]
