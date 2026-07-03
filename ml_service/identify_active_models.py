"""Identify active production models and assess real risk."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ml_service.models.governance import get_production_model_path, load_model_metadata

# Target pairs to check
TARGET_PAIRS = [
    ('BTCUSDT', '1h'),
    ('BTCUSDT', '4h'),
    ('ETHUSDT', '1h'),
    ('ETHUSDT', '4h'),
    ('SOLUSDT', '1h'),
    ('SOLUSDT', '4h'),
    ('BNBUSDT', '1h'),
    ('BNBUSDT', '4h'),
    ('HYPEUSDT', '1h'),
    ('HYPEUSDT', '4h'),
]

print("=" * 80)
print("ACTIVE PRODUCTION MODEL IDENTIFICATION")
print("=" * 80)
print()
print("Selection Logic:")
print("  get_production_model_path() uses:")
print("  - Pattern: {symbol}_{timeframe}_*.pkl")
print("  - Directory: storage/models/production/")
print("  - Selection: max(files, key=lambda p: p.stat().st_mtime)")
print("  - Logic: MOST RECENTLY MODIFIED file wins")
print()
print("=" * 80)
print()

active_models = []

for symbol, timeframe in TARGET_PAIRS:
    print(f"Checking {symbol} {timeframe}...")

    model_path = get_production_model_path(symbol, timeframe)

    if not model_path:
        print(f"  ✗ NO MODEL FOUND")
        print()
        continue

    filename = Path(model_path).name
    metadata = load_model_metadata(model_path)

    if not metadata:
        print(f"  ✗ FAILED TO LOAD METADATA: {filename}")
        print()
        continue

    model_type = metadata.get('model_type', 'unknown')
    trained_at = metadata.get('trained_at', 'unknown')
    feature_cols = metadata.get('feature_cols', [])

    print(f"  ✓ Active: {filename}")
    print(f"    Model type: {model_type}")
    print(f"    Trained: {trained_at}")
    print(f"    Features: {len(feature_cols)}")

    active_models.append({
        'symbol': symbol,
        'timeframe': timeframe,
        'filename': filename,
        'model_path': model_path,
        'model_type': model_type,
        'trained_at': trained_at,
        'feature_count': len(feature_cols),
        'feature_cols': feature_cols,
    })

    print()

print("=" * 80)
print(f"FOUND {len(active_models)} ACTIVE MODELS")
print("=" * 80)

# Save results
import json

output_file = Path(__file__).parent / 'active_models.json'
with open(output_file, 'w') as f:
    json.dump(active_models, f, indent=2)

print(f"\nActive models saved to: {output_file}")
