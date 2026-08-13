"""Core experiment engine logic."""

import math
from typing import Dict, Any, List

from ml_service.research.snapshot_engine.types import Snapshot
from ml_service.research.replay_engine.types import ReplayResult
from ml_service.research.experiment_engine.types import StrategyConfig, StrategyResult
from ml_service.research.decision_truth import DecisionEngine, DecisionContext


def apply_strategy_config(
    replay_result: ReplayResult,
    snapshot: Snapshot,
    config: StrategyConfig
) -> StrategyResult:
    """Apply strategy configuration using Decision Truth Layer and compute metrics.

    Args:
        replay_result: Replay result containing decisions
        snapshot: Original snapshot data
        config: Strategy configuration to apply

    Returns:
        StrategyResult with computed metrics
    """
    decision_engine = DecisionEngine(
        threshold_long=config.threshold_long,
        threshold_short=config.threshold_short
    )

    filtered_decisions = []

    for decision in replay_result.decisions:
        signal_id = decision.get('signal_id')
        symbol = decision.get('symbol')
        prob_long = decision.get('prob_long', 0.0) or 0.0
        prob_short = decision.get('prob_short', 0.0) or 0.0
        prob_neutral = decision.get('prob_neutral', 0.0) or 0.0

        context = DecisionContext(
            signal_id=signal_id,
            symbol=symbol,
            probability_long=prob_long,
            probability_short=prob_short,
            probability_neutral=prob_neutral
        )

        decision_result = decision_engine.decide(context)

        if decision_result.action != "HOLD":
            if config.enable_filter and config.regime_filter:
                continue

            filtered_decisions.append({
                **decision,
                'strategy_action': decision_result.action,
                'strategy_confidence': decision_result.confidence,
                'strategy_reason': decision_result.reason_code
            })

    metrics = _compute_metrics(filtered_decisions, snapshot)

    return StrategyResult(
        config_id=config.config_id,
        pnl=metrics['pnl'],
        winrate=metrics['winrate'],
        sharpe=metrics['sharpe'],
        max_drawdown=metrics['max_drawdown'],
        consistency_score=replay_result.consistency_score,
        trade_count=metrics['trade_count'],
        profit_factor=metrics.get('profit_factor')
    )




def _compute_metrics(decisions: List[Dict[str, Any]], snapshot: Snapshot) -> Dict[str, float]:
    """Compute performance metrics from filtered decisions.

    Args:
        decisions: Filtered decisions that would execute
        snapshot: Snapshot containing trade data

    Returns:
        Dictionary of computed metrics
    """
    if not decisions:
        return {
            'pnl': 0.0,
            'winrate': 0.0,
            'sharpe': 0.0,
            'max_drawdown': 0.0,
            'trade_count': 0
        }

    trade_map = {trade.get('signal_id'): trade for trade in snapshot.trades}

    executed_count = 0
    matched_count = 0
    pnl = 0.0
    trade_pnls = []

    for decision in decisions:
        if decision.get('executed'):
            executed_count += 1

            trade = trade_map.get(decision.get('signal_id'))
            if trade:
                trade_pnl = trade.get('pnl', 0.0) or 0.0
                pnl += trade_pnl
                trade_pnls.append(trade_pnl)

                if trade_pnl > 0:
                    matched_count += 1

    winrate = matched_count / executed_count if executed_count > 0 else 0.0
    sharpe = _compute_sharpe_ratio(trade_pnls)
    max_drawdown = _compute_max_drawdown(trade_pnls)
    profit_factor = _compute_profit_factor(trade_pnls)

    return {
        'pnl': pnl,
        'winrate': winrate,
        'sharpe': sharpe,
        'max_drawdown': max_drawdown,
        'profit_factor': profit_factor,
        'trade_count': executed_count
    }


def _compute_sharpe_ratio(returns: List[float]) -> float:
    """Compute Sharpe ratio from return series.

    NOTE: The current StrategyResult contract defines these returns as individual
    trade PnLs, not periodic returns with a known frequency. As a result,
    annualizing by multiplying by sqrt(252) is mathematically indefensible
    as a true annualized Sharpe ratio.
    To preserve compatibility with existing model registry thresholds that expect
    values in the typical annualized range, the scaling factor is retained.
    This represents a known contract limitation.

    Args:
        returns: List of trade returns (PnLs)

    Returns:
        Contract-defined scaled Sharpe ratio (non-annualized but scaled by sqrt(252))
    """
    if not returns or len(returns) < 2:
        return 0.0

    mean_return = sum(returns) / len(returns)

    variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
    std_dev = math.sqrt(variance)

    if std_dev == 0:
        return 0.0

    sharpe = mean_return / std_dev

    return sharpe * math.sqrt(252)


def _compute_max_drawdown(returns: List[float]) -> float:
    """Compute maximum drawdown from return series.

    NOTE: This metric is defined under the domain contract as absolute cumulative
    PnL drawdown (measured in base currency/PnL units), NOT percentage equity drawdown.
    This preserves the existing domain contract and avoids silently mixing the two.

    Args:
        returns: List of trade returns (PnLs)

    Returns:
        Maximum absolute drawdown (negative value representing peak-to-trough decline)
    """
    if not returns:
        return 0.0

    cumulative_returns = []
    cumsum = 0.0
    for r in returns:
        cumsum += r
        cumulative_returns.append(cumsum)

    peak = cumulative_returns[0]
    max_dd = 0.0

    for value in cumulative_returns:
        if value > peak:
            peak = value

        drawdown = value - peak
        if drawdown < max_dd:
            max_dd = drawdown

    return max_dd


def _compute_profit_factor(returns: List[float]) -> float:
    """Compute profit factor from trade returns.

    Args:
        returns: List of trade returns (PnLs)

    Returns:
        Profit factor (gross_profit / abs(gross_loss))
    """
    if not returns:
        return 1.0

    gross_profit = sum(r for r in returns if r > 0)
    gross_loss = sum(r for r in returns if r < 0)

    if gross_loss == 0:
        return 10.0 if gross_profit > 0 else 1.0

    return gross_profit / abs(gross_loss)
