"""Statistical comparison engine for experiments."""

from .types import (
    MetricsDifference,
    HypothesisTestResult,
    BootstrapResult,
    ComparisonReport
)
from .comparison import (
    calculate_metrics_difference,
    calculate_confidence_interval
)
from .hypothesis import run_hypothesis_tests
from .bootstrap import run_bootstrap_analysis
from .service import ComparisonEngine

__all__ = [
    "MetricsDifference",
    "HypothesisTestResult",
    "BootstrapResult",
    "ComparisonReport",
    "calculate_metrics_difference",
    "calculate_confidence_interval",
    "run_hypothesis_tests",
    "run_bootstrap_analysis",
    "ComparisonEngine",
]
