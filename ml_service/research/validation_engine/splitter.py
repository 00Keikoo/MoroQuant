"""Time series split logic."""

from datetime import datetime
from typing import List, Tuple

from .types import TimeSeriesSplit


def create_time_series_split(
    timestamps: List[str],
    train_ratio: float = 0.6,
    validation_ratio: float = 0.2,
    test_ratio: float = 0.2
) -> TimeSeriesSplit:
    """
    Create chronological time series split.

    No random shuffle - maintains temporal order.
    """
    if not timestamps:
        raise ValueError("timestamps cannot be empty")

    if abs((train_ratio + validation_ratio + test_ratio) - 1.0) > 1e-6:
        raise ValueError("ratios must sum to 1.0")

    sorted_timestamps = sorted(timestamps)
    n = len(sorted_timestamps)

    train_end_idx = int(n * train_ratio)
    validation_end_idx = train_end_idx + int(n * validation_ratio)

    train_start = sorted_timestamps[0]
    train_end = sorted_timestamps[train_end_idx - 1]
    validation_start = sorted_timestamps[train_end_idx]
    validation_end = sorted_timestamps[validation_end_idx - 1]
    test_start = sorted_timestamps[validation_end_idx]
    test_end = sorted_timestamps[-1]

    return TimeSeriesSplit(
        train_start=train_start,
        train_end=train_end,
        validation_start=validation_start,
        validation_end=validation_end,
        test_start=test_start,
        test_end=test_end
    )


def filter_by_period(
    timestamps: List[str],
    start: str,
    end: str
) -> List[str]:
    """Filter timestamps within period [start, end]."""
    return [ts for ts in timestamps if start <= ts <= end]
