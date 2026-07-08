"""Sample quality analysis functions."""

import numpy as np
from typing import List
from scipy import stats

from ml_service.research.statistics_toolkit.types import QualityStats


def compute_confidence_level(sample_size: int, std: float, mean: float) -> float:
    """Compute confidence level for sample mean estimate."""
    if sample_size < 2 or std == 0:
        return 0.0

    t_stat = abs(mean) / (std / np.sqrt(sample_size))
    df = sample_size - 1
    p_value = 2 * (1 - stats.t.cdf(t_stat, df))

    return float(1 - p_value)


def generate_quality_warnings(
    sample_size: int,
    trade_count: int,
    confidence_level: float
) -> List[str]:
    """Generate warnings about sample quality."""
    warnings = []

    if sample_size < 30:
        warnings.append(f"Small sample size ({sample_size}). Results may not be reliable.")

    if trade_count < 20:
        warnings.append(f"Low trade count ({trade_count}). Insufficient trading activity.")

    if confidence_level < 0.90:
        warnings.append(f"Low confidence level ({confidence_level:.2f}). Results not statistically significant.")

    if sample_size < 100 and confidence_level < 0.95:
        warnings.append("Combined small sample and low confidence. Use results with caution.")

    return warnings


def compute_quality_stats(
    returns: List[float],
    trade_count: int
) -> QualityStats:
    """Compute sample quality statistics."""
    sample_size = len(returns)

    if sample_size == 0:
        return QualityStats(
            sample_size=0,
            trade_count=trade_count,
            confidence_level=0.0,
            warnings=["No data available for analysis."]
        )

    arr = np.array(returns)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))

    confidence = compute_confidence_level(sample_size, std, mean)
    warnings = generate_quality_warnings(sample_size, trade_count, confidence)

    return QualityStats(
        sample_size=sample_size,
        trade_count=trade_count,
        confidence_level=confidence,
        warnings=warnings
    )
