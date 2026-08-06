"""Research Reporting Models - Sprint 3.9C-6

Immutable domain models representing finalized quantitative research reports.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Tuple
import json


@dataclass(frozen=True)
class ResearchReport:
    """Immutable quantitative research report representing evaluation results.

    Adheres to ADR-024 compliance with strict immutability and deterministic serialization.
    """
    experiment_id: str
    total_signals: int
    win_rate: float
    average_return: float
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    profit_factor: float
    metrics: Tuple[Tuple[str, float], ...] = field(default_factory=tuple)

    def __post_init__(self):
        if not self.experiment_id:
            raise ValueError("experiment_id cannot be empty")
        # Ensure metrics is a tuple of tuples
        if not isinstance(self.metrics, tuple):
            object.__setattr__(self, 'metrics', tuple(self.metrics))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the report to a dictionary with deterministic key and metric sorting."""
        sorted_metrics = sorted(self.metrics, key=lambda x: x[0])
        return {
            "experiment_id": self.experiment_id,
            "total_signals": self.total_signals,
            "win_rate": self.win_rate,
            "average_return": self.average_return,
            "total_return": self.total_return,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "profit_factor": self.profit_factor,
            "metrics": [list(x) for x in sorted_metrics],
        }

    def to_json(self) -> str:
        """Deterministic JSON serialization of the research report."""
        return json.dumps(self.to_dict(), sort_keys=True)
