"""Core comparison logic for experiments."""

from typing import List
import numpy as np

from .types import MetricsDifference


def calculate_metrics_difference(
    returns_a: List[float],
    returns_b: List[float],
    sharpe_a: float,
    sharpe_b: float,
    max_dd_a: float,
    max_dd_b: float,
    win_rate_a: float,
    win_rate_b: float
) -> MetricsDifference:
    """Calculate difference in key metrics between two experiments."""

    total_return_a = sum(returns_a)
    total_return_b = sum(returns_b)

    return MetricsDifference(
        return_diff=total_return_a - total_return_b,
        sharpe_diff=sharpe_a - sharpe_b,
        drawdown_diff=max_dd_a - max_dd_b,
        win_rate_diff=win_rate_a - win_rate_b
    )


def calculate_confidence_interval(
    returns: List[float],
    confidence_level: float = 0.95
) -> tuple[float, float]:
    """Calculate confidence interval for returns using normal approximation."""

    if len(returns) == 0:
        return (0.0, 0.0)

    arr = np.array(returns)
    mean = np.mean(arr)
    std_err = np.std(arr, ddof=1) / np.sqrt(len(arr))

    from scipy import stats
    z_score = stats.norm.ppf((1 + confidence_level) / 2)

    margin = z_score * std_err

    return (float(mean - margin), float(mean + margin))
