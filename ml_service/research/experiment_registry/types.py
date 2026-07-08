"""Types for experiment registry."""

from dataclasses import dataclass
from typing import List

from ml_service.research.experiment_engine.types import StrategyConfig, StrategyResult


@dataclass
class StoredExperiment:
    """Stored experiment with full history."""
    experiment_id: str
    snapshot_id: str
    created_at: str
    configs: List[StrategyConfig]
    results: List[StrategyResult]


@dataclass
class ComparisonResult:
    """Comparison between two experiments."""
    base_experiment_id: str
    compare_experiment_id: str
    pnl_diff: float
    sharpe_diff: float
    winrate_diff: float
    consistency_diff: float
    drawdown_diff: float
