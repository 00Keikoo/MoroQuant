"""Adapter for converting evaluation results to research reports.

Pure-functional adapter that converts EvaluationResult (from evaluation_engine)
into ResearchReport (for benchmark/promotion pipeline).

ADR-024 compliant: stateless, deterministic, no side effects.
"""

from ml_service.research.evaluation_engine.types import EvaluationResult
from ml_service.research.reporting.models import ResearchReport


def evaluation_to_report(evaluation: EvaluationResult) -> ResearchReport:
    """Convert EvaluationResult to ResearchReport.

    Uses the best strategy from the evaluation as the basis for the report.

    Args:
        evaluation: Evaluation result from evaluation_engine

    Returns:
        ResearchReport with metrics from best strategy

    Raises:
        ValueError: If evaluation has no strategies
    """
    if not evaluation.strategy_scores:
        raise ValueError(f"Cannot create report for evaluation {evaluation.experiment_id}: no strategies")

    best_strategy = next(
        (score for score in evaluation.strategy_scores if score.config_id == evaluation.best_strategy_id),
        evaluation.strategy_scores[0]
    )

    additional_metrics = (
        ("expectancy", best_strategy.expectancy),
        ("final_score", best_strategy.final_score),
        ("overall_risk_score", evaluation.overall_risk_score),
    )

    return ResearchReport(
        experiment_id=evaluation.experiment_id,
        total_signals=best_strategy.trade_count,
        win_rate=best_strategy.win_rate,
        average_return=best_strategy.expectancy,
        total_return=best_strategy.total_return,
        max_drawdown=best_strategy.max_drawdown,
        sharpe_ratio=best_strategy.sharpe_ratio,
        sortino_ratio=best_strategy.sortino_ratio,
        profit_factor=best_strategy.profit_factor,
        metrics=additional_metrics
    )
