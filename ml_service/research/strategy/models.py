"""Strategy Domain Models - Sprint 3.9B-1

Immutable domain objects following ADR-024.
All state transitions are pure functional - no mutation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Tuple, Union, Optional
import json


class SignalAction(Enum):
    """Allowed strategy actions."""
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


@dataclass(frozen=True)
class StrategyState:
    """Immutable strategy runtime state.

    Updated via dataclasses.replace() - never mutated in place.
    """
    strategy_id: str
    timestamp: str
    parameters: Tuple[Tuple[str, Union[str, int, float, bool, None]], ...] = field(default_factory=tuple)
    internal_state: Tuple[Tuple[str, Union[str, int, float, bool, None]], ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        sorted_params = sorted(self.parameters, key=lambda x: x[0])
        sorted_state = sorted(self.internal_state, key=lambda x: x[0])
        return {
            "strategy_id": self.strategy_id,
            "timestamp": self.timestamp,
            "parameters": [list(item) for item in sorted_params],
            "internal_state": [list(item) for item in sorted_state],
        }

    def serialize(self) -> str:
        """Returns deterministic JSON string."""
        return json.dumps(self.to_dict(), sort_keys=True)


@dataclass(frozen=True)
class FeatureSnapshot:
    """Immutable container for calculated features.

    Future: will contain feature engineering output.
    Currently placeholder for architecture boundary.
    """
    timestamp: str
    features: Tuple[Tuple[str, float], ...] = field(default_factory=tuple)
    schema_version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        sorted_features = sorted(self.features, key=lambda x: x[0])
        return {
            "timestamp": self.timestamp,
            "features": [list(item) for item in sorted_features],
            "schema_version": self.schema_version,
        }



@dataclass(frozen=True)
class Signal:
    """Immutable strategy decision output.

    Represents strategy intent - NOT order execution.
    No order creation or portfolio logic allowed here.
    """
    timestamp: str
    action: SignalAction
    confidence: float
    metadata: Tuple[Tuple[str, Union[str, int, float, bool, None]], ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        sorted_metadata = sorted(self.metadata, key=lambda x: x[0])
        return {
            "timestamp": self.timestamp,
            "action": self.action.value,
            "confidence": self.confidence,
            "metadata": [list(item) for item in sorted_metadata],
        }


@dataclass(frozen=True)
class StrategyResult:
    """Result of strategy.process() call.

    Contains new state and optional signal.
    Immutable container - updated state returned, not mutated.
    """
    new_state: StrategyState
    signal: Optional[Signal] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "new_state": self.new_state.to_dict(),
            "signal": self.signal.to_dict() if self.signal else None,
        }
