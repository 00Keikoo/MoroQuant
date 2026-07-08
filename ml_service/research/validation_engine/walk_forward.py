"""Walk forward validation logic."""

from typing import List, Callable
from datetime import datetime, timedelta

from .types import WalkForwardWindow, SplitMetrics


def create_walk_forward_windows(
    timestamps: List[str],
    train_window_days: int,
    test_window_days: int,
    step_days: int
) -> List[WalkForwardWindow]:
    """
    Create rolling walk-forward windows.

    Train on fixed window, test on future window, step forward.
    """
    if not timestamps:
        raise ValueError("timestamps cannot be empty")

    sorted_timestamps = sorted(timestamps)
    start_dt = datetime.fromisoformat(sorted_timestamps[0].replace('Z', '+00:00'))
    end_dt = datetime.fromisoformat(sorted_timestamps[-1].replace('Z', '+00:00'))

    windows = []
    window_id = 0
    current_start = start_dt

    while True:
        train_start = current_start
        train_end = train_start + timedelta(days=train_window_days)
        test_start = train_end
        test_end = test_start + timedelta(days=test_window_days)

        if test_end > end_dt:
            break

        windows.append(WalkForwardWindow(
            window_id=window_id,
            train_start=train_start.isoformat(),
            train_end=train_end.isoformat(),
            test_start=test_start.isoformat(),
            test_end=test_end.isoformat()
        ))

        window_id += 1
        current_start += timedelta(days=step_days)

    return windows


def evaluate_walk_forward(
    windows: List[WalkForwardWindow],
    evaluate_fn: Callable[[str, str], SplitMetrics]
) -> List[WalkForwardWindow]:
    """
    Evaluate each walk-forward window using provided function.

    evaluate_fn receives (start, end) and returns SplitMetrics.
    """
    evaluated_windows = []

    for window in windows:
        train_metrics = evaluate_fn(window.train_start, window.train_end)
        test_metrics = evaluate_fn(window.test_start, window.test_end)

        evaluated_windows.append(WalkForwardWindow(
            window_id=window.window_id,
            train_start=window.train_start,
            train_end=window.train_end,
            test_start=window.test_start,
            test_end=window.test_end,
            train_metrics=train_metrics,
            test_metrics=test_metrics
        ))

    return evaluated_windows
