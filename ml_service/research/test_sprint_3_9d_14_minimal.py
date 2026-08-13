"""Minimal integration test for Sprint 3.9D-14.

Tests core pipeline without heavy dependencies:
Snapshot → Experiment → Evaluation (metrics calculated correctly)
"""

import sys
sys.path.insert(0, '/home/zafka/trade-dashboard')

from ml_service.research.snapshot_engine.types import Snapshot
from ml_service.research.replay_engine.types import ReplayResult
from ml_service.research.experiment_engine.engine import apply_strategy_config
from ml_service.research.experiment_engine.types import StrategyConfig, ExperimentResult
from ml_service.research.evaluation_engine.engine import evaluate_experiment


def test_pipeline_with_repaired_metrics():
    """Test pipeline with Phase 1-2 fixes: trade mapping and actual metric calculations."""

    # Phase 1 regression: trade.id != trade.signal_id
    snapshot = Snapshot(
        snapshot_id="test-snap-1",
        timestamp="2024-08-13T12:00:00Z",
        trades=[
            {"id": "trade-001", "signal_id": "sig-001", "symbol": "AAPL", "pnl": 250.0},
            {"id": "trade-002", "signal_id": "sig-002", "symbol": "GOOGL", "pnl": -100.0},
            {"id": "trade-003", "signal_id": "sig-003", "symbol": "MSFT", "pnl": 150.0},
            {"id": "trade-004", "signal_id": "sig-004", "symbol": "TSLA", "pnl": -75.0},
            {"id": "trade-005", "signal_id": "sig-005", "symbol": "AMZN", "pnl": 200.0},
        ],
        signals=[]
    )

    replay_result = ReplayResult(
        snapshot_id="test-snap-1",
        decisions=[
            {"signal_id": "sig-001", "symbol": "AAPL", "prob_long": 0.75, "prob_short": 0.1, "prob_neutral": 0.15, "executed": True},
            {"signal_id": "sig-002", "symbol": "GOOGL", "prob_long": 0.2, "prob_short": 0.7, "prob_neutral": 0.1, "executed": True},
            {"signal_id": "sig-003", "symbol": "MSFT", "prob_long": 0.8, "prob_short": 0.1, "prob_neutral": 0.1, "executed": True},
            {"signal_id": "sig-004", "symbol": "TSLA", "prob_long": 0.1, "prob_short": 0.75, "prob_neutral": 0.15, "executed": True},
            {"signal_id": "sig-005", "symbol": "AMZN", "prob_long": 0.85, "prob_short": 0.05, "prob_neutral": 0.1, "executed": True},
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
        threshold_long=0.65,
        threshold_short=0.65,
        enable_filter=False
    )

    # Test Phase 1: Trade mapping works with id != signal_id
    result = apply_strategy_config(replay_result, snapshot, config)

    assert result.pnl == 425.0, f"Phase 1 FAILED: Expected PnL=425.0, got {result.pnl}"
    assert result.trade_count == 5, f"Phase 1 FAILED: Expected 5 trades, got {result.trade_count}"
    assert result.winrate == 0.6, f"Phase 1 FAILED: Expected winrate=0.6, got {result.winrate}"

    # Test Phase 2: Metrics calculated from actual data
    assert result.sharpe != 0.0, "Phase 2 FAILED: Sharpe should be non-zero with actual returns"
    assert result.max_drawdown < 0.0, "Phase 2 FAILED: Max drawdown should be negative with losses"
    assert result.profit_factor is not None, "Phase 2 FAILED: Profit factor should be calculated"
    assert result.profit_factor > 1.0, f"Phase 2 FAILED: Profit factor should be > 1, got {result.profit_factor}"

    # Verify evaluation engine receives and processes metrics
    experiment_result = ExperimentResult(
        experiment_id="test-exp-1",
        snapshot_id="test-snap-1",
        results=[result]
    )

    evaluation = evaluate_experiment(experiment_result)

    assert evaluation.experiment_id == "test-exp-1"
    assert len(evaluation.strategy_scores) == 1
    assert evaluation.best_strategy_id == "test-config-1"

    score = evaluation.strategy_scores[0]
    assert score.total_return == 425.0
    assert score.win_rate == 0.6
    assert score.sharpe_ratio != 0.0
    assert score.profit_factor > 1.0
    assert score.expectancy == 85.0

    print("✓ Sprint 3.9D-14 Integration Test PASSED")
    print(f"  Phase 1: Trade mapping fixed (id != signal_id)")
    print(f"  Phase 2: Metrics calculated from actual trades")
    print(f"    PnL: {result.pnl}")
    print(f"    Win Rate: {result.winrate}")
    print(f"    Sharpe: {result.sharpe:.3f}")
    print(f"    Max Drawdown: {result.max_drawdown:.2f}")
    print(f"    Profit Factor: {result.profit_factor:.2f}")
    print(f"    Trade Count: {result.trade_count}")


if __name__ == "__main__":
    test_pipeline_with_repaired_metrics()
