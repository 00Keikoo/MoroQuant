"""Stability analysis logic."""

from typing import List
import statistics

from .types import SplitMetrics, StabilityAnalysis, WalkForwardWindow


def calculate_stability_score(
    windows: List[WalkForwardWindow],
    threshold: float = 0.5
) -> StabilityAnalysis:
    """
    Evaluate performance consistency across periods.

    Returns stability_score and is_stable flag.
    """
    if not windows:
        raise ValueError("windows cannot be empty")

    test_windows = [w for w in windows if w.test_metrics is not None]

    if len(test_windows) < 2:
        return StabilityAnalysis(
            sharpe_std=0.0,
            return_std=0.0,
            winrate_std=0.0,
            consistency_ratio=1.0,
            stability_score=1.0,
            is_stable=True
        )

    sharpes = [w.test_metrics.sharpe_ratio for w in test_windows]
    returns = [w.test_metrics.total_return for w in test_windows]
    winrates = [w.test_metrics.win_rate for w in test_windows]

    sharpe_std = statistics.stdev(sharpes) if len(sharpes) > 1 else 0.0
    return_std = statistics.stdev(returns) if len(returns) > 1 else 0.0
    winrate_std = statistics.stdev(winrates) if len(winrates) > 1 else 0.0

    positive_windows = sum(1 for s in sharpes if s > 0)
    consistency_ratio = positive_windows / len(test_windows)

    stability_score = consistency_ratio * (1.0 - min(sharpe_std, 1.0))
    is_stable = stability_score >= threshold

    return StabilityAnalysis(
        sharpe_std=sharpe_std,
        return_std=return_std,
        winrate_std=winrate_std,
        consistency_ratio=consistency_ratio,
        stability_score=stability_score,
        is_stable=is_stable
    )


def calculate_stability_from_metrics(
    metrics_list: List[SplitMetrics],
    threshold: float = 0.5
) -> StabilityAnalysis:
    """Calculate stability from list of SplitMetrics directly."""
    if len(metrics_list) < 2:
        return StabilityAnalysis(
            sharpe_std=0.0,
            return_std=0.0,
            winrate_std=0.0,
            consistency_ratio=1.0,
            stability_score=1.0,
            is_stable=True
        )

    sharpes = [m.sharpe_ratio for m in metrics_list]
    returns = [m.total_return for m in metrics_list]
    winrates = [m.win_rate for m in metrics_list]

    sharpe_std = statistics.stdev(sharpes)
    return_std = statistics.stdev(returns)
    winrate_std = statistics.stdev(winrates)

    positive_windows = sum(1 for s in sharpes if s > 0)
    consistency_ratio = positive_windows / len(metrics_list)

    stability_score = consistency_ratio * (1.0 - min(sharpe_std, 1.0))
    is_stable = stability_score >= threshold

    return StabilityAnalysis(
        sharpe_std=sharpe_std,
        return_std=return_std,
        winrate_std=winrate_std,
        consistency_ratio=consistency_ratio,
        stability_score=stability_score,
        is_stable=is_stable
    )
