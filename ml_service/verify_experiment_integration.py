"""Verify experiment engine integration with ReplayResult backward compatibility."""

import sys
sys.path.insert(0, '/home/zafka/trade-dashboard')

from ml_service.research.snapshot_engine import SnapshotService
from ml_service.research.replay_engine import ReplayService
from ml_service.research.experiment_engine.engine import apply_strategy_config
from ml_service.research.experiment_engine.types import StrategyConfig

print("=" * 60)
print("EXPERIMENT ENGINE INTEGRATION TEST")
print("=" * 60)

print("\n[TEST 1] Create snapshot...")
snapshot_service = SnapshotService()
snapshot = snapshot_service.create_snapshot(symbol="BTCUSDT")
print(f"Snapshot created: {snapshot.snapshot_id}")
print(f"Trades: {len(snapshot.trades)}, Signals: {len(snapshot.signals)}")

print("\n[TEST 2] Run replay...")
replay_service = ReplayService()
replay_result = replay_service.run(snapshot)
print(f"Replay completed: {len(replay_result.decisions)} decisions")

print("\n[TEST 3] Verify backward compatibility properties exist...")
assert hasattr(replay_result, 'consistency_score'), "Missing consistency_score"
assert hasattr(replay_result, 'divergence_score'), "Missing divergence_score"
print(f"  consistency_score: {replay_result.consistency_score:.4f}")
print(f"  divergence_score: {replay_result.divergence_score:.4f}")
print("  ✓ Backward compatibility properties present")

print("\n[TEST 4] Apply strategy config using ReplayResult...")
config = StrategyConfig(
    config_id="test_config",
    threshold_long=0.6,
    threshold_short=0.6,
    enable_filter=False
)

try:
    strategy_result = apply_strategy_config(replay_result, snapshot, config)
    print(f"  Strategy result created:")
    print(f"    config_id: {strategy_result.config_id}")
    print(f"    pnl: {strategy_result.pnl:.2f}")
    print(f"    winrate: {strategy_result.winrate:.2%}")
    print(f"    consistency_score: {strategy_result.consistency_score:.4f}")
    print(f"    trade_count: {strategy_result.trade_count}")
    print("  ✓ Experiment engine integration works")
except AttributeError as e:
    print(f"  ✗ FAIL: {e}")
    sys.exit(1)

print("\n[TEST 5] Verify consistency_score flows through...")
assert strategy_result.consistency_score == replay_result.consistency_score, \
    "consistency_score not properly propagated"
print(f"  ✓ consistency_score properly propagated from ReplayResult to StrategyResult")

print("\n" + "=" * 60)
print("✓ ALL INTEGRATION TESTS PASSED")
print("=" * 60)
print("\nBackward compatibility restored successfully.")
print("Experiment engine can access consistency_score from ReplayResult.")
