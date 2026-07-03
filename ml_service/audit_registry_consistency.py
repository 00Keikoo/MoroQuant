"""Audit registry consistency - verify all entries have valid files and metadata."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ml_service.models.governance import load_active_models_registry, get_model_directories, load_model_metadata

print("=" * 80)
print("REGISTRY CONSISTENCY AUDIT")
print("=" * 80)
print()

registry = load_active_models_registry()
dirs = get_model_directories()
production_dir = dirs['production']

results = []
pass_count = 0
fail_count = 0

for symbol, timeframes in registry.items():
    for timeframe, filename in timeframes.items():
        print(f"Checking {symbol} {timeframe}: {filename}")

        # Check 1: Registry entry exists
        registry_ok = True

        # Check 2: File exists
        model_path = production_dir / filename
        file_exists = model_path.exists()

        # Check 3: Metadata exists and loadable
        metadata = None
        metadata_ok = False
        if file_exists:
            metadata = load_model_metadata(str(model_path))
            metadata_ok = metadata is not None

        # Overall status
        if registry_ok and file_exists and metadata_ok:
            status = "PASS"
            pass_count += 1
            print(f"  ✓ PASS")
        else:
            status = "FAIL"
            fail_count += 1
            print(f"  ✗ FAIL")
            if not file_exists:
                print(f"    Missing file: {model_path}")
            if not metadata_ok:
                print(f"    Metadata load failed")

        if metadata_ok:
            print(f"    Features: {len(metadata.get('feature_cols', []))}")
            print(f"    Trained: {metadata.get('trained_at', 'unknown')[:10]}")

        print()

        results.append({
            'symbol': symbol,
            'timeframe': timeframe,
            'filename': filename,
            'registry_ok': registry_ok,
            'file_exists': file_exists,
            'metadata_ok': metadata_ok,
            'status': status,
        })

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total entries: {len(results)}")
print(f"PASS: {pass_count}")
print(f"FAIL: {fail_count}")
print()

if fail_count == 0:
    print("✓ ALL REGISTRY ENTRIES VALID")
else:
    print("✗ REGISTRY CONSISTENCY ISSUES FOUND")

# Save results
output_file = Path(__file__).parent / 'registry_consistency_results.json'
with open(output_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\nResults saved to: {output_file}")
