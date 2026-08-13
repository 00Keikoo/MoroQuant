"""Regression test for trade mapping bug fix (Sprint 3.9D-14 Phase 1)."""

from ml_service.research.experiment_engine.engine import apply_strategy_config
from ml_service.research.experiment_engine.types import StrategyConfig
from ml_service.research.replay_engine.types import ReplayResult
from ml_service.research.snapshot_engine.types import Snapshot


def test_trade_mapping_uses_signal_id_not_id():
    """Verify trade mapping uses signal_id for lookup, not id.

    Regression test: the bug was that trade_map keyed by trade['id']
    but lookups used decision['signal_id'], causing PnL to be zero
    when id != signal_id.
    """
    snapshot = Snapshot(
        snapshot_id="test-snapshot-1",
        timestamp="2024-01-01T12:00:00Z",
        trades=[
            {
                "id": "trade-001",
                "signal_id": "signal-001",
                "symbol": "AAPL",
                "pnl": 150.0
            },
            {
                "id": "trade-002",
                "signal_id": "signal-002",
                "symbol": "GOOGL",
                "pnl": -50.0
            }
        ],
        signals=[]
    )

    replay_result = ReplayResult(
        snapshot_id="test-snapshot-1",
        decisions=[
            {
                "signal_id": "signal-001",
                "symbol": "AAPL",
                "prob_long": 0.7,
                "prob_short": 0.1,
                "prob_neutral": 0.2,
                "executed": True
            },
            {
                "signal_id": "signal-002",
                "symbol": "GOOGL",
                "prob_long": 0.1,
                "prob_short": 0.7,
                "prob_neutral": 0.2,
                "executed": True
            }
        ],
        signal_reproduction_rate=1.0,
        execution_alignment_rate=1.0,
        divergence_count=0,
        notes=[],
        consistency_score=0.95,
        divergence_score=0.05
    )

    config = StrategyConfig(
        config_id="test-config-1",
        threshold_long=0.6,
        threshold_short=0.6,
        enable_filter=False
    )

    result = apply_strategy_config(replay_result, snapshot, config)

    assert result.pnl == 100.0, f"Expected PnL=100.0, got {result.pnl}"
    assert result.trade_count == 2, f"Expected 2 trades, got {result.trade_count}"
    assert result.winrate > 0.0, f"Expected non-zero winrate, got {result.winrate}"
