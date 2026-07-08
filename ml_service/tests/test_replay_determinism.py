"""Test deterministic replay behavior: same snapshot produces identical results."""

import pytest
from ml_service.research.snapshot_engine.types import Snapshot
from ml_service.research.replay_engine.replay import run_replay


def test_replay_determinism():
    """Same snapshot twice produces identical decisions and metrics."""

    snapshot = Snapshot(
        snapshot_id="test_determinism_001",
        timestamp='2026-07-08T10:20:00Z',
        signals=[
            {
                'id': 'sig_1',
                'symbol': 'BTCUSDT',
                'prob_long': 0.7,
                'prob_short': 0.2,
                'prob_neutral': 0.1,
                'regime': 'trending',
                'features': {}
            },
            {
                'id': 'sig_2',
                'symbol': 'ETHUSDT',
                'prob_long': 0.3,
                'prob_short': 0.6,
                'prob_neutral': 0.1,
                'regime': 'ranging',
                'features': {}
            },
            {
                'id': 'sig_3',
                'symbol': 'BNBUSDT',
                'prob_long': 0.4,
                'prob_short': 0.3,
                'prob_neutral': 0.3,
                'regime': 'choppy',
                'features': {}
            }
        ],
        trades=[
            {
                'id': 'trade_1',
                'signal_id': 'sig_1',
                'direction': 'LONG',
                'pnl': 150.0
            },
            {
                'id': 'trade_2',
                'signal_id': 'sig_2',
                'direction': 'SHORT',
                'pnl': -50.0
            }
        ]
    )

    result_1 = run_replay(snapshot, threshold_long=0.5, threshold_short=0.5)
    result_2 = run_replay(snapshot, threshold_long=0.5, threshold_short=0.5)

    assert result_1.snapshot_id == result_2.snapshot_id
    assert result_1.signal_reproduction_rate == result_2.signal_reproduction_rate
    assert result_1.execution_alignment_rate == result_2.execution_alignment_rate
    assert result_1.divergence_count == result_2.divergence_count
    assert result_1.consistency_score == result_2.consistency_score
    assert result_1.divergence_score == result_2.divergence_score

    assert len(result_1.decisions) == len(result_2.decisions)

    for dec_1, dec_2 in zip(result_1.decisions, result_2.decisions):
        assert dec_1['signal_id'] == dec_2['signal_id']
        assert dec_1['reconstructed_signal'] == dec_2['reconstructed_signal']
        assert dec_1['original_signal'] == dec_2['original_signal']
        assert dec_1['decision_match'] == dec_2['decision_match']
        assert dec_1['confidence'] == dec_2['confidence']
        assert dec_1['threshold_used'] == dec_2['threshold_used']
        assert dec_1['reason_codes'] == dec_2['reason_codes']
        assert dec_1['divergence_reason'] == dec_2['divergence_reason']


def test_replay_argmax_decision_logic():
    """Verify replay uses argmax logic matching production."""

    snapshot = Snapshot(
        snapshot_id="test_argmax_001",
        timestamp='2026-07-08T10:20:00Z',
        signals=[
            {
                'id': 'sig_long',
                'symbol': 'BTCUSDT',
                'prob_long': 0.6,
                'prob_short': 0.3,
                'prob_neutral': 0.1,
                'regime': 'trending'
            },
            {
                'id': 'sig_short',
                'symbol': 'ETHUSDT',
                'prob_long': 0.2,
                'prob_short': 0.7,
                'prob_neutral': 0.1,
                'regime': 'trending'
            },
            {
                'id': 'sig_neutral',
                'symbol': 'BNBUSDT',
                'prob_long': 0.3,
                'prob_short': 0.3,
                'prob_neutral': 0.4,
                'regime': 'choppy'
            }
        ],
        trades=[]
    )

    result = run_replay(snapshot)

    decisions_map = {d['signal_id']: d for d in result.decisions}

    assert decisions_map['sig_long']['reconstructed_signal'] == 'LONG'
    assert 'ARGMAX_LONG' in decisions_map['sig_long']['reason_codes']

    assert decisions_map['sig_short']['reconstructed_signal'] == 'SHORT'
    assert 'ARGMAX_SHORT' in decisions_map['sig_short']['reason_codes']

    assert decisions_map['sig_neutral']['reconstructed_signal'] == 'HOLD'
    assert 'ARGMAX_NEUTRAL' in decisions_map['sig_neutral']['reason_codes']


def test_replay_decision_parity_fields():
    """Verify all decision parity fields are present in replay output."""

    snapshot = Snapshot(
        snapshot_id="test_parity_001",
        timestamp='2026-07-08T10:20:00Z',
        signals=[
            {
                'id': 'sig_1',
                'symbol': 'BTCUSDT',
                'prob_long': 0.7,
                'prob_short': 0.2,
                'prob_neutral': 0.1
            }
        ],
        trades=[
            {
                'id': 'trade_1',
                'signal_id': 'sig_1',
                'direction': 'LONG'
            }
        ]
    )

    result = run_replay(snapshot)

    assert len(result.decisions) == 1
    decision = result.decisions[0]

    required_fields = [
        'original_signal',
        'reconstructed_signal',
        'decision_match',
        'reason_codes',
        'divergence_reason'
    ]

    for field in required_fields:
        assert field in decision, f"Missing required field: {field}"

    assert decision['original_signal'] == 'LONG'
    assert decision['reconstructed_signal'] == 'LONG'
    assert decision['decision_match'] is True
    assert isinstance(decision['reason_codes'], list)
    assert decision['divergence_reason'] is None


def test_replay_divergence_reasons():
    """Verify divergence reasons are correctly identified."""

    snapshot = Snapshot(
        snapshot_id="test_divergence_001",
        timestamp='2026-07-08T10:20:00Z',
        signals=[
            {
                'id': 'sig_hold_but_executed',
                'symbol': 'BTCUSDT',
                'prob_long': 0.3,
                'prob_short': 0.3,
                'prob_neutral': 0.4
            },
            {
                'id': 'sig_long_but_not_executed',
                'symbol': 'ETHUSDT',
                'prob_long': 0.7,
                'prob_short': 0.2,
                'prob_neutral': 0.1
            }
        ],
        trades=[
            {
                'id': 'trade_1',
                'signal_id': 'sig_hold_but_executed',
                'direction': 'LONG'
            }
        ]
    )

    result = run_replay(snapshot)

    decisions_map = {d['signal_id']: d for d in result.decisions}

    hold_decision = decisions_map['sig_hold_but_executed']
    assert hold_decision['decision_match'] is False
    assert hold_decision['divergence_reason'] == 'REPLAY_HOLD_BUT_PRODUCTION_EXECUTED_LONG'

    long_decision = decisions_map['sig_long_but_not_executed']
    assert long_decision['decision_match'] is False
    assert long_decision['divergence_reason'] == 'REPLAY_LONG_BUT_PRODUCTION_NOT_EXECUTED'
