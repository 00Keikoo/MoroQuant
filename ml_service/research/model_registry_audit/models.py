"""Model Registry Audit Models - Sprint 3.9D-4

Immutable data models representing model classification audit reports.
"""

import json
from dataclasses import dataclass, field
from typing import Tuple, Dict, Any


@dataclass(frozen=True)
class AuditReport:
    """Immutable report containing classification metrics for discovered models.

    Adheres to ADR-024 compliance with strict immutability and deterministic serialization.
    """
    total_models: int
    crypto_models: int
    proxy_models: int
    validated_models: int
    calibrated_models: int
    governance_ready_models: int
    invalid_models: int
    classification_summary: Tuple[Tuple[str, int], ...] = field(default_factory=tuple)

    def __post_init__(self):
        # Validate inputs are integers
        for field_name in [
            "total_models",
            "crypto_models",
            "proxy_models",
            "validated_models",
            "calibrated_models",
            "governance_ready_models",
            "invalid_models"
        ]:
            val = getattr(self, field_name)
            if not isinstance(val, int):
                raise TypeError(f"{field_name} must be an integer, got {type(val)}")
            if val < 0:
                raise ValueError(f"{field_name} cannot be negative, got {val}")

        # Compute or enforce deterministic sorted classification_summary
        if not self.classification_summary:
            summary = (
                ("total_models", self.total_models),
                ("crypto_models", self.crypto_models),
                ("proxy_models", self.proxy_models),
                ("validated_models", self.validated_models),
                ("calibrated_models", self.calibrated_models),
                ("governance_ready_models", self.governance_ready_models),
                ("invalid_models", self.invalid_models),
            )
            # Sort keys alphabetically to guarantee deterministic order
            sorted_summary = tuple(sorted(summary, key=lambda x: x[0]))
            object.__setattr__(self, "classification_summary", sorted_summary)
        else:
            # Ensure the provided classification_summary is a tuple of tuples
            formatted_summary = tuple(tuple(x) for x in self.classification_summary)
            # Sort it to ensure determinism
            sorted_summary = tuple(sorted(formatted_summary, key=lambda x: x[0]))
            object.__setattr__(self, "classification_summary", sorted_summary)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the audit report into a dictionary.

        Collections are sorted to ensure determinism.
        """
        return {
            "total_models": self.total_models,
            "crypto_models": self.crypto_models,
            "proxy_models": self.proxy_models,
            "validated_models": self.validated_models,
            "calibrated_models": self.calibrated_models,
            "governance_ready_models": self.governance_ready_models,
            "invalid_models": self.invalid_models,
            "classification_summary": [list(x) for x in self.classification_summary],
        }

    def to_json(self) -> str:
        """Deterministic JSON serialization of the audit report."""
        return json.dumps(self.to_dict(), sort_keys=True)
