"""Check active production model compatibility and assess real risk."""

import json
from pathlib import Path

# Load active models
active_file = Path(__file__).parent / 'active_models.json'
with open(active_file, 'r') as f:
    active_models = json.load(f)

# Load full audit results
audit_file = Path(__file__).parent / 'production_model_audit_results.json'
with open(audit_file, 'r') as f:
    audit_results = json.load(f)

# Build lookup from audit
audit_lookup = {r['filename']: r for r in audit_results}

print("=" * 80)
print("ACTIVE MODEL COMPATIBILITY CHECK")
print("=" * 80)
print()

results = []

for active in active_models:
    filename = active['filename']
    symbol = active['symbol']
    timeframe = active['timeframe']

    # Find in audit results
    audit_data = audit_lookup.get(filename)

    if not audit_data:
        print(f"✗ {symbol} {timeframe}: NOT IN AUDIT")
        results.append({
            'symbol': symbol,
            'timeframe': timeframe,
            'filename': filename,
            'status': 'NOT_IN_AUDIT',
            'compatible': None,
            'missing_features': [],
        })
        continue

    compatible = audit_data['compatible']
    missing = audit_data['missing_features']

    if compatible:
        status = "✓ SAFE"
        print(f"{status} {symbol} {timeframe}")
        print(f"  Model: {filename}")
        print(f"  Features: {active['feature_count']}")
    else:
        status = "✗ BROKEN"
        print(f"{status} {symbol} {timeframe}")
        print(f"  Model: {filename}")
        print(f"  Features: {active['feature_count']}")
        print(f"  Missing: {', '.join(missing[:5])}")
        if len(missing) > 5:
            print(f"  ... and {len(missing) - 5} more")

    print()

    results.append({
        'symbol': symbol,
        'timeframe': timeframe,
        'filename': filename,
        'status': status,
        'compatible': compatible,
        'missing_features': missing,
        'feature_count': active['feature_count'],
    })

# Summary
safe = [r for r in results if r['status'] == '✓ SAFE']
broken = [r for r in results if r['status'] == '✗ BROKEN']

print("=" * 80)
print("REAL RISK ASSESSMENT")
print("=" * 80)
print()
print(f"SAFE: {len(safe)}/10")
print(f"BROKEN: {len(broken)}/10")
print()

if broken:
    print("CRITICAL: The following active models are INCOMPATIBLE:")
    print()
    for r in broken:
        print(f"  - {r['symbol']} {r['timeframe']}")
        print(f"    File: {r['filename']}")
        print(f"    Missing: {len(r['missing_features'])} features")
    print()
    print("These models will FAIL during signal generation.")
else:
    print("✓ ALL ACTIVE MODELS ARE COMPATIBLE")

# Save results
output_file = Path(__file__).parent / 'active_compatibility_check.json'
with open(output_file, 'w') as f:
    json.dump(results, f, indent=2)

print()
print(f"Results saved to: {output_file}")
