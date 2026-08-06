"""Research Benchmark Scoring Engine - Sprint 3.9D-1

Provides isolated mathematical scoring and normalization logic for research report metrics.
"""

from typing import Dict
from ml_service.research.reporting.models import ResearchReport


def calculate_absolute_score(report: ResearchReport) -> float:
    """Calculate absolute composite score for a single ResearchReport.

    Formula weights:
    - 30% Sharpe Ratio (normalized to [0, 3] target range)
    - 20% Sortino Ratio (normalized to [0, 3] target range)
    - 20% Profit Factor (normalized using 1.0 - 1.0/PF)
    - 15% Win Rate (already [0, 1])
    - 15% Drawdown Recovery (1.0 - max_drawdown)
    """
    # 1. Sharpe Ratio Score (scaled against 3.0)
    sharpe_score = min(max(report.sharpe_ratio / 3.0, 0.0), 1.0)

    # 2. Sortino Ratio Score (scaled against 3.0)
    sortino_score = min(max(report.sortino_ratio / 3.0, 0.0), 1.0)

    # 3. Profit Factor Score
    # For PF: inf -> 1.0, <= 1.0 -> 0.0, else 1.0 - 1.0/PF
    if report.profit_factor == float('inf') or report.profit_factor > 100.0:
        profit_factor_score = 1.0
    elif report.profit_factor <= 1.0:
        profit_factor_score = 0.0
    else:
        profit_factor_score = 1.0 - (1.0 / report.profit_factor)

    # 4. Win Rate Score (already 0.0 to 1.0)
    win_rate_score = min(max(report.win_rate, 0.0), 1.0)

    # 5. Drawdown Recovery Score (1.0 - max_drawdown)
    drawdown_recovery_score = max(0.0, 1.0 - report.max_drawdown)

    # Apply Weights
    composite_score = (
        0.30 * sharpe_score +
        0.20 * sortino_score +
        0.20 * profit_factor_score +
        0.15 * win_rate_score +
        0.15 * drawdown_recovery_score
    )

    return float(composite_score)
