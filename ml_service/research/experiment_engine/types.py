"""Types for experiment engine."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class StrategyConfig:
    """Strategy configuration for experiment."""
    config_id: str
    threshold_long: float
    threshold_short: float
    enable_filter: bool
    regime_filter: Optional[str] = None


@dataclass
class StrategyResult:
    """Result for a single strategy configuration."""
    config_id: str
    pnl: float
    winrate: float
    sharpe: float
    max_drawdown: float
    consistency_score: float
    trade_count: int


@dataclass
class ExperimentConfig:
    """Configuration for an experiment."""
    experiment_id: str
    snapshot_id: str
    configs: List[StrategyConfig]


@dataclass
class ExperimentResult:
    """Result of running an experiment."""
    experiment_id: str
    snapshot_id: str
    results: List[StrategyResult]
    artifact_path: Optional[str] = None
