"""Overfitting detection logic."""

from .types import SplitMetrics, OverfitAnalysis


def calculate_overfit_score(
    train_metrics: SplitMetrics,
    validation_metrics: SplitMetrics,
    threshold: float = 0.3
) -> OverfitAnalysis:
    """
    Detect overfitting by comparing train vs validation performance.

    Returns overfit_score and is_overfit flag.
    """
    sharpe_decay = _calculate_decay(
        train_metrics.sharpe_ratio,
        validation_metrics.sharpe_ratio
    )

    return_decay = _calculate_decay(
        train_metrics.total_return,
        validation_metrics.total_return
    )

    overfit_score = (sharpe_decay + return_decay) / 2.0
    is_overfit = overfit_score > threshold

    return OverfitAnalysis(
        train_sharpe=train_metrics.sharpe_ratio,
        validation_sharpe=validation_metrics.sharpe_ratio,
        sharpe_decay=sharpe_decay,
        train_return=train_metrics.total_return,
        validation_return=validation_metrics.total_return,
        return_decay=return_decay,
        overfit_score=overfit_score,
        is_overfit=is_overfit
    )


def _calculate_decay(train_value: float, validation_value: float) -> float:
    """Calculate performance decay from train to validation."""
    if train_value == 0:
        return 0.0

    decay = (train_value - validation_value) / abs(train_value)
    return max(0.0, decay)
