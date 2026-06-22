"""Trace promotion flow and identify registry integration gaps."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("PROMOTION FLOW ANALYSIS")
print("=" * 80)
print()

print("STEP 1: compare_and_promote() Flow")
print("-" * 40)
print("1. Load candidate metadata")
print("2. Load production model via get_production_model_path() <- USES REGISTRY")
print("3. Compare metrics (should_promote_model)")
print("4. If approved, call promote_model()")
print()

print("STEP 2: promote_model() Flow")
print("-" * 40)
print("1. Get old production via get_production_model_path() <- USES REGISTRY")
print("2. Archive old production model")
print("3. Copy candidate to production directory")
print("4. Copy calibration file if exists")
print("5. Return success")
print()

print("FINDING:")
print("-" * 40)
print("✗ promote_model() does NOT update active_models.json")
print()
print("Impact:")
print("  - Files copied to production/")
print("  - Registry still points to old model")
print("  - New model not activated")
print("  - Manual registry update required")
print()

print("=" * 80)
print("REGISTRY INTEGRATION GAP IDENTIFIED")
print("=" * 80)
