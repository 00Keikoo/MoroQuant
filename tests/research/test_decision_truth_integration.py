"""Integration tests for Decision Truth Layer with Replay and Experiment engines."""

import pytest
from ml_service.research.snapshot_engine.types import Snapshot
from ml_service.research.replay_engine.replay import run_replay
from ml_service.research.experiment_engine.engine import apply_strategy_config
from ml_service.research.experiment_engine.types import StrategyConfig


class TestDecisionTruthIntegration:
    """Test Decision Truth Layer integration with other engines."""

    def test_replay_uses_decision_truth(self):
        """Test that replay engine uses Decision Truth Layer."""
        snapshot = Snapshot(
            snapshot_id="snap1",
            timestamp="2026-07-06T22:00:00Z",
            trades=[
                {"id": "sig1", "direction": "LONG", "pnl": 100.0}
            ],
            signals=[
                {
                    "id": "sig1",
                    "symbol": "BTCUSDT",
                    "prob_long": 0.7,
                    "prob_short": 0.3,
                    "prob_neutral": 0.0
                }
            ]
        )

        result = run_replay(snapshot, threshold_long=0.5, threshold_short=0.5)

        assert result.snapshot_id == "snap1"
        assert len(result.decisions) == 1

        decision = result.decisions[0]
        assert decision["reconstructed"] == "LONG"
        assert decision["confidence"] == 0.7
        assert decision["threshold_used"] == 0.5
        assert "reason_code" in decision

    def test_replay_deterministic_across_calls(self):
        """Test that replay produces identical results for same input."""
        snapshot = Snapshot(
            snapshot_id="snap2",
            timestamp="2026-07-06T22:00:00Z",
            trades=[],
            signals=[
                {
                    "id": "sig1",
                    "symbol": "BTCUSDT",
                    "prob_long": 0.6,
                    "prob_short": 0.4,
                    "prob_neutral": 0.0
                },
                {
                    "id": "sig2",
                    "symbol": "ETHUSDT",
                    "prob_long": 0.3,
                    "prob_short": 0.8,
                    "prob_neutral": 0.0
                }
            ]
        )

        result1 = run_replay(snapshot, threshold_long=0.5, threshold_short=0.5)
        result2 = run_replay(snapshot, threshold_long=0.5, threshold_short=0.5)
        result3 = run_replay(snapshot, threshold_long=0.5, threshold_short=0.5)

        assert result1.decisions == result2.decisions == result3.decisions
        assert result1.consistency_score == result2.consistency_score == result3.consistency_score

    def test_experiment_uses_decision_truth(self):
        """Test that experiment engine uses Decision Truth Layer."""
        snapshot = Snapshot(
            snapshot_id="snap3",
            timestamp="2026-07-06T22:00:00Z",
            trades=[
                {"id": "sig1", "direction": "LONG", "pnl": 50.0}
            ],
            signals=[
                {
                    "id": "sig1",
                    "symbol": "BTCUSDT",
                    "prob_long": 0.7,
                    "prob_short": 0.3,
                    "prob_neutral": 0.0
                }
            ]
        )

        replay_result = run_replay(snapshot, threshold_long=0.5, threshold_short=0.5)

        config = StrategyConfig(
            config_id="cfg1",
            threshold_long=0.6,
            threshold_short=0.6,
            enable_filter=False
        )

        strategy_result = apply_strategy_config(replay_result, snapshot, config)

        assert strategy_result.config_id == "cfg1"
        assert strategy_result.trade_count == 1

    def test_experiment_respects_threshold_config(self):
        """Test that experiment respects strategy threshold configuration."""
        snapshot = Snapshot(
            snapshot_id="snap4",
            timestamp="2026-07-06T22:00:00Z",
            trades=[],
            signals=[
                {
                    "id": "sig1",
                    "symbol": "BTCUSDT",
                    "prob_long": 0.55,
                    "prob_short": 0.45,
                    "prob_neutral": 0.0
                }
            ]
        )

        replay_result = run_replay(snapshot, threshold_long=0.5, threshold_short=0.5)

        low_threshold_config = StrategyConfig(
            config_id="low",
            threshold_long=0.5,
            threshold_short=0.5,
            enable_filter=False
        )

        high_threshold_config = StrategyConfig(
            config_id="high",
            threshold_long=0.7,
            threshold_short=0.7,
            enable_filter=False
        )

        low_result = apply_strategy_config(replay_result, snapshot, low_threshold_config)
        high_result = apply_strategy_config(replay_result, snapshot, high_threshold_config)

        assert low_result.trade_count == 1
        assert high_result.trade_count == 0

    def test_no_side_effects_across_experiments(self):
        """Test that running multiple experiments has no side effects."""
        snapshot = Snapshot(
            snapshot_id="snap5",
            timestamp="2026-07-06T22:00:00Z",
            trades=[],
            signals=[
                {
                    "id": "sig1",
                    "symbol": "BTCUSDT",
                    "prob_long": 0.8,
                    "prob_short": 0.2,
                    "prob_neutral": 0.0
                }
            ]
        )

        replay_result = run_replay(snapshot, threshold_long=0.5, threshold_short=0.5)

        config1 = StrategyConfig(
            config_id="cfg1",
            threshold_long=0.6,
            threshold_short=0.6,
            enable_filter=False
        )

        config2 = StrategyConfig(
            config_id="cfg2",
            threshold_long=0.7,
            threshold_short=0.7,
            enable_filter=False
        )

        result1 = apply_strategy_config(replay_result, snapshot, config1)
        result2 = apply_strategy_config(replay_result, snapshot, config2)
        result1_again = apply_strategy_config(replay_result, snapshot, config1)

        assert result1.trade_count == result1_again.trade_count
        assert result1.config_id == result1_again.config_id
