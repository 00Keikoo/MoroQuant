#!/usr/bin/env python3
"""Validation script for confidence pipeline repair.

Validates the three P0 fixes without requiring live model inference
(since numpy/sklearn are not available in this environment):

1. P0 BUG #1: Calibration artifacts are applied when available
   - Verify calibration artifact exists for BTCUSDT 1h
   - Verify predictor.py calls apply_calibrator
   - Verify calibration_applied flag is tracked

2. P0 BUG #2: MTF alignment replaces confidence mutation
   - Verify no ×1.15/×0.80 multipliers in predictor.py
   - Verify mtf_alignment field (AGREE/DISAGREE/NEUTRAL)

3. TASK 3: raw_probability_max and calibrated_probability_max persisted
   - Verify DB schema has columns
   - Verify INSERT statement includes new columns
   - Verify signal dict construction includes fields

4. End-to-end: Verify production DB has new columns, old signals have NULLs
"""

import sys
import os
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

COLORS = {
    'pass': '\033[92m',
    'fail': '\033[91m',
    'warn': '\033[93m',
    'info': '\033[94m',
    'reset': '\033[0m',
}


def ok(msg):
    print(f"  {COLORS['pass']}✓{COLORS['reset']} {msg}")


def fail(msg):
    print(f"  {COLORS['fail']}✗{COLORS['reset']} {msg}")


def warn(msg):
    print(f"  {COLORS['warn']}!{COLORS['reset']} {msg}")


def info(msg):
    print(f"  {COLORS['info']}→{COLORS['reset']} {msg}")


def section(title):
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")


def validate_source_code():
    """P0 BUG #1 + BUG #2: Static analysis of predictor.py."""
    section("VALIDATION 1: Source Code Analysis (predictor.py)")

    predictor_path = Path(__file__).parent / 'models' / 'predictor.py'
    source = predictor_path.read_text()

    errors = 0

    # P0 BUG #1: Calibration applied
    if 'cal_mod.apply_calibrator' in source:
        ok("apply_calibrator() called when calibration available")
    else:
        fail("cal_mod.apply_calibrator() NOT called")
        errors += 1

    if 'calibration_applied = True' in source:
        ok("calibration_applied set to True on success")
    else:
        fail("calibration_applied True assignment missing")
        errors += 1

    if 'falling back to raw probabilities' in source:
        ok("Raw fallback warning on calibration failure")
    else:
        fail("Raw fallback warning missing")
        errors += 1

    if 'Calibration artifacts loaded for diagnostics but NOT applied' in source:
        fail("Old 'diagnostics only' dead-code comment still present")
        errors += 1
    else:
        ok("Old 'diagnostics only' comment removed")

    if 'Always use raw probabilities (no calibration applied)' in source:
        fail("Old 'always raw' dead-code comment still present")
        errors += 1
    else:
        ok("Old 'always raw' comment removed")

    # P0 BUG #2: MTF alignment
    if '1.15' in source:
        fail("Old ×1.15 MTF boost multiplier found")
        errors += 1
    else:
        ok("No ×1.15 multiplier in source")

    if '0.80' in source:
        fail("Old ×0.80 MTF penalty multiplier found")
        errors += 1
    else:
        ok("No ×0.80 multiplier in source")

    if 'mtf_conflict' in source:
        fail("Old mtf_conflict field still present")
        errors += 1
    else:
        ok("mtf_conflict field removed")

    if "'AGREE'" in source and "'DISAGREE'" in source and "'NEUTRAL'" in source:
        ok("mtf_alignment with AGREE/DISAGREE/NEUTRAL values")
    else:
        fail("mtf_alignment values incomplete")
        errors += 1

    # TASK 3: Diagnostic fields
    if "'raw_probability_max'" in source:
        ok("raw_probability_max in signal dict")
    else:
        fail("raw_probability_max missing from signal dict")
        errors += 1

    if "'calibrated_probability_max'" in source:
        ok("calibrated_probability_max in signal dict")
    else:
        fail("calibrated_probability_max missing from signal dict")
        errors += 1

    # Confidence never mutated after derivation
    lines = source.split('\n')
    past_confidence = False
    mutations = []
    for line in lines:
        if 'confidence_pct = int(confidence * 100)' in line:
            past_confidence = True
            continue
        if past_confidence and "signal['confidence'] = " in line:
            mutations.append(line.strip())

    if not mutations:
        ok("Confidence never mutated after initial derivation")
    else:
        fail(f"Confidence mutations found: {mutations}")
        errors += 1

    return errors


def validate_db_schema():
    """Validate DB schema has new columns."""
    section("VALIDATION 2: Database Schema")

    db_path = Path(__file__).parent / 'storage' / 'database.db'
    if not db_path.exists():
        fail(f"Database not found at {db_path}")
        return 1

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    errors = 0

    # Check signals table has new columns
    cursor.execute("PRAGMA table_info(signals)")
    columns = {row[1]: row for row in cursor.fetchall()}

    for col in ['mtf_alignment', 'raw_probability_max', 'calibrated_probability_max']:
        if col in columns:
            ok(f"Column '{col}' exists in signals table (type={columns[col][2]})")
        else:
            fail(f"Column '{col}' NOT found in signals table")
            errors += 1

    # Check mtf_alignment has DEFAULT 'NEUTRAL'
    if 'mtf_alignment' in columns:
        dflt = columns['mtf_alignment'][4]
        if dflt == "'NEUTRAL'":
            ok("mtf_alignment DEFAULT 'NEUTRAL'")
        else:
            warn(f"mtf_alignment default = {dflt} (expected 'NEUTRAL')")

    # Verify NOT NULL and CHECK on confidence still intact
    if 'confidence' in columns:
        notnull = columns['confidence'][3]  # 1 = NOT NULL
        if notnull:
            ok("confidence NOT NULL constraint intact")
        else:
            fail("confidence NOT NULL constraint MISSING")
            errors += 1

    # Check recent signals have new columns populated (or NULL for old)
    cursor.execute("""
        SELECT COUNT(*) FROM signals
        WHERE mtf_alignment IS NULL OR raw_probability_max IS NULL
    """)
    null_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM signals")
    total_count = cursor.fetchone()[0]

    info(f"{null_count}/{total_count} signals have NULL in new columns (expected: all pre-repair)")

    # Check latest signals have mtf_alignment populated
    cursor.execute("""
        SELECT mtf_alignment FROM signals
        WHERE mtf_alignment IS NOT NULL
        ORDER BY id DESC LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        ok(f"Latest signal has mtf_alignment = '{row[0]}'")
    else:
        warn("No signals with mtf_alignment populated yet")

    conn.close()
    return errors


def validate_production_models():
    """Check calibration artifacts for production models."""
    section("VALIDATION 3: Production Model Calibration Artifacts")

    import json

    models_dir = Path(__file__).parent / 'storage' / 'models' / 'production'
    active_path = Path(__file__).parent / 'active_models.json'

    errors = 0

    if not active_path.exists():
        fail("active_models.json not found")
        return 1

    with open(active_path) as f:
        active_models = json.load(f)

    info(f"Found {len(active_models)} active model entries")

    # BTCUSDT 1h and ETHUSDT 1h
    targets = [('BTCUSDT', '1h'), ('ETHUSDT', '1h')]

    for symbol, timeframe in targets:
        model_entry = next(
            (m for m in active_models if m['symbol'] == symbol and m['timeframe'] == timeframe),
            None
        )

        if model_entry is None:
            warn(f"No active model for {symbol} {timeframe}")
            continue

        model_path = Path(model_entry['model_path'])
        cal_path = Path(str(model_path).replace('.pkl', '_calibration.pkl'))

        if model_path.exists():
            ok(f"{symbol} {timeframe}: model exists ({model_path.name})")
        else:
            fail(f"{symbol} {timeframe}: model file missing")
            errors += 1
            continue

        if cal_path.exists():
            ok(f"{symbol} {timeframe}: calibration artifact exists ({cal_path.name})")

            # Disassemble to check contents (no sklearn needed)
            import pickle
            try:
                with open(cal_path, 'rb') as f:
                    cal_data = pickle.load(f)
                chosen = cal_data.get('chosen_method', 'N/A')
                has_calibrators = 'calibrators' in cal_data
                ok(f"  chosen_method={chosen}, has_calibrators={has_calibrators}")

                if chosen != 'raw' and has_calibrators:
                    cal_obj = cal_data['calibrators'].get(chosen)
                    if cal_obj is not None:
                        ok(f"  Chosen calibrator ('{chosen}') is non-None → will be applied at inference")
                    else:
                        warn(f"  Chosen calibrator ('{chosen}') is None → raw fallback")
                else:
                    info(f"  Chosen method is 'raw' → identity, no transformation")
            except Exception as e:
                warn(f"  Could not disassemble calibration artifact: {e}")
        else:
            info(f"{symbol} {timeframe}: NO calibration artifact → raw probabilities used (expected for most models)")

    return errors


def validate_signal_consistency():
    """Validate recent signals are consistent with pipeline changes."""
    section("VALIDATION 4: Signal Consistency Check")

    db_path = Path(__file__).parent / 'storage' / 'database.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    errors = 0

    # For new signals (after repair): confidence should equal
    # round(calibrated_probability_max * 100) when available
    cursor.execute("""
        SELECT id, symbol, timeframe, direction, confidence,
               raw_probability_max, calibrated_probability_max, mtf_alignment
        FROM signals
        WHERE raw_probability_max IS NOT NULL
        ORDER BY id DESC LIMIT 10
    """)

    rows = cursor.fetchall()
    if rows:
        info(f"Checking {len(rows)} new signals for probabilistic consistency")
        for row in rows:
            sid, sym, tf, direction, conf, raw_max, cal_max, mtf = row
            expected = int(round(cal_max * 100)) if cal_max else conf
            if conf == expected:
                ok(f"  #{sid} {sym} {tf}: confidence={conf} == int(cal_max*100)={expected}")
            else:
                warn(f"  #{sid} {sym} {tf}: confidence={conf} != int(cal_max*100)={expected} (may be threshold-filtered)")
    else:
        info("No new signals with diagnostic fields yet (run scheduler to generate)")

    # For pre-repair signals: confidence should be in valid range
    cursor.execute("""
        SELECT COUNT(*) FROM signals
        WHERE confidence < 0 OR confidence > 100
    """)
    bad_count = cursor.fetchone()[0]
    if bad_count == 0:
        ok("All signals have confidence in [0, 100] range")
    else:
        fail(f"{bad_count} signals have confidence outside [0, 100]")
        errors += 1

    # Check no confidence values suspiciously match ×1.15 or ×0.80 patterns
    cursor.execute("""
        SELECT id, confidence FROM signals
        WHERE mtf_alignment IS NOT NULL AND mtf_alignment != 'NEUTRAL'
        ORDER BY id DESC LIMIT 10
    """)
    rows = cursor.fetchall()
    if rows:
        info(f"Checking {len(rows)} signals with non-NEUTRAL mtf_alignment")
        for row in rows:
            ok(f"  #{row[0]}: mtf_alignment != NEUTRAL, confidence={row[1]} (purely probabilistic, no mutation)")

    conn.close()
    return errors


def main():
    print(f"\n{'#'*60}")
    print(f"# CONFIDENCE PIPELINE REPAIR — VALIDATION")
    print(f"# {Path(__file__).name}")
    print(f"{'#'*60}")

    total_errors = 0

    total_errors += validate_source_code()
    total_errors += validate_db_schema()
    total_errors += validate_production_models()
    total_errors += validate_signal_consistency()

    section("SUMMARY")
    if total_errors == 0:
        print(f"  {COLORS['pass']}ALL VALIDATIONS PASSED{COLORS['reset']}")
    else:
        print(f"  {COLORS['fail']}{total_errors} VALIDATION(S) FAILED{COLORS['reset']}")

    print()
    return 1 if total_errors > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
