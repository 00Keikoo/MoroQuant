"""Core replay logic for deterministic decision reconstruction."""

from typing import Dict, Any, List

from ml_service.research.snapshot_engine.types import Snapshot
from ml_service.research.replay_engine.types import ReplayResult
from ml_service.research.decision_truth import DecisionEngine, DecisionContext
from ml_service.research.execution_parity import ExecutionParityChecker


def run_replay(snapshot: Snapshot, threshold_long: float = 0.5, threshold_short: float = 0.5) -> ReplayResult:
    """Run deterministic replay on snapshot data using Decision Truth Layer.

    Args:
        snapshot: Snapshot object containing trades and signals
        threshold_long: Threshold for LONG decisions (default 0.5)
        threshold_short: Threshold for SHORT decisions (default 0.5)

    Returns:
        ReplayResult with decision reconstruction and divergence analysis
    """
    decision_engine = DecisionEngine(threshold_long=threshold_long, threshold_short=threshold_short)
    execution_checker = ExecutionParityChecker(snapshot)

    decisions = []
    notes = []

    matched_decisions = 0
    total_signals = 0
    correctly_predicted_executions = 0
    execution_parity_matches = 0
    total_executed_trades = len([t for t in snapshot.trades if t.get('signal_id') is not None])

    trade_map = {trade.get('signal_id'): trade for trade in snapshot.trades if trade.get('signal_id') is not None}

    for signal in snapshot.signals:
        signal_id = signal.get('id')
        symbol = signal.get('symbol')
        prob_long = signal.get('prob_long', 0.0) or 0.0
        prob_short = signal.get('prob_short', 0.0) or 0.0
        prob_neutral = signal.get('prob_neutral', 0.0) or 0.0

        context = DecisionContext(
            signal_id=signal_id,
            symbol=symbol,
            probability_long=prob_long,
            probability_short=prob_short,
            probability_neutral=prob_neutral,
            regime=signal.get('regime'),
            features=signal.get('features')
        )

        decision_result = decision_engine.decide(context)
        reconstructed_decision = decision_result.action

        execution_result = execution_checker.check_execution(signal, reconstructed_decision)

        corresponding_trade = trade_map.get(signal_id)
        if corresponding_trade:
            actual_decision = corresponding_trade.get('direction', 'UNKNOWN')
            executed = True
        else:
            actual_decision = 'NONE'
            executed = False

        if reconstructed_decision == 'HOLD' and not executed:
            matched = True
        elif reconstructed_decision == actual_decision:
            matched = True
        else:
            matched = False

        if matched:
            matched_decisions += 1

        if executed and reconstructed_decision == actual_decision:
            correctly_predicted_executions += 1

        execution_parity_match = (executed == execution_result.execution_allowed)
        if execution_parity_match:
            execution_parity_matches += 1

        total_signals += 1

        divergence_reason = None
        if not matched:
            if reconstructed_decision == 'HOLD' and executed:
                divergence_reason = f"REPLAY_HOLD_BUT_PRODUCTION_EXECUTED_{actual_decision}"
            elif reconstructed_decision != 'HOLD' and not executed:
                divergence_reason = f"REPLAY_{reconstructed_decision}_BUT_PRODUCTION_NOT_EXECUTED"
            elif reconstructed_decision != actual_decision:
                divergence_reason = f"DIRECTION_MISMATCH_REPLAY_{reconstructed_decision}_PRODUCTION_{actual_decision}"

        decisions.append({
            'signal_id': signal_id,
            'symbol': symbol,
            'original_signal': actual_decision,
            'reconstructed_signal': reconstructed_decision,
            'decision_match': matched,
            'executed': executed,
            'prob_long': prob_long,
            'prob_short': prob_short,
            'prob_neutral': prob_neutral,
            'confidence': decision_result.confidence,
            'threshold_used': decision_result.threshold_used,
            'reason_code': decision_result.reason_code,
            'reason_codes': decision_result.reason_code,
            'divergence_reason': divergence_reason,
            'reconstructed': reconstructed_decision,
            'actual': actual_decision,
            'matched': matched,
            'execution_allowed': execution_result.execution_allowed,
            'execution_block_reason': execution_result.block_reason,
            'execution_parity_match': execution_parity_match,
            'passed_filters': execution_result.passed_filters,
            'position_size': execution_result.position_size,
            'sizing_multiplier': execution_result.sizing_multiplier,
            'risk_check_result': execution_result.risk_check_result,
            'regime_check_result': execution_result.regime_check_result
        })

    signal_reproduction_rate = matched_decisions / total_signals if total_signals > 0 else 0.0
    execution_alignment_rate = correctly_predicted_executions / total_executed_trades if total_executed_trades > 0 else 0.0
    execution_parity_rate = execution_parity_matches / total_signals if total_signals > 0 else 0.0
    divergence_count = total_signals - matched_decisions

    consistency_score = signal_reproduction_rate
    divergence_score = divergence_count / total_signals if total_signals > 0 else 0.0

    if not snapshot.signals:
        notes.append("LIMITATION: No signals in snapshot")

    if not snapshot.trades:
        notes.append("LIMITATION: No executed trades in snapshot")

    if execution_parity_rate < 0.95:
        notes.append(f"WARNING: Execution parity rate {execution_parity_rate:.2%} below 95% threshold")

    return ReplayResult(
        snapshot_id=snapshot.snapshot_id,
        decisions=decisions,
        signal_reproduction_rate=signal_reproduction_rate,
        execution_alignment_rate=execution_alignment_rate,
        divergence_count=divergence_count,
        notes=notes,
        consistency_score=consistency_score,
        divergence_score=divergence_score,
        execution_parity_rate=execution_parity_rate
    )


