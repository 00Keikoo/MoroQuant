"""Validation tests for outcome engine repair.

Tests the three critical scenarios from the OUTCOME_LOGIC_AUDIT:
1. TP hit after 72h (was incorrectly marked TIMEOUT by old 48h cap)
2. SL hit after 60h (was incorrectly marked TIMEOUT by old 48h cap)
3. Timeout after 7d (should correctly be TIMEOUT, not premature)
4. Early WIN at 4h checkpoint (should finalize immediately)
5. Checkpoint timeout does NOT remove signal from pending queue
6. Signal stays pending after checkpoint timeouts until 7-day final evaluation
"""

import sys
import os
import sqlite3
import tempfile
import unittest.mock
from pathlib import Path
from datetime import datetime

# Add ml_service to path (parent of tests/)
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock CalibrationTracker if numpy is not available
try:
    import numpy as np
except ImportError:
    import types
    mock_cal = types.ModuleType('analytics.calibration')
    mock_cal.CalibrationTracker = type('CalibrationTracker', (), {
        '__init__': lambda self, *a, **kw: None,
        'update_calibration_stats': lambda self, *a, **kw: None,
    })
    sys.modules['analytics.calibration'] = mock_cal

from analytics.outcome_engine import (
    OutcomeEngine,
    SignalOutcome,
    FINAL_TIMEOUT_DAYS,
    CHECKPOINT_INTERVALS_HOURS,
)


def setup_test_db():
    """Create a temporary database with test schema and data."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create signals table
    cursor.execute("""
        CREATE TABLE signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            direction TEXT NOT NULL,
            confidence INTEGER NOT NULL,
            features_json TEXT,
            model_version TEXT,
            entry_price REAL,
            take_profit REAL,
            stop_loss REAL,
            tp_multiplier REAL,
            sl_multiplier REAL,
            labeling_method TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create OHLCV table
    cursor.execute("""
        CREATE TABLE ohlcv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, timeframe, timestamp)
        )
    """)

    # Create signal_outcomes table
    cursor.execute("""
        CREATE TABLE signal_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER NOT NULL UNIQUE,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            entry_price REAL NOT NULL,
            take_profit REAL NOT NULL,
            stop_loss REAL NOT NULL,
            outcome TEXT CHECK(outcome IN ('win', 'loss', 'timeout')),
            exit_price REAL,
            exit_time INTEGER,
            max_favorable_excursion REAL,
            max_adverse_excursion REAL,
            holding_hours REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create signal_checkpoints table
    cursor.execute("""
        CREATE TABLE signal_checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER NOT NULL,
            checkpoint_hours INTEGER NOT NULL,
            outcome_at_checkpoint TEXT NOT NULL,
            exit_price REAL,
            exit_time INTEGER,
            mfe REAL DEFAULT 0,
            mae REAL DEFAULT 0,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(signal_id, checkpoint_hours)
        )
    """)

    # Create calibration table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_calibration_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            confidence_bucket TEXT NOT NULL,
            signal_count INTEGER DEFAULT 0,
            win_count INTEGER DEFAULT 0,
            loss_count INTEGER DEFAULT 0,
            avg_confidence REAL,
            actual_win_rate REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, timeframe, confidence_bucket)
        )
    """)

    conn.commit()
    conn.close()
    return db_path


def insert_signal(conn, signal_id, symbol, timestamp, direction,
                  entry_price, take_profit, stop_loss, confidence=70):
    """Insert a test signal."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO signals
        (id, symbol, timeframe, timestamp, direction, confidence,
         entry_price, take_profit, stop_loss)
        VALUES (?, ?, '1h', ?, ?, ?, ?, ?, ?)
    """, (signal_id, symbol, timestamp, direction, confidence,
          entry_price, take_profit, stop_loss))
    conn.commit()


def insert_candle(conn, symbol, timestamp, open_p, high, low, close, volume=100):
    """Insert a test OHLCV candle."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO ohlcv
        (symbol, timeframe, timestamp, open, high, low, close, volume)
        VALUES (?, '1h', ?, ?, ?, ?, ?, ?)
    """, (symbol, timestamp, open_p, high, low, close, volume))
    conn.commit()


def hours_to_ms(hours):
    return hours * 60 * 60 * 1000


# ============================================================
# TEST 1: TP hit after 72h
# ============================================================
def test_tp_hit_after_72h():
    """
    SCENARIO: Entry at 100, TP at 110 (long). Price stays flat for 72h,
    then rallies to 110 at the 73rd hour candle.

    OLD BEHAVIOR: After 48h checkpoint, all checkpoints timed out.
    System returned TIMEOUT and saved to signal_outcomes. Signal permanently excluded.

    NEW BEHAVIOR: Checkpoints 1h-48h all timeout (monitoring events in signal_checkpoints).
    After 7 days, final scan finds TP hit at 73h. Returns WIN.
    """
    print("\n" + "="*60)
    print("TEST 1: TP hit after 72h (was incorrectly TIMEOUT)")
    print("="*60)

    db_path = setup_test_db()
    try:
        conn = sqlite3.connect(db_path)

        entry_time = 1000000000000  # Base timestamp
        entry_price = 100.0
        tp = 110.0
        sl = 95.0

        # Insert signal
        insert_signal(conn, 1, 'BTCUSDT', entry_time, 'long',
                      entry_price, tp, sl)
        conn.close()

        engine = OutcomeEngine(db_path)

        # Insert candles: flat for 72h, then rally
        conn = sqlite3.connect(db_path)
        for h in range(1, 73):
            t = entry_time + hours_to_ms(h)
            # Price stays flat around 100 (between SL 95 and TP 110)
            insert_candle(conn, 'BTCUSDT', t, 99.5, 101.0, 99.0, 100.5)

        # 73rd hour: price hits TP
        t73 = entry_time + hours_to_ms(73)
        insert_candle(conn, 'BTCUSDT', t73, 105.0, 112.0, 104.0, 110.0)
        conn.close()

        # Simulate current time = 8 days after entry (past final expiry)
        now_ms = entry_time + hours_to_ms(8 * 24)

        result = engine._evaluate_signal_phased(1, now_ms)

        assert result is not None, "Should return a result after 8 days"
        assert result.outcome == 'win', f"Expected 'win', got '{result.outcome}'"
        assert result.exit_price == tp, f"Expected exit_price={tp}, got {result.exit_price}"
        print(f"  PASS: outcome={result.outcome}, exit_price={result.exit_price}, "
              f"holding_hours={result.holding_hours:.1f}")

        # Verify checkpoints were recorded as monitoring events
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT checkpoint_hours, outcome_at_checkpoint FROM signal_checkpoints "
                       "WHERE signal_id = 1 ORDER BY checkpoint_hours")
        checkpoints = cursor.fetchall()
        conn.close()

        assert len(checkpoints) > 0, "Should have checkpoint records"
        for cp in checkpoints:
            assert cp[1] == 'timeout', \
                f"Checkpoint at {cp[0]}h should be 'timeout' (monitoring), got '{cp[1]}'"
        print(f"  PASS: {len(checkpoints)} checkpoints recorded as monitoring events")

    finally:
        os.unlink(db_path)

    print("  TEST 1 PASSED")


# ============================================================
# TEST 2: SL hit after 60h
# ============================================================
def test_sl_hit_after_60h():
    """
    SCENARIO: Entry at 100, SL at 90 (long). Price drops slowly,
    hits SL at the 60th hour candle.

    OLD BEHAVIOR: All checkpoints up to 48h saw price above SL.
    System returned TIMEOUT. Loss between 48-60h was missed.

    NEW BEHAVIOR: Checkpoints 1h-48h timeout (monitoring).
    Final 7-day scan finds SL hit at 60h. Returns LOSS.
    """
    print("\n" + "="*60)
    print("TEST 2: SL hit after 60h (was incorrectly TIMEOUT)")
    print("="*60)

    db_path = setup_test_db()
    try:
        conn = sqlite3.connect(db_path)

        entry_time = 1000000000000
        entry_price = 100.0
        tp = 115.0
        sl = 90.0

        insert_signal(conn, 2, 'BTCUSDT', entry_time, 'long',
                      entry_price, tp, sl)
        conn.close()

        engine = OutcomeEngine(db_path)

        # Insert candles: slow decline for 60h, hit SL
        conn = sqlite3.connect(db_path)
        for h in range(1, 60):
            t = entry_time + hours_to_ms(h)
            price = 100.0 - (h * 0.05)  # Very slow decline
            low = max(price - 0.5, 92.0)  # Stay above SL until hour 60
            insert_candle(conn, 'BTCUSDT', t, price + 0.3, price + 1.0, low, price)

        # 60th hour: SL hit
        t60 = entry_time + hours_to_ms(60)
        insert_candle(conn, 'BTCUSDT', t60, 91.0, 92.0, 88.0, 90.0)
        conn.close()

        now_ms = entry_time + hours_to_ms(8 * 24)

        result = engine._evaluate_signal_phased(2, now_ms)

        assert result is not None, "Should return a result after 8 days"
        assert result.outcome == 'loss', f"Expected 'loss', got '{result.outcome}'"
        assert result.exit_price == sl, f"Expected exit_price={sl}, got {result.exit_price}"
        print(f"  PASS: outcome={result.outcome}, exit_price={result.exit_price}, "
              f"holding_hours={result.holding_hours:.1f}")

    finally:
        os.unlink(db_path)

    print("  TEST 2 PASSED")


# ============================================================
# TEST 3: Timeout after 7d (no TP/SL hit)
# ============================================================
def test_timeout_after_7d():
    """
    SCENARIO: Entry at 100, TP at 110, SL at 90.
    Price oscillates in range for 7 days, never hitting TP or SL.

    OLD BEHAVIOR: Marked as TIMEOUT at 48h (premature).
    NEW BEHAVIOR: All checkpoints timeout (monitoring).
    After 7 days, final scan still finds no resolution. Returns TIMEOUT (final).
    """
    print("\n" + "="*60)
    print("TEST 3: Correct TIMEOUT after 7 days (not premature)")
    print("="*60)

    db_path = setup_test_db()
    try:
        conn = sqlite3.connect(db_path)

        entry_time = 1000000000000
        entry_price = 100.0
        tp = 110.0
        sl = 90.0

        insert_signal(conn, 3, 'BTCUSDT', entry_time, 'long',
                      entry_price, tp, sl)
        conn.close()

        engine = OutcomeEngine(db_path)

        # Insert candles: oscillate between 95 and 105 for 7 days
        conn = sqlite3.connect(db_path)
        for h in range(1, 7 * 24 + 1):
            t = entry_time + hours_to_ms(h)
            # Oscillate safely between SL and TP
            mid = 100.0 + (2.0 if h % 2 == 0 else -2.0)
            insert_candle(conn, 'BTCUSDT', t, mid - 1, mid + 3, mid - 3, mid)
        conn.close()

        # Exactly at 7 days
        now_ms = entry_time + hours_to_ms(7 * 24)

        result = engine._evaluate_signal_phased(3, now_ms)

        assert result is not None, "Should return a result at 7 days"
        assert result.outcome == 'timeout', \
            f"Expected 'timeout', got '{result.outcome}'"
        assert result.exit_price is None, \
            f"Expected no exit_price for timeout, got {result.exit_price}"
        print(f"  PASS: outcome={result.outcome} (correct final timeout after 7 days)")

    finally:
        os.unlink(db_path)

    print("  TEST 3 PASSED")


# ============================================================
# TEST 4: Early WIN at 4h checkpoint (should finalize immediately)
# ============================================================
def test_early_win_at_checkpoint():
    """
    SCENARIO: Entry at 100, TP at 105 (long). Price hits TP at 3rd hour.

    EXPECTED: Checkpoint 1h finds timeout. Checkpoint 4h finds WIN.
    WIN is a FINAL outcome -- signal exits pending immediately.
    No need to wait for 7-day expiry.
    """
    print("\n" + "="*60)
    print("TEST 4: Early WIN at checkpoint (should finalize immediately)")
    print("="*60)

    db_path = setup_test_db()
    try:
        conn = sqlite3.connect(db_path)

        entry_time = 1000000000000
        entry_price = 100.0
        tp = 105.0
        sl = 95.0

        insert_signal(conn, 4, 'BTCUSDT', entry_time, 'long',
                      entry_price, tp, sl)
        conn.close()

        engine = OutcomeEngine(db_path)

        conn = sqlite3.connect(db_path)
        # Hour 1: flat
        t1 = entry_time + hours_to_ms(1)
        insert_candle(conn, 'BTCUSDT', t1, 100.0, 101.0, 99.0, 100.5)

        # Hour 3: TP hit (will be found when 4h checkpoint scans)
        t3 = entry_time + hours_to_ms(3)
        insert_candle(conn, 'BTCUSDT', t3, 103.0, 107.0, 102.0, 105.0)
        conn.close()

        # Only 5 hours elapsed (not yet 7 days)
        now_ms = entry_time + hours_to_ms(5)

        result = engine._evaluate_signal_phased(4, now_ms)

        assert result is not None, "Should return result (early WIN)"
        assert result.outcome == 'win', \
            f"Expected 'win' (early resolution), got '{result.outcome}'"
        assert result.holding_hours is not None
        assert result.holding_hours < 4, \
            f"Expected holding < 4h, got {result.holding_hours}"
        print(f"  PASS: outcome={result.outcome}, holding_hours={result.holding_hours:.1f} (finalized early)")

        # In production, evaluate_pending_outcomes calls save_outcome()
        engine.save_outcome(result)

        # Verify signal is now in signal_outcomes (final)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT outcome FROM signal_outcomes WHERE signal_id = 4")
        row = cursor.fetchone()
        conn.close()

        assert row is not None, "WIN should be saved to signal_outcomes"
        assert row[0] == 'win', f"Expected 'win' in DB, got '{row[0]}'"
        print(f"  PASS: Final outcome saved to signal_outcomes")

        # Verify signal is no longer in pending queue
        pending = engine.get_pending_signals()
        assert 4 not in pending, "Signal 4 should NOT be in pending queue after WIN"
        print(f"  PASS: Signal removed from pending queue (pending={pending})")

    finally:
        os.unlink(db_path)

    print("  TEST 4 PASSED")


# ============================================================
# TEST 5: Checkpoint timeout does NOT create signal_outcomes row
# ============================================================
def test_checkpoint_timeout_no_outcome_row():
    """
    SCENARIO: Signal evaluated at checkpoints, all timeout.
    Not enough time elapsed for 7-day final evaluation.

    EXPECTED: No row in signal_outcomes. Signal remains in pending queue.
    """
    print("\n" + "="*60)
    print("TEST 5: Checkpoint timeouts do NOT create outcome rows")
    print("="*60)

    db_path = setup_test_db()
    try:
        conn = sqlite3.connect(db_path)

        entry_time = 1000000000000
        entry_price = 100.0
        tp = 110.0
        sl = 90.0

        insert_signal(conn, 5, 'BTCUSDT', entry_time, 'long',
                      entry_price, tp, sl)
        conn.close()

        engine = OutcomeEngine(db_path)

        # Insert flat candles for 50 hours
        conn = sqlite3.connect(db_path)
        for h in range(1, 51):
            t = entry_time + hours_to_ms(h)
            insert_candle(conn, 'BTCUSDT', t, 100.0, 101.0, 99.0, 100.5)
        conn.close()

        # Only 50 hours elapsed -- NOT enough for 7-day final
        now_ms = entry_time + hours_to_ms(50)

        result = engine._evaluate_signal_phased(5, now_ms)

        assert result is None, \
            f"Expected None (still pending), got outcome='{result.outcome if result else 'none'}'"
        print(f"  PASS: No final outcome returned (signal still pending)")

        # Verify NO row in signal_outcomes
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM signal_outcomes WHERE signal_id = 5")
        row = cursor.fetchone()
        conn.close()

        assert row is None, "Should NOT have signal_outcomes row after checkpoint timeouts"
        print(f"  PASS: No signal_outcomes row (correctly absent)")

        # Verify signal IS in pending queue
        pending = engine.get_pending_signals()
        assert 5 in pending, "Signal 5 should still be in pending queue"
        print(f"  PASS: Signal still in pending queue (pending={pending})")

        # Verify checkpoints WERE recorded
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM signal_checkpoints WHERE signal_id = 5")
        cp_count = cursor.fetchone()[0]
        conn.close()

        assert cp_count > 0, f"Should have checkpoint records, got {cp_count}"
        print(f"  PASS: {cp_count} checkpoint monitoring events recorded")

    finally:
        os.unlink(db_path)

    print("  TEST 5 PASSED")


# ============================================================
# TEST 6: Signal stays pending until final expiry
# ============================================================
def test_signal_stays_pending_until_7d():
    """
    SCENARIO: Flat price action. Checkpoints at 1h, 4h, 12h, 24h, 48h all timeout.
    At 6 days, signal should still be pending. At 7 days, should be TIMEOUT.
    """
    print("\n" + "="*60)
    print("TEST 6: Signal stays pending until 7-day final expiry")
    print("="*60)

    db_path = setup_test_db()
    try:
        conn = sqlite3.connect(db_path)

        entry_time = 1000000000000
        entry_price = 100.0
        tp = 110.0
        sl = 90.0

        insert_signal(conn, 6, 'BTCUSDT', entry_time, 'long',
                      entry_price, tp, sl)
        conn.close()

        engine = OutcomeEngine(db_path)

        # Insert flat candles for 7 days
        conn = sqlite3.connect(db_path)
        for h in range(1, 7 * 24 + 1):
            t = entry_time + hours_to_ms(h)
            insert_candle(conn, 'BTCUSDT', t, 100.0, 101.0, 99.0, 100.5)
        conn.close()

        # At 6 days: should still be pending
        now_ms_6d = entry_time + hours_to_ms(6 * 24)
        result_6d = engine._evaluate_signal_phased(6, now_ms_6d)

        assert result_6d is None, \
            f"At 6 days: expected None (pending), got '{result_6d.outcome if result_6d else 'none'}'"
        print(f"  PASS: At 6 days, signal still pending (no final outcome)")

        # At 7 days: should be TIMEOUT (final)
        now_ms_7d = entry_time + hours_to_ms(7 * 24)
        result_7d = engine._evaluate_signal_phased(6, now_ms_7d)

        assert result_7d is not None, "At 7 days: should return final result"
        assert result_7d.outcome == 'timeout', \
            f"At 7 days: expected 'timeout', got '{result_7d.outcome}'"
        print(f"  PASS: At 7 days, correctly marked as TIMEOUT (final)")

        # In production, evaluate_pending_outcomes calls save_outcome()
        engine.save_outcome(result_7d)

        # Verify it's saved
        pending = engine.get_pending_signals()
        assert 6 not in pending, "After 7d timeout, signal should NOT be in pending"
        print(f"  PASS: Signal removed from pending queue after final timeout")

    finally:
        os.unlink(db_path)

    print("  TEST 6 PASSED")


# ============================================================
# RUN ALL TESTS
# ============================================================
if __name__ == '__main__':
    print("\n" + "="*60)
    print("OUTCOME ENGINE REPAIR - VALIDATION TESTS")
    print("="*60)
    print(f"CHECKPOINT_INTERVALS: {CHECKPOINT_INTERVALS_HOURS}")
    print(f"FINAL_TIMEOUT_DAYS: {FINAL_TIMEOUT_DAYS}")

    passed = 0
    failed = 0

    try:
        test_tp_hit_after_72h()
        passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        failed += 1

    try:
        test_sl_hit_after_60h()
        passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        failed += 1

    try:
        test_timeout_after_7d()
        passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        failed += 1

    try:
        test_early_win_at_checkpoint()
        passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        failed += 1

    try:
        test_checkpoint_timeout_no_outcome_row()
        passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        failed += 1

    try:
        test_signal_stays_pending_until_7d()
        passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        failed += 1

    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print("="*60)

    if failed > 0:
        sys.exit(1)
    else:
        print("\nALL TESTS PASSED")
        sys.exit(0)
