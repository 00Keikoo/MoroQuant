"""Test snapshot purity - replay operates without database access.

Sprint 3.6E Integration Test
Verifies replay pipeline is truly snapshot-pure and doesn't require live database.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from ml_service.research.snapshot_engine.types import Snapshot
from ml_service.research.replay_engine.replay import run_replay
from ml_service.research.execution_parity.checker import ExecutionParityChecker


def test_replay_without_database_file():
    """Verify replay works when database file doesn't exist."""

    # Create minimal snapshot
    snapshot = Snapshot(
        snapshot_id="test_purity_001",
        timestamp='2026-07-08T12:00:00Z',
        signals=[
            {
                'id': 'sig_1',
                'symbol': 'BTCUSDT',
                'prob_long': 0.7,
                'prob_short': 0.2,
                'prob_neutral': 0.1,
                'regime': 'trending',
                'confidence': 60
            }
        ],
        trades=[],
        account_state={'balance': 10000.0, 'equity': 10000.0},
        position_state={'open_positions': [], 'recent_sl_hits': [], 'open_count': 0},
        execution_constraints={'min_execution_confidence': 55, 'min_probability_edge': 0.2},
        regime_statistics={}
    )

    # Replay should work without database
    result = run_replay(snapshot)

    assert result is not None
    assert result.snapshot_id == "test_purity_001"
    assert len(result.decisions) == 1


def test_execution_parity_checker_without_database():
    """Verify ExecutionParityChecker operates purely from snapshot."""

    snapshot = Snapshot(
        snapshot_id="test_purity_002",
        timestamp='2026-07-08T12:00:00Z',
        signals=[],
        trades=[],
        account_state={'balance': 10000.0, 'equity': 10000.0},
        position_state={'open_positions': [], 'recent_sl_hits': [], 'open_count': 0},
        execution_constraints={
            'min_execution_confidence': 55,
            'min_probability_edge': 0.2,
            'max_open_positions': 3,
            'cooldown_after_sl_hours': 6
        },
        regime_statistics={
            'trending': {'status': 'permitted', 'mean_return': 0.5, 'lci': 0.1, 'uci': 0.9}
        }
    )

    checker = ExecutionParityChecker(snapshot)

    # Test signal
    signal = {
        'symbol': 'BTCUSDT',
        'confidence': 60,
        'prob_long': 0.7,
        'prob_short': 0.2,
        'prob_neutral': 0.1,
        'regime': 'trending'
    }

    # Should work without database
    result = checker.check_execution(signal, 'LONG')

    assert result is not None
    assert result.execution_allowed is True


def test_snapshot_serialization_roundtrip():
    """Verify snapshot can be serialized and deserialized for storage."""

    import json

    snapshot = Snapshot(
        snapshot_id="test_serialize_001",
        timestamp='2026-07-08T12:00:00Z',
        signals=[
            {'id': 'sig_1', 'symbol': 'BTCUSDT', 'prob_long': 0.6, 'prob_short': 0.3, 'prob_neutral': 0.1}
        ],
        trades=[
            {'id': 'trade_1', 'signal_id': 'sig_1', 'direction': 'LONG', 'pnl': 100.0}
        ],
        account_state={'balance': 10100.0, 'equity': 10100.0},
        position_state={'open_positions': [], 'recent_sl_hits': [], 'open_count': 0},
        execution_constraints={'min_execution_confidence': 55}
    )

    # Serialize
    snapshot_dict = snapshot.to_dict()
    json_str = json.dumps(snapshot_dict, sort_keys=True)

    # Deserialize
    restored_dict = json.loads(json_str)
    restored = Snapshot(**restored_dict)

    # Run replay on both
    result1 = run_replay(snapshot)
    result2 = run_replay(restored)

    # Results should be identical
    assert result1.signal_reproduction_rate == result2.signal_reproduction_rate
    assert result1.execution_alignment_rate == result2.execution_alignment_rate
    assert len(result1.decisions) == len(result2.decisions)


def test_replay_determinism_with_snapshot():
    """Verify same snapshot produces identical replay results."""

    snapshot = Snapshot(
        snapshot_id="test_determinism_snapshot",
        timestamp='2026-07-08T12:00:00Z',
        signals=[
            {
                'id': 'sig_1',
                'symbol': 'BTCUSDT',
                'prob_long': 0.7,
                'prob_short': 0.2,
                'prob_neutral': 0.1
            }
        ],
        trades=[],
        account_state={'balance': 10000.0, 'equity': 10000.0},
        position_state={'open_positions': [], 'recent_sl_hits': [], 'open_count': 0}
    )

    # Run twice
    result1 = run_replay(snapshot)
    result2 = run_replay(snapshot)

    # Compare all fields
    assert result1.snapshot_id == result2.snapshot_id
    assert result1.signal_reproduction_rate == result2.signal_reproduction_rate
    assert result1.execution_alignment_rate == result2.execution_alignment_rate
    assert result1.divergence_count == result2.divergence_count

    # Compare decisions
    assert len(result1.decisions) == len(result2.decisions)
    for d1, d2 in zip(result1.decisions, result2.decisions):
        assert d1 == d2


def test_filter_parity_confidence():
    """Verify confidence filter behaves consistently."""

    snapshot = Snapshot(
        snapshot_id="test_filter_conf",
        timestamp='2026-07-08T12:00:00Z',
        signals=[],
        trades=[],
        account_state={'balance': 10000.0, 'equity': 10000.0},
        position_state={'open_positions': [], 'recent_sl_hits': [], 'open_count': 0},
        execution_constraints={'min_execution_confidence': 55}
    )

    checker = ExecutionParityChecker(snapshot)

    # Test below threshold
    signal_low = {'symbol': 'BTCUSDT', 'confidence': 50}
    result_low = checker._check_confidence(signal_low)
    assert result_low.passed is False
    assert 'below_min' in result_low.reason

    # Test above threshold
    signal_high = {'symbol': 'BTCUSDT', 'confidence': 60}
    result_high = checker._check_confidence(signal_high)
    assert result_high.passed is True


def test_filter_parity_edge():
    """Verify edge filter behaves consistently."""

    snapshot = Snapshot(
        snapshot_id="test_filter_edge",
        timestamp='2026-07-08T12:00:00Z',
        signals=[],
        trades=[],
        account_state={'balance': 10000.0, 'equity': 10000.0},
        position_state={'open_positions': [], 'recent_sl_hits': [], 'open_count': 0},
        execution_constraints={'min_probability_edge': 0.2}
    )

    checker = ExecutionParityChecker(snapshot)

    # Test insufficient edge
    signal_low_edge = {
        'symbol': 'BTCUSDT',
        'prob_long': 0.4,
        'prob_short': 0.35,
        'prob_neutral': 0.25
    }
    result_low = checker._check_edge(signal_low_edge)
    assert result_low.passed is False

    # Test sufficient edge
    signal_high_edge = {
        'symbol': 'BTCUSDT',
        'prob_long': 0.7,
        'prob_short': 0.2,
        'prob_neutral': 0.1
    }
    result_high = checker._check_edge(signal_high_edge)
    assert result_high.passed is True


def test_no_live_db_dependency_in_replay():
    """Verify replay modules have no database imports."""

    import importlib
    import sys

    # Import replay modules
    replay_module = importlib.import_module('ml_service.research.replay_engine.replay')
    parity_module = importlib.import_module('ml_service.research.execution_parity.checker')

    # Check module imports don't include database modules
    replay_imports = [name for name in dir(replay_module) if not name.startswith('_')]
    parity_imports = [name for name in dir(parity_module) if not name.startswith('_')]

    # Should not have repository or sqlite imports
    for module in [replay_module, parity_module]:
        module_str = str(module.__dict__)
        assert 'TradeRepository' not in module_str
        assert 'SignalRepository' not in module_str
        assert 'sqlite3.connect' not in module_str
