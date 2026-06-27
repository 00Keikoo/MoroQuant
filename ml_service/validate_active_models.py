"""Validate active production models by attempting signal generation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from models.predictor import generate_signal
from utils.logger import get_logger

logger = get_logger(__name__)

# Target pairs to validate
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
print("ACTIVE MODEL VALIDATION - LIVE SIGNAL GENERATION TEST")
print("=" * 80)
print()

results = []

for symbol, timeframe in TARGET_PAIRS:
    print(f"Testing {symbol} {timeframe}...")

    try:
        signal = generate_signal(symbol, timeframe, n_candles=300, skip_mtf=True, persist=False)

        if signal:
            print(f"  ✓ SUCCESS")
            print(f"    Direction: {signal['direction']}")
            print(f"    Confidence: {signal['confidence']}%")
            print(f"    Model: {signal.get('model_version', 'unknown')}")

            results.append({
                'symbol': symbol,
                'timeframe': timeframe,
                'status': 'SUCCESS',
                'direction': signal['direction'],
                'confidence': signal['confidence'],
                'model_version': signal.get('model_version', 'unknown'),
            })
        else:
            print(f"  ✗ FAILED: No signal returned")
            results.append({
                'symbol': symbol,
                'timeframe': timeframe,
                'status': 'FAILED',
                'error': 'No signal returned',
            })

    except Exception as e:
        print(f"  ✗ FAILED: {str(e)}")
        results.append({
            'symbol': symbol,
            'timeframe': timeframe,
            'status': 'FAILED',
            'error': str(e),
        })

    print()

# Summary
successful = [r for r in results if r['status'] == 'SUCCESS']
failed = [r for r in results if r['status'] == 'FAILED']

print("=" * 80)
print("VALIDATION SUMMARY")
print("=" * 80)
print()
print(f"Successful: {len(successful)}/10")
print(f"Failed: {len(failed)}/10")
print()

if failed:
    print("FAILED MODELS:")
    for r in failed:
        print(f"  - {r['symbol']} {r['timeframe']}")
        print(f"    Error: {r.get('error', 'Unknown')}")
    print()

# Save results
import json
output_file = Path(__file__).parent / 'validation_results.json'
with open(output_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"Results saved to: {output_file}")
