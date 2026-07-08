"""Pure statistical functions for distribution and return analysis."""

import numpy as np
from scipy import stats
from typing import List, Optional

from ml_service.research.statistics_toolkit.types import DistributionStats, ReturnStats


def compute_distribution_stats(returns: List[float]) -> DistributionStats:
    """Compute distribution statistics for a return series."""
    arr = np.array(returns)

    return DistributionStats(
        mean=float(np.mean(arr)),
        median=float(np.median(arr)),
        std=float(np.std(arr, ddof=1)),
        variance=float(np.var(arr, ddof=1)),
        skew=float(stats.skew(arr)),
        kurtosis=float(stats.kurtosis(arr))
    )


def compute_return_stats(
    returns: List[float],
    rolling_window: Optional[int] = None
) -> ReturnStats:
    """Compute return statistics."""
    arr = np.array(returns)

    cumulative = float(np.prod(1 + arr) - 1)
    average = float(np.mean(arr))
    vol = float(np.std(arr, ddof=1))

    rolling_vol = None
    if rolling_window and len(arr) >= rolling_window:
        rolling_vol = [
            float(np.std(arr[i:i+rolling_window], ddof=1))
            for i in range(len(arr) - rolling_window + 1)
        ]

    return ReturnStats(
        cumulative_return=cumulative,
        average_return=average,
        volatility=vol,
        rolling_volatility=rolling_vol
    )
