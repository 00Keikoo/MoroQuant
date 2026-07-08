"""Types for validation engine."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TimeSeriesSplit:
    """Chronological time series split."""
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    test_start: str
    test_end: str


@dataclass
class SplitMetrics:
    """Performance metrics for a time period."""
    sharpe_ratio: float
    total_return: float
    win_rate: float
    max_drawdown: float
    trade_count: int
    sortino_ratio: float
    profit_factor: float


@dataclass
class WalkForwardWindow:
    """Single walk-forward window."""
    window_id: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    train_metrics: Optional[SplitMetrics] = None
    test_metrics: Optional[SplitMetrics] = None


@dataclass
class OverfitAnalysis:
    """Overfitting detection result."""
    train_sharpe: float
    validation_sharpe: float
    sharpe_decay: float
    train_return: float
    validation_return: float
    return_decay: float
    overfit_score: float
    is_overfit: bool


@dataclass
class StabilityAnalysis:
    """Stability analysis result."""
    sharpe_std: float
    return_std: float
    winrate_std: float
    consistency_ratio: float
    stability_score: float
    is_stable: bool


@dataclass
class ValidationReport:
    """Complete validation report."""
    experiment_id: str
    train_metrics: SplitMetrics
    validation_metrics: SplitMetrics
    test_metrics: SplitMetrics
    overfit_score: float
    stability_score: float
    warnings: List[str]
    final_verdict: str
    overfit_analysis: Optional[OverfitAnalysis] = None
    stability_analysis: Optional[StabilityAnalysis] = None
    walk_forward_windows: Optional[List[WalkForwardWindow]] = None
