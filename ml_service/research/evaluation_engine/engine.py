"""Core evaluation engine logic."""

import math
from typing import List

from ml_service.research.experiment_engine.types import StrategyResult, ExperimentResult
from ml_service.research.evaluation_engine.types import StrategyScore, EvaluationResult


def compute_strategy_score(result: StrategyResult) -> StrategyScore:
    """Compute enriched metrics and final score for a single strategy.

    Args:
        result: Strategy result from experiment engine

    Returns:
        StrategyScore with all computed metrics
    """
    total_return = result.pnl
    win_rate = result.winrate
    sharpe_ratio = result.sharpe
    max_drawdown = result.max_drawdown
    trade_count = result.trade_count

    expectancy = total_return / trade_count if trade_count > 0 else 0.0

    profit_factor = result.profit_factor if result.profit_factor is not None else _estimate_profit_factor(
        pnl=total_return,
        winrate=win_rate,
        trade_count=trade_count
    )

    sortino_ratio = _estimate_sortino_ratio(sharpe_ratio)

    final_score = _compute_final_score(
        sharpe=sharpe_ratio,
        winrate=win_rate,
        profit_factor=profit_factor,
        total_return=total_return,
        max_drawdown=max_drawdown
    )

    return StrategyScore(
        config_id=result.config_id,
        total_return=total_return,
        win_rate=win_rate,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        trade_count=trade_count,
        profit_factor=profit_factor,
        sortino_ratio=sortino_ratio,
        expectancy=expectancy,
        final_score=final_score
    )


def evaluate_experiment(experiment_result: ExperimentResult) -> EvaluationResult:
    """Evaluate all strategies in an experiment and rank them.

    Args:
        experiment_result: Complete experiment result from experiment engine

    Returns:
        EvaluationResult with ranked strategies
    """
    if not experiment_result.results:
        return EvaluationResult(
            experiment_id=experiment_result.experiment_id,
            strategy_scores=[],
            ranking=[],
            best_strategy_id="",
            worst_strategy_id="",
            overall_risk_score=0.0
        )

    strategy_scores = [
        compute_strategy_score(result)
        for result in experiment_result.results
    ]

    sorted_scores = sorted(
        strategy_scores,
        key=lambda x: x.final_score,
        reverse=True
    )

    ranking = [score.config_id for score in sorted_scores]
    best_strategy_id = sorted_scores[0].config_id
    worst_strategy_id = sorted_scores[-1].config_id

    overall_risk_score = _compute_overall_risk_score(sorted_scores)

    return EvaluationResult(
        experiment_id=experiment_result.experiment_id,
        strategy_scores=strategy_scores,
        ranking=ranking,
        best_strategy_id=best_strategy_id,
        worst_strategy_id=worst_strategy_id,
        overall_risk_score=overall_risk_score
    )


def _estimate_profit_factor(pnl: float, winrate: float, trade_count: int) -> float:
    """Estimate profit factor from aggregate metrics.

    Note: This is a fallback estimation when individual trade PnLs are not available.
    The experiment_engine should ideally provide profit_factor directly.

    Args:
        pnl: Total PnL
        winrate: Win rate (0.0 to 1.0)
        trade_count: Number of trades

    Returns:
        Estimated profit factor (fallback estimation, not actual calculation)
    """
    if trade_count == 0:
        return 1.0

    if winrate >= 1.0:
        return 10.0 if pnl > 0 else 1.0

    if winrate == 0.0:
        return 0.1 if pnl < 0 else 1.0

    avg_pnl_per_trade = pnl / trade_count

    wins = trade_count * winrate
    losses = trade_count * (1.0 - winrate)

    if losses == 0:
        return 10.0 if pnl > 0 else 1.0

    if pnl <= 0:
        return max(0.1, 1.0 + (pnl / abs(pnl + 1)))

    avg_win = avg_pnl_per_trade / winrate if winrate > 0 else 0
    avg_loss = avg_pnl_per_trade / (winrate - 1.0) if winrate < 1.0 else 0

    gross_profit = wins * avg_win
    gross_loss = abs(losses * avg_loss)

    if gross_loss == 0:
        return 10.0 if gross_profit > 0 else 1.0

    return max(0.1, gross_profit / gross_loss)


def _estimate_sortino_ratio(sharpe_ratio: float) -> float:
    """Placeholder Sortino ratio estimation.

    Limitation: Proper Sortino calculation requires the full return series
    to compute downside deviation. The current contract (StrategyResult)
    only provides aggregate metrics, not individual returns.

    For now, we return the Sharpe ratio as a conservative approximation.
    A future enhancement would pass return series through StrategyResult
    to enable proper Sortino calculation.

    Args:
        sharpe_ratio: Sharpe ratio

    Returns:
        Sharpe ratio (conservative placeholder until return series available)
    """
    return sharpe_ratio


def _compute_final_score(
    sharpe: float,
    winrate: float,
    profit_factor: float,
    total_return: float,
    max_drawdown: float
) -> float:
    """Compute risk-adjusted composite score.

    Formula:
        final_score =
            0.25 * sharpe +
            0.20 * winrate +
            0.20 * profit_factor +
            0.20 * normalized_return +
            0.15 * (-max_drawdown)

    All inputs normalized to comparable scales.

    Args:
        sharpe: Sharpe ratio
        winrate: Win rate (0.0 to 1.0)
        profit_factor: Profit factor
        total_return: Total return (PnL)
        max_drawdown: Maximum drawdown (negative value)

    Returns:
        Composite score (higher is better)
    """
    norm_sharpe = _normalize_sharpe(sharpe)
    norm_winrate = winrate
    norm_profit_factor = _normalize_profit_factor(profit_factor)
    norm_return = _normalize_return(total_return)
    norm_drawdown = _normalize_drawdown(max_drawdown)

    final_score = (
        0.25 * norm_sharpe +
        0.20 * norm_winrate +
        0.20 * norm_profit_factor +
        0.20 * norm_return +
        0.15 * (-norm_drawdown)
    )

    return final_score


def _normalize_sharpe(sharpe: float) -> float:
    """Normalize Sharpe ratio to 0-1 scale.

    Sharpe > 3 is excellent, use sigmoid normalization.
    """
    return 1.0 / (1.0 + math.exp(-sharpe))


def _normalize_profit_factor(pf: float) -> float:
    """Normalize profit factor to 0-1 scale.

    PF > 2 is excellent, use sigmoid normalization.
    """
    if pf <= 0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-(pf - 1.0)))


def _normalize_return(return_val: float) -> float:
    """Normalize return to 0-1 scale.

    Use sigmoid for unbounded returns.
    """
    return 1.0 / (1.0 + math.exp(-return_val / 1000.0))


def _normalize_drawdown(dd: float) -> float:
    """Normalize max drawdown to 0-1 scale.

    Drawdown is negative, closer to 0 is better.
    """
    return 1.0 / (1.0 + math.exp(dd / 100.0))


def _compute_overall_risk_score(scores: List[StrategyScore]) -> float:
    """Compute overall risk score across all strategies.

    Uses average of top strategy's metrics weighted by volatility.

    Args:
        scores: List of strategy scores (sorted best to worst)

    Returns:
        Overall risk score
    """
    if not scores:
        return 0.0

    best = scores[0]

    risk_score = (
        0.4 * (1.0 - abs(best.max_drawdown) / 100.0) +
        0.3 * best.sharpe_ratio / 3.0 +
        0.3 * best.win_rate
    )

    return max(0.0, min(1.0, risk_score))
