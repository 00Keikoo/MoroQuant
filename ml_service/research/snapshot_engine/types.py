"""Types for snapshot engine."""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class Snapshot:
    """Immutable snapshot of system state."""
    snapshot_id: str
    timestamp: str
    trades: List[Dict[str, Any]]
    signals: List[Dict[str, Any]]
    account_state: Optional[Dict[str, Any]] = None
    market_state: Optional[Dict[str, Any]] = None
    model_state: Optional[Dict[str, Any]] = None
    signal_state: Optional[Dict[str, Any]] = None
    feature_state: Optional[Dict[str, Any]] = None
    regime_state: Optional[Dict[str, Any]] = None
    risk_state: Optional[Dict[str, Any]] = None
    execution_state: Optional[Dict[str, Any]] = None
    position_state: Optional[Dict[str, Any]] = None
    execution_constraints: Optional[Dict[str, Any]] = None
    regime_statistics: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary for JSON serialization."""
        result = {
            'snapshot_id': self.snapshot_id,
            'timestamp': self.timestamp,
            'trades': self.trades,
            'signals': self.signals
        }
        if self.account_state is not None:
            result['account_state'] = self.account_state
        if self.market_state is not None:
            result['market_state'] = self.market_state
        if self.model_state is not None:
            result['model_state'] = self.model_state
        if self.signal_state is not None:
            result['signal_state'] = self.signal_state
        if self.feature_state is not None:
            result['feature_state'] = self.feature_state
        if self.regime_state is not None:
            result['regime_state'] = self.regime_state
        if self.risk_state is not None:
            result['risk_state'] = self.risk_state
        if self.execution_state is not None:
            result['execution_state'] = self.execution_state
        if self.position_state is not None:
            result['position_state'] = self.position_state
        if self.execution_constraints is not None:
            result['execution_constraints'] = self.execution_constraints
        if self.regime_statistics is not None:
            result['regime_statistics'] = self.regime_statistics
        return result
