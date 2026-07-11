"""Experiment analytics calculation engine.

Pure functions that compute aggregate metrics from experiment domain objects.
No database access, no side effects, no global state.
"""

from dataclasses import dataclass
from typing import List

from ml_service.lab.experiments import ExperimentContract


@dataclass
class ExperimentAnalyticsResult:
    """Calculated aggregate metrics for experiments."""
    total_experiments: int
    completed_experiments: int
    failed_experiments: int
    running_experiments: int
    completion_rate: float
    avg_sharpe_ratio: float
    avg_sortino_ratio: float
    avg_calmar_ratio: float
    avg_profit_factor: float
    avg_win_rate: float
    avg_max_drawdown: float
    avg_ece: float
    avg_brier_score: float
    best_sharpe_run_id: str
    worst_sharpe_run_id: str


def calculate_experiment_analytics(experiments: List[ExperimentContract]) -> ExperimentAnalyticsResult:
    """Calculate aggregate analytics from a list of ExperimentContract objects.

    Pure function with no side effects. All calculations operate on the provided
    experiment list without accessing external state.

    Args:
        experiments: List of ExperimentContract domain objects

    Returns:
        ExperimentAnalyticsResult containing calculated metrics

    Notes:
        - Only completed experiments are included in metric averages
        - Empty list returns zero values for all metrics
        - None values are excluded from averages
    """
    if not experiments:
        return _empty_result()

    total_experiments = len(experiments)
    completed = [e for e in experiments if e.status == 'COMPLETED']
    failed = [e for e in experiments if e.status == 'FAILED']
    running = [e for e in experiments if e.status == 'RUNNING']

    completed_count = len(completed)
    failed_count = len(failed)
    running_count = len(running)

    completion_rate = completed_count / total_experiments if total_experiments > 0 else 0.0

    sharpe_values = [e.sharpe_ratio for e in completed if e.sharpe_ratio is not None]
    sortino_values = [e.sortino_ratio for e in completed if e.sortino_ratio is not None]
    calmar_values = [e.calmar_ratio for e in completed if e.calmar_ratio is not None]
    profit_factor_values = [e.profit_factor for e in completed if e.profit_factor is not None]
    win_rate_values = [e.win_rate for e in completed if e.win_rate is not None]
    max_drawdown_values = [e.max_drawdown for e in completed if e.max_drawdown is not None]
    ece_values = [e.ece for e in completed if e.ece is not None]
    brier_values = [e.brier_score for e in completed if e.brier_score is not None]

    avg_sharpe = sum(sharpe_values) / len(sharpe_values) if sharpe_values else 0.0
    avg_sortino = sum(sortino_values) / len(sortino_values) if sortino_values else 0.0
    avg_calmar = sum(calmar_values) / len(calmar_values) if calmar_values else 0.0
    avg_profit_factor = sum(profit_factor_values) / len(profit_factor_values) if profit_factor_values else 0.0
    avg_win_rate = sum(win_rate_values) / len(win_rate_values) if win_rate_values else 0.0
    avg_max_drawdown = sum(max_drawdown_values) / len(max_drawdown_values) if max_drawdown_values else 0.0
    avg_ece = sum(ece_values) / len(ece_values) if ece_values else 0.0
    avg_brier = sum(brier_values) / len(brier_values) if brier_values else 0.0

    best_sharpe_run_id = ""
    worst_sharpe_run_id = ""
    if sharpe_values:
        experiments_with_sharpe = [e for e in completed if e.sharpe_ratio is not None]
        best_exp = max(experiments_with_sharpe, key=lambda e: e.sharpe_ratio)
        worst_exp = min(experiments_with_sharpe, key=lambda e: e.sharpe_ratio)
        best_sharpe_run_id = best_exp.run_id
        worst_sharpe_run_id = worst_exp.run_id

    return ExperimentAnalyticsResult(
        total_experiments=total_experiments,
        completed_experiments=completed_count,
        failed_experiments=failed_count,
        running_experiments=running_count,
        completion_rate=completion_rate,
        avg_sharpe_ratio=avg_sharpe,
        avg_sortino_ratio=avg_sortino,
        avg_calmar_ratio=avg_calmar,
        avg_profit_factor=avg_profit_factor,
        avg_win_rate=avg_win_rate,
        avg_max_drawdown=avg_max_drawdown,
        avg_ece=avg_ece,
        avg_brier_score=avg_brier,
        best_sharpe_run_id=best_sharpe_run_id,
        worst_sharpe_run_id=worst_sharpe_run_id
    )


def _empty_result() -> ExperimentAnalyticsResult:
    """Return zero-initialized analytics result for empty experiment list."""
    return ExperimentAnalyticsResult(
        total_experiments=0,
        completed_experiments=0,
        failed_experiments=0,
        running_experiments=0,
        completion_rate=0.0,
        avg_sharpe_ratio=0.0,
        avg_sortino_ratio=0.0,
        avg_calmar_ratio=0.0,
        avg_profit_factor=0.0,
        avg_win_rate=0.0,
        avg_max_drawdown=0.0,
        avg_ece=0.0,
        avg_brier_score=0.0,
        best_sharpe_run_id="",
        worst_sharpe_run_id=""
    )
