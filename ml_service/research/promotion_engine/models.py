"""Promotion Decision Engine Models - Sprint 3.9D-8

Immutable data models for deterministic promotion decision tracking.
ADR-024 compliant: research layer only, no database, no execution dependencies.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Tuple
import json


class PromotionStatus(Enum):
    """Promotion status states for model candidates.

    Status flow:
    - CANDIDATE: Initial state for evaluation
    - APPROVED: Passed all promotion criteria
    - REJECTED: Failed one or more promotion criteria
    - BLOCKED: Cannot be promoted due to policy constraints
    """
    CANDIDATE = "CANDIDATE"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class PromotionScore:
    """Immutable weighted promotion score.

    Deterministic scoring with fixed weights:
    - validation_score: 30%
    - calibration_score: 20%
    - lifecycle_score: 30%
    - governance_score: 20%
    """
    model_id: str
    validation_score: float
    calibration_score: float
    lifecycle_score: float
    governance_score: float
    total_score: float

    def __post_init__(self):
        if not self.model_id:
            raise ValueError("model_id cannot be empty")

        for field_name in ["validation_score", "calibration_score", "lifecycle_score", "governance_score", "total_score"]:
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)):
                raise TypeError(f"{field_name} must be numeric, got {type(value)}")
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0.0 and 1.0, got {value}")

        expected_total = (
            self.validation_score * 0.30 +
            self.calibration_score * 0.20 +
            self.lifecycle_score * 0.30 +
            self.governance_score * 0.20
        )
        if abs(self.total_score - expected_total) > 0.001:
            raise ValueError(
                f"total_score {self.total_score} does not match weighted sum {expected_total}"
            )


@dataclass(frozen=True)
class RegistryProposal:
    """Immutable promotion proposal for registry update.

    Represents a deterministic promotion decision with complete audit trail.
    Supports JSON serialization for persistence and reproducibility.
    """
    model_id: str
    symbol: str
    asset_class: str
    current_state: str
    proposed_state: str
    status: PromotionStatus
    score: PromotionScore
    reason_codes: Tuple[str, ...]

    def __post_init__(self):
        if not isinstance(self.status, PromotionStatus):
            raise TypeError(f"status must be PromotionStatus, got {type(self.status)}")
        if not isinstance(self.score, PromotionScore):
            raise TypeError(f"score must be PromotionScore, got {type(self.score)}")
        if not isinstance(self.reason_codes, tuple):
            raise TypeError(f"reason_codes must be tuple, got {type(self.reason_codes)}")

        if not self.model_id:
            raise ValueError("model_id cannot be empty")
        if not self.symbol:
            raise ValueError("symbol cannot be empty")
        if not self.asset_class:
            raise ValueError("asset_class cannot be empty")
        if not self.current_state:
            raise ValueError("current_state cannot be empty")
        if not self.proposed_state:
            raise ValueError("proposed_state cannot be empty")

        if self.model_id != self.score.model_id:
            raise ValueError(
                f"model_id mismatch: proposal={self.model_id}, score={self.score.model_id}"
            )

    def to_dict(self) -> dict:
        """Convert to deterministic dictionary for JSON serialization."""
        return {
            "model_id": self.model_id,
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "current_state": self.current_state,
            "proposed_state": self.proposed_state,
            "status": self.status.value,
            "score": {
                "model_id": self.score.model_id,
                "validation_score": self.score.validation_score,
                "calibration_score": self.score.calibration_score,
                "lifecycle_score": self.score.lifecycle_score,
                "governance_score": self.score.governance_score,
                "total_score": self.score.total_score,
            },
            "reason_codes": list(self.reason_codes),
        }

    def to_json(self) -> str:
        """Convert to deterministic JSON string."""
        return json.dumps(self.to_dict(), sort_keys=True, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "RegistryProposal":
        """Reconstruct from dictionary."""
        score_data = data["score"]
        score = PromotionScore(
            model_id=score_data["model_id"],
            validation_score=score_data["validation_score"],
            calibration_score=score_data["calibration_score"],
            lifecycle_score=score_data["lifecycle_score"],
            governance_score=score_data["governance_score"],
            total_score=score_data["total_score"],
        )

        return cls(
            model_id=data["model_id"],
            symbol=data["symbol"],
            asset_class=data["asset_class"],
            current_state=data["current_state"],
            proposed_state=data["proposed_state"],
            status=PromotionStatus(data["status"]),
            score=score,
            reason_codes=tuple(data["reason_codes"]),
        )
