"""Types for Decision Truth Layer."""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Literal


@dataclass
class DecisionContext:
    """Input context for decision making."""
    signal_id: str
    symbol: str
    probability_long: float
    probability_short: float
    probability_neutral: float
    regime: Optional[str] = None
    features: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert decision context to dictionary for JSON serialization."""
        result = {
            'signal_id': self.signal_id,
            'symbol': self.symbol,
            'probability_long': self.probability_long,
            'probability_short': self.probability_short,
            'probability_neutral': self.probability_neutral
        }
        if self.regime is not None:
            result['regime'] = self.regime
        if self.features is not None:
            result['features'] = self.features
        return result


@dataclass
class DecisionResult:
    """Output result from decision engine."""
    action: Literal["LONG", "SHORT", "HOLD"]
    confidence: float
    threshold_used: float
    reason_code: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert decision result to dictionary for JSON serialization."""
        return {
            'action': self.action,
            'confidence': self.confidence,
            'threshold_used': self.threshold_used,
            'reason_code': self.reason_code
        }
