"""Verify replay determinism with SHA256 hash comparison.

Sprint 3.6E - Determinism Audit
Tests that running replay twice on identical snapshot produces identical results.
"""

import json
import hashlib
from ml_service.research.snapshot_engine import SnapshotService
from ml_service.research.replay_engine import ReplayService

print("=" * 70)
print("SPRINT 3.6E - DETERMINISM AUDIT")
print("=" * 70)

print("\n[STEP 1] Creating snapshot...")
snapshot_service = SnapshotService()
snapshot = snapshot_service.create_snapshot()

print(f"Snapshot ID: {snapshot.snapshot_id}")
print(f"Trades: {len(snapshot.trades)}")
print(f"Signals: {len(snapshot.signals)}")

print("\n[STEP 2] Running replay #1...")
replay_service = ReplayService()
result1 = replay_service.run(snapshot, threshold_long=0.5, threshold_short=0.5)

print(f"Result 1:")
print(f"  Signal Reproduction Rate: {result1.signal_reproduction_rate:.4f}")
print(f"  Execution Alignment Rate: {result1.execution_alignment_rate:.4f}")
print(f"  Execution Parity Rate: {result1.execution_parity_rate:.4f}")
print(f"  Divergence Count: {result1.divergence_count}")
print(f"  Decisions: {len(result1.decisions)}")

print("\n[STEP 3] Running replay #2...")
result2 = replay_service.run(snapshot, threshold_long=0.5, threshold_short=0.5)

print(f"Result 2:")
print(f"  Signal Reproduction Rate: {result2.signal_reproduction_rate:.4f}")
print(f"  Execution Alignment Rate: {result2.execution_alignment_rate:.4f}")
print(f"  Execution Parity Rate: {result2.execution_parity_rate:.4f}")
print(f"  Divergence Count: {result2.divergence_count}")
print(f"  Decisions: {len(result2.decisions)}")

print("\n[STEP 4] Computing SHA256 hashes...")

def serialize_result(result):
    """Serialize replay result to deterministic JSON."""
    result_dict = {
        'snapshot_id': result.snapshot_id,
        'signal_reproduction_rate': result.signal_reproduction_rate,
        'execution_alignment_rate': result.execution_alignment_rate,
        'divergence_count': result.divergence_count,
        'consistency_score': result.consistency_score,
        'divergence_score': result.divergence_score,
        'execution_parity_rate': result.execution_parity_rate,
        'decisions': sorted(result.decisions, key=lambda d: d['signal_id'])
    }

    # Sort keys and use separators for deterministic output
    return json.dumps(result_dict, sort_keys=True, separators=(',', ':'))

json1 = serialize_result(result1)
json2 = serialize_result(result2)

hash1 = hashlib.sha256(json1.encode()).hexdigest()
hash2 = hashlib.sha256(json2.encode()).hexdigest()

print(f"Hash 1: {hash1}")
print(f"Hash 2: {hash2}")

print("\n[STEP 5] Verifying determinism...")
if hash1 == hash2:
    print("✓ PASS: Hashes are identical")
    print("✓ Replay is fully deterministic")
else:
    print("✗ FAIL: Hashes differ")
    print("✗ Replay is NOT deterministic")

    # Find differences
    print("\n[DEBUG] Finding differences...")
    import difflib
    diff = list(difflib.unified_diff(
        json1.splitlines(keepends=True),
        json2.splitlines(keepends=True),
        fromfile='result1',
        tofile='result2',
        lineterm=''
    ))
    if diff:
        print("Differences found:")
        for line in diff[:50]:  # Show first 50 lines
            print(line.rstrip())

print("\n[STEP 6] Field-by-field comparison...")
matches = {
    'snapshot_id': result1.snapshot_id == result2.snapshot_id,
    'signal_reproduction_rate': result1.signal_reproduction_rate == result2.signal_reproduction_rate,
    'execution_alignment_rate': result1.execution_alignment_rate == result2.execution_alignment_rate,
    'divergence_count': result1.divergence_count == result2.divergence_count,
    'consistency_score': result1.consistency_score == result2.consistency_score,
    'divergence_score': result1.divergence_score == result2.divergence_score,
    'execution_parity_rate': result1.execution_parity_rate == result2.execution_parity_rate,
    'decision_count': len(result1.decisions) == len(result2.decisions)
}

for field, match in matches.items():
    status = "✓" if match else "✗"
    print(f"{status} {field}: {match}")

print("\n[STEP 7] Decision-level comparison...")
if len(result1.decisions) == len(result2.decisions):
    mismatches = []
    for i, (d1, d2) in enumerate(zip(result1.decisions, result2.decisions)):
        if d1 != d2:
            mismatches.append((i, d1.get('signal_id'), d1, d2))

    if not mismatches:
        print("✓ All decisions match exactly")
    else:
        print(f"✗ Found {len(mismatches)} decision mismatches")
        for i, sig_id, d1, d2 in mismatches[:5]:
            print(f"\n  Mismatch #{i+1} (signal {sig_id}):")
            for key in d1.keys():
                if d1.get(key) != d2.get(key):
                    print(f"    {key}: {d1.get(key)} != {d2.get(key)}")
else:
    print(f"✗ Decision count mismatch: {len(result1.decisions)} != {len(result2.decisions)}")

print("\n[STEP 8] Testing with different thresholds...")
result3 = replay_service.run(snapshot, threshold_long=0.6, threshold_short=0.4)
result4 = replay_service.run(snapshot, threshold_long=0.6, threshold_short=0.4)

json3 = serialize_result(result3)
json4 = serialize_result(result4)
hash3 = hashlib.sha256(json3.encode()).hexdigest()
hash4 = hashlib.sha256(json4.encode()).hexdigest()

if hash3 == hash4:
    print("✓ Deterministic with different thresholds (0.6, 0.4)")
else:
    print("✗ Non-deterministic with different thresholds")

print("\n" + "=" * 70)
print("DETERMINISM AUDIT COMPLETE")
print("=" * 70)

if hash1 == hash2 and hash3 == hash4:
    print("\n✓ VERDICT: Replay engine is FULLY DETERMINISTIC")
    print("  - Identical snapshots produce identical results")
    print("  - SHA256 hashes match across multiple runs")
    print("  - Determinism holds for different threshold configurations")
else:
    print("\n✗ VERDICT: Replay engine has NON-DETERMINISTIC behavior")
    print("  - Results differ across runs with same inputs")
    print("  - Investigation required")
