"""Types for statistical comparison engine."""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class MetricsDifference:
    """Difference in key metrics between two experiments."""
    return_diff: float
    sharpe_diff: float
    drawdown_diff: float
    win_rate_diff: float


@dataclass
class HypothesisTestResult:
    """Result of hypothesis testing."""
    t_test_pvalue: float
    mann_whitney_pvalue: float
    t_test_significant: bool
    mann_whitney_significant: bool
    alpha: float


@dataclass
class BootstrapResult:
    """Result of bootstrap analysis."""
    confidence_interval_lower: float
    confidence_interval_upper: float
    probability_a_beats_b: float
    n_iterations: int


@dataclass
class ComparisonReport:
    """Complete statistical comparison report."""
    experiment_a_id: str
    experiment_b_id: str

    metrics_difference: MetricsDifference

    hypothesis_test: HypothesisTestResult

    bootstrap_result: BootstrapResult

    verdict: str
