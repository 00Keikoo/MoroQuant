"""Regression tests for Blocker 1: Drawdown Scoring Inversion

Verifies that drawdown_recovery_score behaves correctly with realistic
negative drawdown values. Tests the invariant that worse drawdowns
MUST NOT improve the score.

Sprint 3.9D-14R
"""

import pytest
from ml_service.research.reporting.models import ResearchReport
from ml_service.research.benchmark.scoring import calculate_absolute_score


def test_drawdown_scoring_monotonicity():
    """Verify that worse drawdown never improves score."""
    base_report = ResearchReport(
        experiment_id="test",
        total_signals=100,
        win_rate=0.6,
        average_return=0.05,
        total_return=5.0,
        max_drawdown=0.0,
        sharpe_ratio=1.5,
        sortino_ratio=1.5,
        profit_factor=2.0,
    )

    drawdowns = [0.0, -0.1, -1.0, -10.0, -50.0, -100.0]
    scores = []

    for dd in drawdowns:
        report = ResearchReport(
            experiment_id=base_report.experiment_id,
            total_signals=base_report.total_signals,
            win_rate=base_report.win_rate,
            average_return=base_report.average_return,
            total_return=base_report.total_return,
            max_drawdown=dd,
            sharpe_ratio=base_report.sharpe_ratio,
            sortino_ratio=base_report.sortino_ratio,
            profit_factor=base_report.profit_factor,
        )
        score = calculate_absolute_score(report)
        scores.append(score)

    # Verify monotonic decreasing: worse drawdown → lower score
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1], (
            f"Score increased with worse drawdown: "
            f"dd={drawdowns[i]} score={scores[i]:.4f}, "
            f"dd={drawdowns[i+1]} score={scores[i+1]:.4f}"
        )


def test_drawdown_scoring_bounds():
    """Verify drawdown score is bounded [0, 1]."""
    base_report = ResearchReport(
        experiment_id="test",
        total_signals=100,
        win_rate=0.6,
        average_return=0.05,
        total_return=5.0,
        max_drawdown=0.0,
        sharpe_ratio=1.5,
        sortino_ratio=1.5,
        profit_factor=2.0,
    )

    test_drawdowns = [0.0, -10.0, -50.0, -100.0, -150.0]

    for dd in test_drawdowns:
        report = ResearchReport(
            experiment_id=base_report.experiment_id,
            total_signals=base_report.total_signals,
            win_rate=base_report.win_rate,
            average_return=base_report.average_return,
            total_return=base_report.total_return,
            max_drawdown=dd,
            sharpe_ratio=base_report.sharpe_ratio,
            sortino_ratio=base_report.sortino_ratio,
            profit_factor=base_report.profit_factor,
        )
        score = calculate_absolute_score(report)
        assert 0.0 <= score <= 1.0, f"Score {score} out of bounds for drawdown {dd}"


def test_drawdown_scoring_zero():
    """Verify zero drawdown produces maximum drawdown component."""
    report = ResearchReport(
        experiment_id="test",
        total_signals=100,
        win_rate=0.6,
        average_return=0.05,
        total_return=5.0,
        max_drawdown=0.0,
        sharpe_ratio=1.5,
        sortino_ratio=1.5,
        profit_factor=2.0,
    )

    score_zero = calculate_absolute_score(report)

    report_with_drawdown = ResearchReport(
        experiment_id="test",
        total_signals=100,
        win_rate=0.6,
        average_return=0.05,
        total_return=5.0,
        max_drawdown=-10.0,
        sharpe_ratio=1.5,
        sortino_ratio=1.5,
        profit_factor=2.0,
    )

    score_with_drawdown = calculate_absolute_score(report_with_drawdown)

    assert score_zero > score_with_drawdown, "Zero drawdown should score higher"


def test_drawdown_realistic_negative_values():
    """Test with realistic negative drawdown values."""
    test_cases = [
        (0.0, "no drawdown"),
        (-5.0, "5% drawdown"),
        (-15.0, "15% drawdown"),
        (-30.0, "30% drawdown"),
        (-50.0, "50% drawdown"),
    ]

    previous_score = None

    for dd, label in test_cases:
        report = ResearchReport(
            experiment_id=f"test_{label}",
            total_signals=100,
            win_rate=0.6,
            average_return=0.05,
            total_return=5.0,
            max_drawdown=dd,
            sharpe_ratio=1.5,
            sortino_ratio=1.5,
            profit_factor=2.0,
        )

        score = calculate_absolute_score(report)

        # Score must be bounded
        assert 0.0 <= score <= 1.0, f"{label}: score {score} out of bounds"

        # Score must be monotonic
        if previous_score is not None:
            assert score <= previous_score, (
                f"{label}: score {score} increased from previous {previous_score}"
            )

        previous_score = score
