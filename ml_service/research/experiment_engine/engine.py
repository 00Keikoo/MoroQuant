"""Core experiment engine logic."""

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
        trade_count=metrics['trade_count']
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

    trade_map = {trade.get('id'): trade for trade in snapshot.trades}

    executed_count = 0
    matched_count = 0
    pnl = 0.0

    for decision in decisions:
        if decision.get('executed'):
            executed_count += 1

            trade = trade_map.get(decision.get('signal_id'))
            if trade:
                trade_pnl = trade.get('pnl', 0.0) or 0.0
                pnl += trade_pnl

                if trade_pnl > 0:
                    matched_count += 1

    winrate = matched_count / executed_count if executed_count > 0 else 0.0
    sharpe = 0.0
    max_drawdown = 0.0

    return {
        'pnl': pnl,
        'winrate': winrate,
        'sharpe': sharpe,
        'max_drawdown': max_drawdown,
        'trade_count': executed_count
    }
