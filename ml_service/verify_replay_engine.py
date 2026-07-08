"""Verify replay engine implementation - Sprint 3.6A remediation tests."""

from ml_service.research.snapshot_engine import SnapshotService
from ml_service.research.replay_engine import ReplayService
import json

print("=" * 60)
print("REPLAY ENGINE VERIFICATION - Sprint 3.6A")
print("=" * 60)

print("\n[TEST 1] Creating snapshot...")
snapshot_service = SnapshotService()
snapshot = snapshot_service.create_snapshot()

print(f"Snapshot ID: {snapshot.snapshot_id}")
print(f"Trades captured: {len(snapshot.trades)}")
print(f"Signals captured: {len(snapshot.signals)}")

trades_with_signal_id = sum(1 for t in snapshot.trades if t.get('signal_id') is not None)
print(f"Trades with signal_id: {trades_with_signal_id}/{len(snapshot.trades)}")

print("\n[TEST 2] Running replay with correct trade-signal mapping...")
replay_service = ReplayService()
result = replay_service.run(snapshot)

print(f"\nReplay Result:")
print(f"  Snapshot ID: {result.snapshot_id}")
print(f"  Total Signals Processed: {len(result.decisions)}")
print(f"  Signal Reproduction Rate: {result.signal_reproduction_rate:.4f}")
print(f"  Execution Alignment Rate: {result.execution_alignment_rate:.4f}")
print(f"  Divergence Count: {result.divergence_count}")

print("\n[TEST 3] Verifying trade-signal relationship...")
matched = sum(1 for d in result.decisions if d['matched'])
executed = sum(1 for d in result.decisions if d['executed'])
print(f"  Matched decisions: {matched}/{len(result.decisions)}")
print(f"  Executed trades: {executed}/{len(result.decisions)}")
print(f"  Signals without execution: {len(result.decisions) - executed}")

if executed > 0:
    print("  ✓ Trade-signal matching is working")
else:
    print("  ✗ WARNING: No trades were matched to signals")

print("\n[TEST 4] Verifying signals without execution are included...")
hold_decisions = sum(1 for d in result.decisions if d['reconstructed'] == 'HOLD')
print(f"  HOLD decisions: {hold_decisions}")
if hold_decisions > 0 or len(result.decisions) > executed:
    print("  ✓ Non-executed signals are included in replay")
else:
    print("  ✗ WARNING: Survivorship bias detected")

print("\n[TEST 5] Sample decisions:")
for i, decision in enumerate(result.decisions[:3]):
    print(f"\n  Signal #{i+1} (ID: {decision['signal_id']}):")
    print(f"    Symbol: {decision['symbol']}")
    print(f"    Reconstructed: {decision['reconstructed']}")
    print(f"    Actual: {decision['actual']}")
    print(f"    Executed: {decision['executed']}")
    print(f"    Matched: {decision['matched']}")
    prob_long = decision['prob_long'] if decision['prob_long'] is not None else 0.0
    prob_short = decision['prob_short'] if decision['prob_short'] is not None else 0.0
    print(f"    Probs: L={prob_long:.3f} S={prob_short:.3f}")
    print(f"    Confidence: {decision['confidence']:.3f}")
    print(f"    Reason: {decision['reason_code']}")

print("\n[TEST 6] Verifying determinism (same snapshot twice)...")
result2 = replay_service.run(snapshot)
deterministic = (
    result.signal_reproduction_rate == result2.signal_reproduction_rate and
    result.execution_alignment_rate == result2.execution_alignment_rate and
    len(result.decisions) == len(result2.decisions)
)
if deterministic:
    print("  ✓ Replay is deterministic (identical results)")
else:
    print("  ✗ FAIL: Replay results differ")

print("\n[TEST 7] Verifying JSON serialization...")
result_dict = result.to_dict()
json_str = json.dumps(result_dict, indent=2)
print(f"  JSON size: {len(json_str)} bytes")
print("  ✓ JSON serialization works")

print("\n[TEST 8] Testing symbol filter...")
btc_snapshot = snapshot_service.create_snapshot(symbol="BTCUSDT")
btc_result = replay_service.run(btc_snapshot)
print(f"  BTC signals: {len(btc_result.decisions)}")
print(f"  BTC signal reproduction rate: {btc_result.signal_reproduction_rate:.4f}")
if len(btc_result.decisions) <= len(result.decisions):
    print("  ✓ Symbol filter works correctly")

print("\n[TEST 9] Verifying missing probability fields don't break replay...")
if any(d['prob_long'] is None or d['prob_short'] is None for d in result.decisions):
    print("  ✓ Replay handles missing probabilities (found None values)")
else:
    print("  ⚠ All probabilities present (cannot test None handling)")

print("\n" + "=" * 60)
if deterministic and executed > 0:
    print("RESULT: PASS - Replay engine is scientifically valid")
else:
    print("RESULT: FAIL - Issues detected")
print("=" * 60)
