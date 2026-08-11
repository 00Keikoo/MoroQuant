"""Registry Event Ledger Models - Sprint 3.9D-10

Immutable event record models for append-only event ledger.
ADR-024 compliant: research layer only, no database, no execution dependencies.
"""

from dataclasses import dataclass
import hashlib
import json


@dataclass(frozen=True)
class RegistryEventRecord:
    """Immutable event record for the registry ledger.

    Represents a single event in the append-only event history.
    Includes payload hash for integrity verification.
    """
    event_id: str
    model_id: str
    event_type: str
    created_at: str
    payload_hash: str

    def __post_init__(self):
        if not self.event_id:
            raise ValueError("event_id cannot be empty")
        if not self.model_id:
            raise ValueError("model_id cannot be empty")
        if not self.event_type:
            raise ValueError("event_type cannot be empty")
        if not self.created_at:
            raise ValueError("created_at cannot be empty")
        if not self.payload_hash:
            raise ValueError("payload_hash cannot be empty")

    @staticmethod
    def compute_payload_hash(payload: dict) -> str:
        """Compute deterministic SHA256 hash of payload.

        Args:
            payload: Event payload dictionary

        Returns:
            Hex string of SHA256 hash
        """
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def to_dict(self) -> dict:
        """Convert to deterministic dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "model_id": self.model_id,
            "event_type": self.event_type,
            "created_at": self.created_at,
            "payload_hash": self.payload_hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RegistryEventRecord":
        """Reconstruct from dictionary."""
        return cls(
            event_id=data["event_id"],
            model_id=data["model_id"],
            event_type=data["event_type"],
            created_at=data["created_at"],
            payload_hash=data["payload_hash"],
        )
