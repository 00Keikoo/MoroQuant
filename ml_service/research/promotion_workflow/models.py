"""Promotion Workflow Models - Sprint 3.9D-9

Immutable event models for promotion workflow tracking.
ADR-024 compliant: research layer only, no database, no execution dependencies.
"""

from dataclasses import dataclass
import hashlib
import json
from typing import Optional


@dataclass(frozen=True)
class PromotionEvent:
    """Immutable promotion event record.

    Represents a state transition decision with complete audit trail.
    Event IDs are deterministically generated from content.
    """
    event_id: str
    model_id: str
    from_state: str
    to_state: str
    decision: str
    reason_codes: tuple[str, ...]
    created_at: str

    def __post_init__(self):
        if not self.event_id:
            raise ValueError("event_id cannot be empty")
        if not self.model_id:
            raise ValueError("model_id cannot be empty")
        if not self.from_state:
            raise ValueError("from_state cannot be empty")
        if not self.to_state:
            raise ValueError("to_state cannot be empty")
        if not self.decision:
            raise ValueError("decision cannot be empty")
        if not isinstance(self.reason_codes, tuple):
            raise TypeError(f"reason_codes must be tuple, got {type(self.reason_codes)}")
        if not self.created_at:
            raise ValueError("created_at cannot be empty")

    @staticmethod
    def generate_event_id(
        model_id: str,
        from_state: str,
        to_state: str,
        created_at: str,
    ) -> str:
        """Generate deterministic event ID from key fields."""
        content = f"{model_id}|{from_state}|{to_state}|{created_at}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        """Convert to deterministic dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "model_id": self.model_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "decision": self.decision,
            "reason_codes": list(self.reason_codes),
            "created_at": self.created_at,
        }

    def to_json(self) -> str:
        """Convert to deterministic JSON string."""
        return json.dumps(self.to_dict(), sort_keys=True, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "PromotionEvent":
        """Reconstruct from dictionary."""
        return cls(
            event_id=data["event_id"],
            model_id=data["model_id"],
            from_state=data["from_state"],
            to_state=data["to_state"],
            decision=data["decision"],
            reason_codes=tuple(data["reason_codes"]),
            created_at=data["created_at"],
        )
