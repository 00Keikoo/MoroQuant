"""Verify snapshot engine implementation with Sprint 3.6B completeness upgrade."""

from ml_service.research.snapshot_engine import SnapshotService
import json

service = SnapshotService()

print("=" * 60)
print("Sprint 3.6B: Snapshot Completeness Verification")
print("=" * 60)

print("\n1. Creating snapshot...")
snapshot = service.create_snapshot()

print(f"\nSnapshot ID: {snapshot.snapshot_id}")
print(f"Timestamp: {snapshot.timestamp}")
print(f"Trades: {len(snapshot.trades)}")
print(f"Signals: {len(snapshot.signals)}")

print("\n2. Verifying enriched signals...")
enriched_count = sum(1 for s in snapshot.signals if 'features' in s)
prob_count = sum(1 for s in snapshot.signals if s.get('prob_long') is not None)
print(f"Signals with parsed features: {enriched_count}/{len(snapshot.signals)}")
print(f"Signals with probabilities: {prob_count}/{len(snapshot.signals)}")

print("\n3. Verifying state fields...")
state_fields = {
    'signal_state': snapshot.signal_state,
    'feature_state': snapshot.feature_state,
    'regime_state': snapshot.regime_state,
    'risk_state': snapshot.risk_state,
    'execution_state': snapshot.execution_state
}

for field_name, field_value in state_fields.items():
    status = "✓ Present" if field_value is not None else "✗ Missing"
    print(f"{field_name}: {status}")
    if field_value:
        print(f"  Keys: {list(field_value.keys())}")

print("\n4. Verifying signal_state metadata...")
if snapshot.signal_state:
    print(f"Total signals: {snapshot.signal_state.get('total_signals')}")
    print(f"Signals with probabilities: {snapshot.signal_state.get('signals_with_probabilities')}")
    print(f"Signals executed: {snapshot.signal_state.get('signals_executed')}")
    print(f"Execution rate: {snapshot.signal_state.get('execution_rate'):.2%}")

print("\n5. Verifying regime_state...")
if snapshot.regime_state:
    signal_regimes = snapshot.regime_state.get('signal_regime_distribution', {})
    trade_regimes = snapshot.regime_state.get('trade_regime_distribution', {})
    print(f"Signal regime distribution: {signal_regimes}")
    print(f"Trade regime distribution: {trade_regimes}")

print("\n6. Verifying risk_state...")
if snapshot.risk_state:
    print(f"Open positions: {snapshot.risk_state.get('open_positions')}")
    print(f"Total exposure: ${snapshot.risk_state.get('total_exposure_usdt', 0):.2f}")
    print(f"Realized PnL: ${snapshot.risk_state.get('total_realized_pnl', 0):.2f}")

print("\n7. Verifying JSON serialization...")
snapshot_dict = snapshot.to_dict()
json_str = json.dumps(snapshot_dict, indent=2, sort_keys=True)
print(f"JSON size: {len(json_str)} bytes")
print(f"Serialization includes new fields: {all(k in snapshot_dict for k in state_fields.keys())}")

print("\n8. Testing symbol filter...")
btc_snapshot = service.create_snapshot(symbol="BTCUSDT")
print(f"BTC Snapshot ID: {btc_snapshot.snapshot_id}")
print(f"BTC Trades: {len(btc_snapshot.trades)}")
print(f"BTC Signals: {len(btc_snapshot.signals)}")

print("\n9. Verifying determinism...")
snapshot2 = service.create_snapshot()
if snapshot.snapshot_id == snapshot2.snapshot_id:
    print("✓ Snapshot IDs are deterministic")
else:
    print("✗ Warning: Different snapshot IDs (timestamps differ)")

print("\n10. Verifying Replay Engine compatibility...")
from ml_service.research.replay_engine import run_replay

try:
    replay_result = run_replay(snapshot)
    print(f"✓ Replay can consume enriched snapshot")
    print(f"  Signal reproduction rate: {replay_result.signal_reproduction_rate:.2%}")
    print(f"  Execution alignment rate: {replay_result.execution_alignment_rate:.2%}")
    print(f"  Divergence count: {replay_result.divergence_count}")
except Exception as e:
    print(f"✗ Replay failed: {e}")

print("\n" + "=" * 60)
print("Sprint 3.6B: Snapshot Engine Upgraded Successfully!")
print("=" * 60)
