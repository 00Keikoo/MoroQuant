"""Validation tests for model_confidence_stats auto-update and analytics.

Verifies that:
1. The table is created automatically on OutcomeEngine init.
2. save_outcome() correctly buckets signals by confidence and counts outcomes.
3. actual_win_rate is computed over decided outcomes (win + loss), excluding timeouts.
4. Multiple symbols/timeframes/buckets are tracked independently.
5. get_confidence_stats() filters correctly and orders buckets.
6. get_confidence_bucket_performance() derives calibration gap and shares.
7. Re-saving (correction) keeps stats consistent -- no double-count, stale buckets pruned.
8. Signals with NULL confidence are skipped (not miscategorized).
"""

import sys
import os
import sqlite3
import tempfile
import types
from pathlib import Path

# Add ml_service to path (parent of tests/)
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock CalibrationTracker if numpy is not available
try:
    import numpy as np
except ImportError:
    mock_cal = types.ModuleType('analytics.calibration')
    mock_cal.CalibrationTracker = type('CalibrationTracker', (), {
        '__init__': lambda self, *a, **kw: None,
        'update_calibration_stats': lambda self, *a, **kw: None,
    })
    sys.modules['analytics.calibration'] = mock_cal

from analytics.outcome_engine import OutcomeEngine, SignalOutcome
from analytics.confidence_analytics import (
    get_confidence_stats,
    get_confidence_bucket_performance,
)


def setup_test_db():
    """Create a temporary database with the minimal schema."""
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
            direction TEXT NOT NULL,
            confidence INTEGER NOT NULL,
            features_json TEXT,
            model_version TEXT,
            entry_price REAL,
            take_profit REAL,
            stop_loss REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

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


def make_outcome(signal_id, symbol, timeframe, outcome,
                 entry_price=None, take_profit=None, stop_loss=None,
                 exit_price=None, exit_time=None, holding_hours=None,
                 entry=None, tp=None, sl=None):
    """Helper to build a SignalOutcome."""
    if entry is not None:
        entry_price = entry
    if tp is not None:
        take_profit = tp
    if sl is not None:
        stop_loss = sl
    return SignalOutcome(
        signal_id=signal_id,
        symbol=symbol,
        timeframe=timeframe,
        entry_price=entry_price,
        take_profit=take_profit,
        stop_loss=stop_loss,
        outcome=outcome,
        exit_price=exit_price,
        exit_time=exit_time,
        max_favorable_excursion=0.0,
        max_adverse_excursion=0.0,
        holding_hours=holding_hours,
    )


def insert_signal(conn, signal_id, symbol, timeframe, confidence, direction='long'):
    """Insert a signal row."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO signals
        (id, symbol, timeframe, timestamp, direction, confidence)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (signal_id, symbol, timeframe, 1000000000000, direction, confidence))
    conn.commit()


def find_bucket(rows, symbol, timeframe, bucket):
    """Helper to find a specific bucket row in a list."""
    for r in rows:
        if r['symbol'] == symbol and r['timeframe'] == timeframe and r['confidence_bucket'] == bucket:
            return r
    return None


# ============================================================
# TEST 1: Table auto-created on init
# ============================================================
def test_table_auto_created():
    print("\n" + "="*60)
    print("TEST 1: model_confidence_stats auto-created on init")
    print("="*60)

    db_path = setup_test_db()
    try:
        OutcomeEngine(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='model_confidence_stats'
        """)
        row = cursor.fetchone()
        conn.close()

        assert row is not None, "model_confidence_stats table should exist"
        print("  PASS: Table created automatically")

        # Empty accessors
        assert get_confidence_stats(db_path=db_path) == []
        perf = get_confidence_bucket_performance(db_path=db_path)
        assert perf['buckets'] == []
        assert perf['totals']['signal_count'] == 0
        print("  PASS: Empty accessors return [] / zero totals")
    finally:
        os.unlink(db_path)

    print("  TEST 1 PASSED")


# ============================================================
# TEST 2: Signals bucketed and counted correctly
# ============================================================
def test_bucketing_and_counts():
    print("\n" + "="*60)
    print("TEST 2: Signals bucketed by confidence; outcomes counted")
    print("="*60)

    db_path = setup_test_db()
    try:
        engine = OutcomeEngine(db_path)
        conn = sqlite3.connect(db_path)

        # Bucket 80-100: 1 win, 1 loss (confidences 85, 90)
        insert_signal(conn, 1, 'BTCUSDT', '1h', 85)
        insert_signal(conn, 2, 'BTCUSDT', '1h', 90)
        # Bucket 60-79: 1 win, 1 timeout (confidences 65, 70)
        insert_signal(conn, 3, 'BTCUSDT', '1h', 65)
        insert_signal(conn, 4, 'BTCUSDT', '1h', 70)

        engine.save_outcome(make_outcome(1, 'BTCUSDT', '1h', 'win',
                                          entry=100, tp=110, sl=95))
        engine.save_outcome(make_outcome(2, 'BTCUSDT', '1h', 'loss',
                                          entry=100, tp=110, sl=95))
        engine.save_outcome(make_outcome(3, 'BTCUSDT', '1h', 'win',
                                          entry=100, tp=110, sl=95))
        engine.save_outcome(make_outcome(4, 'BTCUSDT', '1h', 'timeout',
                                          entry=100, tp=110, sl=90))

        conn.close()

        stats = get_confidence_stats(symbol='BTCUSDT', timeframe='1h', db_path=db_path)
        assert len(stats) == 2, f"Expected 2 buckets, got {len(stats)}"

        b80 = find_bucket(stats, 'BTCUSDT', '1h', '80-100')
        b60 = find_bucket(stats, 'BTCUSDT', '1h', '60-79')

        assert b80 is not None, "Bucket 80-100 missing"
        assert b80['signal_count'] == 2
        assert b80['wins'] == 1 and b80['losses'] == 1 and b80['timeouts'] == 0
        print(f"  PASS: 80-100 bucket -> {b80['wins']}W {b80['losses']}L {b80['timeouts']}T")

        assert b60 is not None, "Bucket 60-79 missing"
        assert b60['signal_count'] == 2
        assert b60['wins'] == 1 and b60['losses'] == 0 and b60['timeouts'] == 1
        print(f"  PASS: 60-79 bucket -> {b60['wins']}W {b60['losses']}L {b60['timeouts']}T")
    finally:
        os.unlink(db_path)

    print("  TEST 2 PASSED")


# ============================================================
# TEST 3: actual_win_rate excludes timeouts from denominator
# ============================================================
def test_actual_win_rate_excludes_timeouts():
    print("\n" + "="*60)
    print("TEST 3: actual_win_rate excludes timeouts from denominator")
    print("="*60)

    db_path = setup_test_db()
    try:
        engine = OutcomeEngine(db_path)
        conn = sqlite3.connect(db_path)

        # Bucket 80-100: 1 win, 1 loss, 8 timeouts
        # decided = 2, win_rate = 0.5
        for sid in range(1, 11):
            insert_signal(conn, sid, 'BTCUSDT', '1h', 85)

        engine.save_outcome(make_outcome(1, 'BTCUSDT', '1h', 'win',
                                          entry=100, tp=110, sl=95))
        engine.save_outcome(make_outcome(2, 'BTCUSDT', '1h', 'loss',
                                          entry=100, tp=110, sl=95))
        for sid in range(3, 11):
            engine.save_outcome(make_outcome(sid, 'BTCUSDT', '1h', 'timeout',
                                              entry=100, tp=110, sl=90))
        conn.close()

        stats = get_confidence_stats(symbol='BTCUSDT', timeframe='1h', db_path=db_path)
        b80 = find_bucket(stats, 'BTCUSDT', '1h', '80-100')

        assert b80['signal_count'] == 10
        assert b80['wins'] == 1 and b80['losses'] == 1 and b80['timeouts'] == 8
        # win_rate = 1/2 = 0.5 (NOT 1/10 = 0.1)
        assert b80['actual_win_rate'] == 0.5, \
            f"Expected actual_win_rate 0.5, got {b80['actual_win_rate']}"
        print(f"  PASS: actual_win_rate = {b80['actual_win_rate']} (1/2 decided, not 1/10 total)")
    finally:
        os.unlink(db_path)

    print("  TEST 3 PASSED")


# ============================================================
# TEST 4: Multiple symbols/timeframes tracked independently
# ============================================================
def test_independence_across_pairs():
    print("\n" + "="*60)
    print("TEST 4: Multiple symbols/timeframes tracked independently")
    print("="*60)

    db_path = setup_test_db()
    try:
        engine = OutcomeEngine(db_path)
        conn = sqlite3.connect(db_path)

        insert_signal(conn, 1, 'BTCUSDT', '1h', 85)
        insert_signal(conn, 2, 'ETHUSDT', '1h', 85)
        insert_signal(conn, 3, 'BTCUSDT', '4h', 85)

        engine.save_outcome(make_outcome(1, 'BTCUSDT', '1h', 'win',
                                          entry=100, tp=110, sl=95))
        engine.save_outcome(make_outcome(2, 'ETHUSDT', '1h', 'loss',
                                          entry=50, tp=55, sl=48))
        engine.save_outcome(make_outcome(3, 'BTCUSDT', '4h', 'timeout',
                                          entry=100, tp=110, sl=90))
        conn.close()

        btc_1h = get_confidence_stats(symbol='BTCUSDT', timeframe='1h', db_path=db_path)
        eth_1h = get_confidence_stats(symbol='ETHUSDT', timeframe='1h', db_path=db_path)
        btc_4h = get_confidence_stats(symbol='BTCUSDT', timeframe='4h', db_path=db_path)

        assert len(btc_1h) == 1 and btc_1h[0]['wins'] == 1
        assert len(eth_1h) == 1 and eth_1h[0]['losses'] == 1
        assert len(btc_4h) == 1 and btc_4h[0]['timeouts'] == 1
        print("  PASS: Each (symbol, timeframe) tracked independently")

        # Filter by symbol only returns all its timeframes
        btc_all = get_confidence_stats(symbol='BTCUSDT', db_path=db_path)
        assert len(btc_all) == 2, f"Expected 2 BTC rows, got {len(btc_all)}"
        print(f"  PASS: Symbol-only filter returns {len(btc_all)} timeframes")

        # No filter returns everything
        all_stats = get_confidence_stats(db_path=db_path)
        assert len(all_stats) == 3
        print(f"  PASS: Unfiltered returns all {len(all_stats)} rows")
    finally:
        os.unlink(db_path)

    print("  TEST 4 PASSED")


# ============================================================
# TEST 5: get_confidence_bucket_performance derives calibration gap
# ============================================================
def test_bucket_performance_derived_view():
    print("\n" + "="*60)
    print("TEST 5: get_confidence_bucket_performance calibration gap")
    print("="*60)

    db_path = setup_test_db()
    try:
        engine = OutcomeEngine(db_path)
        conn = sqlite3.connect(db_path)

        # Bucket 80-100 (midpoint 90): 8 wins, 2 losses -> actual 80%
        # calibration_gap = 90 - 80 = +10 (overconfident)
        for sid in range(1, 11):
            insert_signal(conn, sid, 'BTCUSDT', '1h', 85)

        for sid in range(1, 9):
            engine.save_outcome(make_outcome(sid, 'BTCUSDT', '1h', 'win',
                                              entry=100, tp=110, sl=95))
        for sid in range(9, 11):
            engine.save_outcome(make_outcome(sid, 'BTCUSDT', '1h', 'loss',
                                              entry=100, tp=110, sl=95))
        conn.close()

        view = get_confidence_bucket_performance(symbol='BTCUSDT', timeframe='1h', db_path=db_path)

        assert len(view['buckets']) == 1
        b = view['buckets'][0]
        assert b['confidence_bucket'] == '80-100'
        assert b['confidence_midpoint'] == 90.0
        assert b['actual_win_rate_pct'] == 80.0
        assert b['calibration_gap'] == 10.0, \
            f"Expected gap +10.0 (overconfident), got {b['calibration_gap']}"
        assert b['share_of_signals'] == 1.0
        print(f"  PASS: bucket midpoint={b['confidence_midpoint']} "
              f"actual={b['actual_win_rate_pct']}% gap={b['calibration_gap']}")

        # Totals
        assert view['totals']['signal_count'] == 10
        assert view['totals']['wins'] == 8
        assert view['totals']['losses'] == 2
        assert view['totals']['actual_win_rate'] == 0.8
        print(f"  PASS: totals wins={view['totals']['wins']} losses={view['totals']['losses']} "
              f"win_rate={view['totals']['actual_win_rate']}")
    finally:
        os.unlink(db_path)

    print("  TEST 5 PASSED")


# ============================================================
# TEST 6: Correction keeps stats consistent, prunes stale buckets
# ============================================================
def test_correction_consistency():
    print("\n" + "="*60)
    print("TEST 6: Correction doesn't double-count; stale buckets pruned")
    print("="*60)

    db_path = setup_test_db()
    try:
        engine = OutcomeEngine(db_path)
        conn = sqlite3.connect(db_path)

        # Only signal in 80-100 bucket
        insert_signal(conn, 1, 'BTCUSDT', '1h', 85)

        engine.save_outcome(make_outcome(1, 'BTCUSDT', '1h', 'timeout',
                                          entry=100, tp=110, sl=90))
        # Now correct to win
        engine.save_outcome(make_outcome(1, 'BTCUSDT', '1h', 'win',
                                          entry=100, tp=110, sl=95,
                                          exit_price=110))
        conn.close()

        stats = get_confidence_stats(symbol='BTCUSDT', timeframe='1h', db_path=db_path)
        assert len(stats) == 1, f"Expected 1 bucket, got {len(stats)}"
        b = stats[0]
        assert b['signal_count'] == 1, f"Expected count 1, got {b['signal_count']}"
        assert b['wins'] == 1 and b['timeouts'] == 0
        print(f"  PASS: After correction -> count={b['signal_count']} "
              f"wins={b['wins']} timeouts={b['timeouts']}")

        # Stale-bucket pruning: if a bucket loses all its signals after correction,
        # the bucket row should disappear.
        # Add a second signal in bucket 0-39, then correct it to remove (simulate
        # by re-saving the only signal in a different bucket is not possible; instead
        # verify pruning by deleting the last signal's outcome directly and re-refreshing).
        insert_signal(conn, 2, 'BTCUSDT', '1h', 30)  # bucket 0-39
        engine.save_outcome(make_outcome(2, 'BTCUSDT', '1h', 'loss',
                                          entry=100, tp=110, sl=95, exit_price=95))
        stats = get_confidence_stats(symbol='BTCUSDT', timeframe='1h', db_path=db_path)
        assert len(stats) == 2, f"Expected 2 buckets now, got {len(stats)}"

        # Now simulate removing signal 2 by deleting its outcome and refreshing
        conn2 = sqlite3.connect(db_path)
        conn2.execute("DELETE FROM signal_outcomes WHERE signal_id = 2")
        conn2.commit()
        conn2.close()
        engine._refresh_confidence_stats(2, 'BTCUSDT', '1h')

        stats = get_confidence_stats(symbol='BTCUSDT', timeframe='1h', db_path=db_path)
        assert len(stats) == 1, f"Expected 1 bucket after prune, got {len(stats)}"
        assert stats[0]['confidence_bucket'] == '80-100'
        print("  PASS: Stale bucket (0-39) pruned after its signals removed")
    finally:
        os.unlink(db_path)

    print("  TEST 6 PASSED")


# ============================================================
# TEST 7: NULL-confidence signals are skipped
# ============================================================
def test_null_confidence_skipped():
    print("\n" + "="*60)
    print("TEST 7: NULL-confidence signals are skipped")
    print("="*60)

    db_path = setup_test_db()
    try:
        engine = OutcomeEngine(db_path)
        conn = sqlite3.connect(db_path)

        # Insert signal with NULL confidence via raw SQL (the schema NOT NULL
        # constraint applies to the helper path, so we bypass it here)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO signals (id, symbol, timeframe, timestamp, direction, confidence)
            VALUES (1, 'BTCUSDT', '1h', 1000000000000, 'long', NULL)
        """)
        conn.commit()

        engine.save_outcome(make_outcome(1, 'BTCUSDT', '1h', 'win',
                                          entry=100, tp=110, sl=95))
        conn.close()

        stats = get_confidence_stats(symbol='BTCUSDT', timeframe='1h', db_path=db_path)
        assert len(stats) == 0, \
            f"NULL-confidence signal should be skipped, got {len(stats)} rows"
        print("  PASS: NULL-confidence signal produces no bucket rows")
    finally:
        os.unlink(db_path)

    print("  TEST 7 PASSED")


# ============================================================
# RUN ALL TESTS
# ============================================================
if __name__ == '__main__':
    print("\n" + "="*60)
    print("CONFIDENCE ANALYTICS FOUNDATION - VALIDATION TESTS")
    print("="*60)

    passed = 0
    failed = 0

    for test in [
        test_table_auto_created,
        test_bucketing_and_counts,
        test_actual_win_rate_excludes_timeouts,
        test_independence_across_pairs,
        test_bucket_performance_derived_view,
        test_correction_consistency,
        test_null_confidence_skipped,
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
