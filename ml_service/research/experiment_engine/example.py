"""Example usage of Experiment Engine."""

from ml_service.research.snapshot_engine import Snapshot
from ml_service.research.experiment_engine import (
    ExperimentService,
    ExperimentConfig,
    StrategyConfig
)


def run_example_experiment():
    """Demonstrate experiment engine with mock snapshot."""

    mock_snapshot = Snapshot(
        snapshot_id="snap_001",
        timestamp="2026-07-06T22:11:00Z",
        trades=[
            {"id": "sig_001", "direction": "LONG", "pnl": 100.0},
            {"id": "sig_002", "direction": "SHORT", "pnl": -50.0},
            {"id": "sig_003", "direction": "LONG", "pnl": 75.0}
        ],
        signals=[
            {"id": "sig_001", "symbol": "BTC", "prob_long": 0.8, "prob_short": 0.1, "prob_neutral": 0.1},
            {"id": "sig_002", "symbol": "ETH", "prob_long": 0.2, "prob_short": 0.7, "prob_neutral": 0.1},
            {"id": "sig_003", "symbol": "BTC", "prob_long": 0.6, "prob_short": 0.2, "prob_neutral": 0.2},
            {"id": "sig_004", "symbol": "ETH", "prob_long": 0.3, "prob_short": 0.3, "prob_neutral": 0.4}
        ]
    )

    experiment_config = ExperimentConfig(
        experiment_id="exp_001",
        snapshot_id="snap_001",
        configs=[
            StrategyConfig(
                config_id="conservative",
                threshold_long=0.7,
                threshold_short=0.7,
                enable_filter=False
            ),
            StrategyConfig(
                config_id="moderate",
                threshold_long=0.6,
                threshold_short=0.6,
                enable_filter=False
            ),
            StrategyConfig(
                config_id="aggressive",
                threshold_long=0.5,
                threshold_short=0.5,
                enable_filter=False
            )
        ]
    )

    service = ExperimentService()

    result = service.run_experiment(experiment_config)

    if result:
        print(f"Experiment: {result.experiment_id}")
        print(f"Snapshot: {result.snapshot_id}")
        print("\nResults:")
        for strategy_result in result.results:
            print(f"\n  Config: {strategy_result.config_id}")
            print(f"    PnL: {strategy_result.pnl:.2f}")
            print(f"    Winrate: {strategy_result.winrate:.2%}")
            print(f"    Trade Count: {strategy_result.trade_count}")
            print(f"    Consistency: {strategy_result.consistency_score:.2%}")
    else:
        print("Snapshot not found")


if __name__ == "__main__":
    run_example_experiment()
