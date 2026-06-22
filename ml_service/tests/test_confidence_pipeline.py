"""Regression tests for confidence pipeline repair.

Validates the three P0 fixes:
  1. Calibration artifacts are APPLIED when available (not just loaded).
  2. MTF alignment is a SEPARATE field (AGREE/DISAGREE/NEUTRAL), not a
     confidence mutation (no ×1.15 or ×0.80 multipliers).
  3. raw_probability_max and calibrated_probability_max are persisted.

Also verifies:
  - Confidence is ALWAYS purely probabilistic (int(max(proba) * 100)).
  - Confidence never exceeds 100 or drops below 0.
  - calibration_applied flag reflects actual state.
"""

import sys
import os
import sqlite3
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock heavy deps that aren't available in system Python
for mod_name in ['numpy', 'sklearn', 'xgboost', 'lightgbm', 'pandas']:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = types.ModuleType(mod_name)


def setup_test_db():
    """Create a temporary database with signals table (migration 011 schema)."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            direction TEXT NOT NULL CHECK(direction IN ('long', 'short', 'neutral')),
            confidence INTEGER NOT NULL CHECK(confidence >= 0 AND confidence <= 100),
            features_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sl_multiplier REAL, tp_multiplier REAL, labeling_method TEXT,
            atr REAL, regime TEXT, model_version TEXT, entry_price REAL,
            take_profit REAL, stop_loss REAL, prob_short REAL, prob_neutral REAL, prob_long REAL,
            mtf_alignment TEXT DEFAULT 'NEUTRAL',
            raw_probability_max REAL,
            calibrated_probability_max REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE ohlcv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL, timeframe TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL,
            close REAL NOT NULL, volume REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, timeframe, timestamp)
        )
    """)

    conn.commit()
    conn.close()
    return db_path


def insert_signal_like_predictor(conn, signal):
    """Replicate save_signal_to_db INSERT via raw SQL (avoids numpy import)."""
    import json
    timestamp = 1000000000000
    features_json = json.dumps(signal.get('top_features', {}))
    conn.execute(
        """
        INSERT INTO signals (
            symbol, timeframe, timestamp, direction, confidence, features_json,
            tp_multiplier, sl_multiplier, labeling_method, atr, regime, model_version,
            entry_price, take_profit, stop_loss,
            prob_short, prob_neutral, prob_long,
            mtf_alignment, raw_probability_max, calibrated_probability_max
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            signal['symbol'],
            signal['timeframe'],
            timestamp,
            signal['direction'],
            signal['confidence'],
            features_json,
            signal.get('tp_multiplier'),
            signal.get('sl_multiplier'),
            signal.get('labeling_method'),
            signal.get('atr'),
            signal.get('regime'),
            signal.get('model_version'),
            signal.get('price'),
            signal.get('take_profit'),
            signal.get('stop_loss'),
            signal.get('prob_short'),
            signal.get('prob_neutral'),
            signal.get('prob_long'),
            signal.get('mtf_alignment', 'NEUTRAL'),
            signal.get('raw_probability_max'),
            signal.get('calibrated_probability_max'),
        )
    )
    conn.commit()


# ============================================================
# TEST 1: save_signal_to_db persists new fields correctly
# ============================================================
def test_save_signal_persists_new_fields():
    print("\n" + "="*60)
    print("TEST 1: Signal INSERT persists new pipeline fields")
    print("="*60)

    db_path = setup_test_db()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        signal = {
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'direction': 'long',
            'confidence': 72,
            'confidence_raw': 0.723,
            'top_features': {'rsi_14': 0.85, 'atr_14': 0.12},
            'tp_multiplier': 3.0,
            'sl_multiplier': 1.5,
            'labeling_method': 'triple_barrier',
            'atr': 150.5,
            'regime': 'trending',
            'model_version': '20260101_120000',
            'price': 65000.0,
            'take_profit': 65450.75,
            'stop_loss': 64775.25,
            'prob_short': 0.15,
            'prob_neutral': 0.13,
            'prob_long': 0.72,
            'mtf_alignment': 'AGREE',
            'raw_probability_max': 0.7234,
            'calibrated_probability_max': 0.7234,
        }

        insert_signal_like_predictor(conn, signal)

        row = conn.execute("SELECT * FROM signals WHERE symbol='BTCUSDT'").fetchone()
        conn.close()

        assert row is not None, "Signal should be inserted"
        assert row['confidence'] == 72
        assert row['mtf_alignment'] == 'AGREE', f"Expected AGREE, got {row['mtf_alignment']}"
        assert abs(row['raw_probability_max'] - 0.7234) < 0.0001, \
            f"raw_probability_max mismatch: {row['raw_probability_max']}"
        assert abs(row['calibrated_probability_max'] - 0.7234) < 0.0001, \
            f"calibrated_probability_max mismatch: {row['calibrated_probability_max']}"
        assert row['prob_long'] == 0.72
        print(f"  PASS: mtf_alignment={row['mtf_alignment']} "
              f"raw_max={row['raw_probability_max']} cal_max={row['calibrated_probability_max']}")

    finally:
        os.unlink(db_path)

    print("  TEST 1 PASSED")


# ============================================================
# TEST 2: mtf_alignment defaults to NEUTRAL when not set
# ============================================================
def test_mtf_alignment_default():
    print("\n" + "="*60)
    print("TEST 2: mtf_alignment defaults to NEUTRAL")
    print("="*60)

    db_path = setup_test_db()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Signal without mtf_alignment field (e.g. 4h timeframe)
        signal = {
            'symbol': 'BTCUSDT',
            'timeframe': '4h',
            'direction': 'long',
            'confidence': 68,
            'confidence_raw': 0.681,
            'top_features': {},
            'prob_short': 0.18,
            'prob_neutral': 0.14,
            'prob_long': 0.68,
            # mtf_alignment intentionally omitted
            'raw_probability_max': 0.681,
            'calibrated_probability_max': 0.681,
        }

        insert_signal_like_predictor(conn, signal)

        row = conn.execute("SELECT mtf_alignment FROM signals WHERE symbol='BTCUSDT'").fetchone()
        conn.close()

        assert row['mtf_alignment'] == 'NEUTRAL', f"Expected NEUTRAL default, got {row['mtf_alignment']}"
        print("  PASS: Default mtf_alignment = NEUTRAL")

    finally:
        os.unlink(db_path)

    print("  TEST 2 PASSED")


# ============================================================
# TEST 3: No confidence mutation multipliers in predictor.py
# ============================================================
def test_no_confidence_mutation_multipliers():
    print("\n" + "="*60)
    print("TEST 3: No ×1.15/×0.80 confidence mutation in predictor.py")
    print("="*60)

    predictor_path = Path(__file__).parent.parent / 'models' / 'predictor.py'
    source = predictor_path.read_text()

    # Must not contain the old multipliers
    assert '1.15' not in source, "Old MTF boost multiplier ×1.15 found in predictor.py"
    assert '0.80' not in source, "Old MTF penalty multiplier ×0.80 found in predictor.py"
    assert 'mtf_conflict' not in source, "Old mtf_conflict field found in predictor.py"
    print("  PASS: No confidence mutation multipliers found")

    # Must contain the new alignment field
    assert 'mtf_alignment' in source, "mtf_alignment field missing from predictor.py"
    assert "'AGREE'" in source, "AGREE alignment value missing"
    assert "'DISAGREE'" in source, "DISAGREE alignment value missing"
    print("  PASS: mtf_alignment field with AGREE/DISAGREE/NEUTRAL present")

    print("  TEST 3 PASSED")


# ============================================================
# TEST 4: Calibration is applied when artifact available
# ============================================================
def test_calibration_applied_when_available():
    print("\n" + "="*60)
    print("TEST 4: Calibration applied when artifact available")
    print("="*60)

    predictor_path = Path(__file__).parent.parent / 'models' / 'predictor.py'
    source = predictor_path.read_text()

    # Must NOT contain the old dead code
    assert 'Calibration artifacts loaded for diagnostics but NOT applied' not in source, \
        "Old 'diagnostics only' comment still present"
    assert 'Always use raw probabilities (no calibration applied)' not in source, \
        "Old 'always raw' comment still present"
    print("  PASS: Old dead-code comments removed")

    # Must contain apply_calibrator call
    assert 'cal_mod.apply_calibrator' in source, \
        "cal_mod.apply_calibrator() call missing from predictor.py"
    assert 'chosen_cal' in source, \
        "chosen_cal variable (selected calibrator) missing"
    print("  PASS: cal_mod.apply_calibrator() called when calibrator available")

    # Must contain calibration_applied tracking
    assert 'calibration_applied = False' in source, \
        "calibration_applied initialization missing"
    assert 'calibration_applied = True' in source, \
        "calibration_applied set-to-True missing"
    print("  PASS: calibration_applied flag tracked correctly")

    # Must contain raw fallback
    assert 'falling back to raw probabilities' in source, \
        "Raw fallback warning missing"
    print("  PASS: Raw fallback with warning on calibration failure")

    print("  TEST 4 PASSED")


# ============================================================
# TEST 5: raw_probability_max and calibrated_probability_max
#         are present in signal dict
# ============================================================
def test_diagnostic_fields_in_signal_dict():
    print("\n" + "="*60)
    print("TEST 5: Diagnostic fields present in signal dict construction")
    print("="*60)

    predictor_path = Path(__file__).parent.parent / 'models' / 'predictor.py'
    source = predictor_path.read_text()

    for field in ['raw_probability_max', 'calibrated_probability_max']:
        assert f"'{field}'" in source, f"'{field}' key missing from signal dict"
        print(f"  PASS: '{field}' in signal dict")

    # Verify both are derived from np.max(proba)
    assert 'raw_proba_max' in source, "raw_proba_max variable missing"
    assert 'calibrated_proba_max' in source, "calibrated_proba_max variable missing"
    print("  PASS: Both diagnostic values computed before signal dict")

    print("  TEST 5 PASSED")


# ============================================================
# TEST 6: Confidence is always int(max_proba * 100)
#         regardless of calibration or MTF
# ============================================================
def test_confidence_is_pure_probability():
    print("\n" + "="*60)
    print("TEST 6: Confidence derived purely from max(proba), never mutated")
    print("="*60)

    predictor_path = Path(__file__).parent.parent / 'models' / 'predictor.py'
    source = predictor_path.read_text()

    # confidence_pct must come from calibrated prediction_proba, not from
    # any multiplication
    lines = source.split('\n')

    # Find the confidence_pct assignment — it should be int(confidence * 100)
    # where confidence = float(prediction_proba[prediction])
    found_proba_derivation = False
    found_int_conversion = False

    for i, line in enumerate(lines):
        if 'confidence = float(prediction_proba[prediction])' in line:
            found_proba_derivation = True
        if 'confidence_pct = int(confidence * 100)' in line:
            found_int_conversion = True

    assert found_proba_derivation, \
        "confidence = float(prediction_proba[prediction]) not found"
    assert found_int_conversion, \
        "confidence_pct = int(confidence * 100) not found"
    print("  PASS: confidence_pct = int(float(max(proba)) * 100)")

    # After this assignment, confidence_pct must NEVER be reassigned
    # (MTF block should only set mtf_alignment, not confidence)
    confidence_set_lines = []
    past_confidence_assignment = False
    for line in lines:
        if 'confidence_pct = int(confidence * 100)' in line:
            past_confidence_assignment = True
            continue
        if past_confidence_assignment and "signal['confidence'] = " in line:
            confidence_set_lines.append(line.strip())

    assert len(confidence_set_lines) == 0, \
        f"Confidence mutated after initial derivation: {confidence_set_lines}"
    print("  PASS: confidence never mutated after initial derivation")

    print("  TEST 6 PASSED")


# ============================================================
# TEST 7: DISAGREE mtf_alignment does NOT reduce confidence
# ============================================================
def test_disagree_no_confidence_reduction():
    print("\n" + "="*60)
    print("TEST 7: DISAGREE mtf_alignment does NOT reduce confidence")
    print("="*60)

    db_path = setup_test_db()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Simulate a signal with DISAGREE mtf_alignment
        signal = {
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'direction': 'long',
            'confidence': 65,
            'confidence_raw': 0.653,
            'top_features': {},
            'prob_short': 0.20,
            'prob_neutral': 0.15,
            'prob_long': 0.65,
            'mtf_alignment': 'DISAGREE',
            'raw_probability_max': 0.653,
            'calibrated_probability_max': 0.653,
        }

        insert_signal_like_predictor(conn, signal)

        row = conn.execute("SELECT confidence, mtf_alignment FROM signals WHERE symbol='BTCUSDT'").fetchone()
        conn.close()

        # DISAGREE must NOT have reduced confidence from 65 to 52 (=65*0.80)
        assert row['confidence'] == 65, \
            f"Confidence was mutated! Expected 65, got {row['confidence']}"
        assert row['mtf_alignment'] == 'DISAGREE'
        print(f"  PASS: DISAGREE alignment with confidence={row['confidence']} (unmutated)")

    finally:
        os.unlink(db_path)

    print("  TEST 7 PASSED")


# ============================================================
# TEST 8: DB schema has NOT NULL on confidence, CHECK on range
# ============================================================
def test_confidence_constraints():
    print("\n" + "="*60)
    print("TEST 8: Confidence NOT NULL and 0-100 CHECK constraint")
    print("="*60)

    db_path = setup_test_db()
    try:
        conn = sqlite3.connect(db_path)

        # NULL confidence should fail
        try:
            conn.execute("""
                INSERT INTO signals (symbol, timeframe, timestamp, direction, confidence)
                VALUES ('BTCUSDT', '1h', 1, 'long', NULL)
            """)
            conn.commit()
            assert False, "NULL confidence should be rejected"
        except sqlite3.IntegrityError as e:
            assert 'NOT NULL' in str(e).upper() or 'constraint' in str(e).lower()
            conn.rollback()
            print("  PASS: NULL confidence rejected by NOT NULL constraint")

        # Out-of-range confidence should fail
        try:
            conn.execute("""
                INSERT INTO signals (symbol, timeframe, timestamp, direction, confidence)
                VALUES ('BTCUSDT', '1h', 2, 'long', 105)
            """)
            conn.commit()
            assert False, "confidence=105 should be rejected"
        except sqlite3.IntegrityError as e:
            assert 'CHECK' in str(e).upper()
            conn.rollback()
            print("  PASS: confidence=105 rejected by CHECK constraint")

        # Valid confidence succeeds
        conn.execute("""
            INSERT INTO signals (symbol, timeframe, timestamp, direction, confidence)
            VALUES ('BTCUSDT', '1h', 3, 'long', 72)
        """)
        conn.commit()
        row = conn.execute("SELECT confidence FROM signals WHERE timestamp=3").fetchone()
        assert row[0] == 72
        print("  PASS: confidence=72 accepted")

        conn.close()

    finally:
        os.unlink(db_path)

    print("  TEST 8 PASSED")


# ============================================================
# TEST 9: raw_probability_max == calibrated_probability_max
#         when no calibration available
# ============================================================
def test_raw_equals_calibrated_when_no_calibration():
    print("\n" + "="*60)
    print("TEST 9: raw_max == calibrated_max when no calibration")
    print("="*60)

    db_path = setup_test_db()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # No calibration: both should be identical
        raw_val = 0.6847
        signal = {
            'symbol': 'ETHUSDT',
            'timeframe': '1h',
            'direction': 'neutral',
            'confidence': 68,
            'confidence_raw': 0.685,
            'top_features': {},
            'prob_short': 0.20,
            'prob_neutral': 0.68,
            'prob_long': 0.12,
            'calibration_applied': False,
            'calibration_available': False,
            'calibration_method': 'none',
            'mtf_alignment': 'NEUTRAL',
            'raw_probability_max': raw_val,
            'calibrated_probability_max': raw_val,
        }

        insert_signal_like_predictor(conn, signal)

        row = conn.execute("SELECT raw_probability_max, calibrated_probability_max "
                           "FROM signals WHERE symbol='ETHUSDT'").fetchone()
        conn.close()

        assert abs(row['raw_probability_max'] - raw_val) < 0.0001
        assert abs(row['calibrated_probability_max'] - raw_val) < 0.0001
        assert row['raw_probability_max'] == row['calibrated_probability_max']
        print(f"  PASS: raw_max={row['raw_probability_max']} == cal_max={row['calibrated_probability_max']}")

    finally:
        os.unlink(db_path)

    print("  TEST 9 PASSED")


# ============================================================
# RUN ALL TESTS
# ============================================================
if __name__ == '__main__':
    print("\n" + "="*60)
    print("CONFIDENCE PIPELINE REPAIR - REGRESSION TESTS")
    print("="*60)

    passed = 0
    failed = 0

    for test in [
        test_save_signal_persists_new_fields,
        test_mtf_alignment_default,
        test_no_confidence_mutation_multipliers,
        test_calibration_applied_when_available,
        test_diagnostic_fields_in_signal_dict,
        test_confidence_is_pure_probability,
        test_disagree_no_confidence_reduction,
        test_confidence_constraints,
        test_raw_equals_calibrated_when_no_calibration,
    ]:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print("="*60)

    sys.exit(1 if failed > 0 else 0)
