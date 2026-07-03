"""Validation tests for the model_performance_summary auto-update.

Verifies that:
1. The summary table is created automatically on OutcomeEngine init.
2. save_outcome() correctly increments win/loss/timeout counters.
3. win_rate is computed over decided outcomes (win + loss), excluding timeouts.
4. profit_factor_proxy is computed from signal price distances.
5. avg_holding_hours is the mean over resolved (win/loss) signals.
6. Multiple symbols/timeframes are tracked independently.
7. The three utility functions return correct shapes and values.
8. Re-saving an outcome for an existing signal (correction) doesn't double-count.
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

from ml_service.analytics.outcome_engine import OutcomeEngine, SignalOutcome
from ml_service.analytics.performance_summary import (
    get_model_performance,
    get_symbol_performance,
    get_global_performance,
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

    # signal_outcomes without the legacy checkpoint columns (clean schema)
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
    """Helper to build a SignalOutcome.

    Accepts short aliases: entry, tp, sl.
    """
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


def insert_signal(conn, signal_id, symbol, timeframe, confidence=70):
    """Insert a signal row (needed for calibration join)."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO signals
        (id, symbol, timeframe, timestamp, direction, confidence)
        VALUES (?, ?, ?, ?, 'long', ?)
    """, (signal_id, symbol, timeframe, 1000000000000, confidence))
    conn.commit()


# ============================================================
# TEST 1: Table auto-created on init
# ============================================================
def test_table_auto_created():
    print("\n" + "="*60)
    print("TEST 1: model_performance_summary auto-created on init")
    print("="*60)

    db_path = setup_test_db()
    try:
        OutcomeEngine(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='model_performance_summary'
        """)
        row = cursor.fetchone()
        conn.close()

        assert row is not None, "model_performance_summary table should exist"
        print("  PASS: Table created automatically")

        # Utility should return None for empty pair
        result = get_model_performance('BTCUSDT', '1h', db_path=db_path)
        assert result is None, f"Expected None for empty pair, got {result}"
        print("  PASS: get_model_performance returns None when no data")
    finally:
        os.unlink(db_path)

    print("  TEST 1 PASSED")


# ============================================================
# TEST 2: Counters increment correctly on save_outcome
# ============================================================
def test_counters_increment():
    print("\n" + "="*60)
    print("TEST 2: Counters increment on save_outcome (win/loss/timeout)")
    print("="*60)

    db_path = setup_test_db()
    try:
        engine = OutcomeEngine(db_path)
        conn = sqlite3.connect(db_path)

        # Seed signals
        for sid in [1, 2, 3, 4, 5]:
            insert_signal(conn, sid, 'BTCUSDT', '1h')

        # 2 wins, 1 loss, 1 timeout (decided = 3)
        engine.save_outcome(make_outcome(1, 'BTCUSDT', '1h', 'win',
                                          entry=100, tp=105, sl=95,
                                          exit_price=105, holding_hours=10.0))
        engine.save_outcome(make_outcome(2, 'BTCUSDT', '1h', 'win',
                                          entry=100, tp=108, sl=95,
                                          exit_price=108, holding_hours=20.0))
        engine.save_outcome(make_outcome(3, 'BTCUSDT', '1h', 'loss',
                                          entry=100, tp=110, sl=92,
                                          exit_price=92, holding_hours=15.0))
        engine.save_outcome(make_outcome(4, 'BTCUSDT', '1h', 'timeout',
                                          entry=100, tp=110, sl=90))

        conn.close()

        perf = get_model_performance('BTCUSDT', '1h', db_path=db_path)
        assert perf is not None, "Should have summary row"
        assert perf['wins'] == 2, f"Expected 2 wins, got {perf['wins']}"
        assert perf['losses'] == 1, f"Expected 1 loss, got {perf['losses']}"
        assert perf['timeouts'] == 1, f"Expected 1 timeout, got {perf['timeouts']}"
        assert perf['total_signals'] == 4, f"Expected total 4, got {perf['total_signals']}"
        print(f"  PASS: counts = wins={perf['wins']} losses={perf['losses']} "
              f"timeouts={perf['timeouts']} total={perf['total_signals']}")

        # win_rate should be over decided (win+loss), excluding timeout
        # 2 wins / 3 decided = 0.6667
        assert perf['win_rate'] == round(2/3, 4), \
            f"Expected win_rate {round(2/3, 4)}, got {perf['win_rate']}"
        print(f"  PASS: win_rate = {perf['win_rate']} (decided-only denominator)")
    finally:
        os.unlink(db_path)

    print("  TEST 2 PASSED")


# ============================================================
# TEST 3: profit_factor_proxy correctness
# ============================================================
def test_profit_factor_proxy():
    print("\n" + "="*60)
    print("TEST 3: profit_factor_proxy from price distances")
    print("="*60)

    db_path = setup_test_db()
    try:
        engine = OutcomeEngine(db_path)
        conn = sqlite3.connect(db_path)

        insert_signal(conn, 1, 'BTCUSDT', '1h')
        insert_signal(conn, 2, 'BTCUSDT', '1h')

        # WIN: entry=100, tp=110 -> distance = 10
        engine.save_outcome(make_outcome(1, 'BTCUSDT', '1h', 'win',
                                          entry=100, tp=110, sl=95,
                                          exit_price=110, holding_hours=10.0))
        # LOSS: entry=100, sl=95 -> distance = 5
        engine.save_outcome(make_outcome(2, 'BTCUSDT', '1h', 'loss',
                                          entry=100, tp=110, sl=95,
                                          exit_price=95, holding_hours=8.0))

        conn.close()

        perf = get_model_performance('BTCUSDT', '1h', db_path=db_path)
        # gross_win = 10, gross_loss = 5 -> PF = 2.0
        assert perf['profit_factor_proxy'] == 2.0, \
            f"Expected PF 2.0, got {perf['profit_factor_proxy']}"
        print(f"  PASS: profit_factor_proxy = {perf['profit_factor_proxy']} (10/5)")

        # avg_holding_hours = (10 + 8) / 2 = 9.0
        assert perf['avg_holding_hours'] == 9.0, \
            f"Expected avg_holding_hours 9.0, got {perf['avg_holding_hours']}"
        print(f"  PASS: avg_holding_hours = {perf['avg_holding_hours']}")
    finally:
        os.unlink(db_path)

    print("  TEST 3 PASSED")


# ============================================================
# TEST 4: Multiple pairs are independent
# ============================================================
def test_multiple_pairs_independent():
    print("\n" + "="*60)
    print("TEST 4: Multiple (symbol, timeframe) pairs tracked independently")
    print("="*60)

    db_path = setup_test_db()
    try:
        engine = OutcomeEngine(db_path)
        conn = sqlite3.connect(db_path)

        insert_signal(conn, 1, 'BTCUSDT', '1h')
        insert_signal(conn, 2, 'ETHUSDT', '1h')
        insert_signal(conn, 3, 'BTCUSDT', '4h')

        engine.save_outcome(make_outcome(1, 'BTCUSDT', '1h', 'win',
                                          entry=100, tp=105, sl=95,
                                          exit_price=105, holding_hours=5.0))
        engine.save_outcome(make_outcome(2, 'ETHUSDT', '1h', 'loss',
                                          entry=50, tp=55, sl=48,
                                          exit_price=48, holding_hours=3.0))
        engine.save_outcome(make_outcome(3, 'BTCUSDT', '4h', 'timeout',
                                          entry=100, tp=110, sl=90))

        conn.close()

        btc_1h = get_model_performance('BTCUSDT', '1h', db_path=db_path)
        eth_1h = get_model_performance('ETHUSDT', '1h', db_path=db_path)
        btc_4h = get_model_performance('BTCUSDT', '4h', db_path=db_path)

        assert btc_1h['wins'] == 1 and btc_1h['total_signals'] == 1
        assert eth_1h['losses'] == 1 and eth_1h['total_signals'] == 1
        assert btc_4h['timeouts'] == 1 and btc_4h['total_signals'] == 1
        print("  PASS: Each (symbol, timeframe) pair tracked independently")

        # get_symbol_performance should return all BTCUSDT timeframes
        btc_all = get_symbol_performance('BTCUSDT', db_path=db_path)
        assert len(btc_all) == 2, f"Expected 2 BTC timeframes, got {len(btc_all)}"
        timeframes = [r['timeframe'] for r in btc_all]
        assert set(timeframes) == {'1h', '4h'}
        print(f"  PASS: get_symbol_performance returns {len(btc_all)} timeframes")
    finally:
        os.unlink(db_path)

    print("  TEST 4 PASSED")


# ============================================================
# TEST 5: get_global_performance aggregates correctly
# ============================================================
def test_global_performance():
    print("\n" + "="*60)
    print("TEST 5: get_global_performance aggregates across pairs")
    print("="*60)

    db_path = setup_test_db()
    try:
        engine = OutcomeEngine(db_path)
        conn = sqlite3.connect(db_path)

        for sid in [1, 2, 3, 4]:
            insert_signal(conn, sid, 'BTCUSDT', '1h')

        # 3 wins, 1 loss (4 decided)
        engine.save_outcome(make_outcome(1, 'BTCUSDT', '1h', 'win',
                                          entry=100, tp=110, sl=95,
                                          exit_price=110, holding_hours=10.0))
        engine.save_outcome(make_outcome(2, 'BTCUSDT', '1h', 'win',
                                          entry=100, tp=108, sl=95,
                                          exit_price=108, holding_hours=12.0))
        engine.save_outcome(make_outcome(3, 'BTCUSDT', '1h', 'win',
                                          entry=100, tp=105, sl=95,
                                          exit_price=105, holding_hours=8.0))
        engine.save_outcome(make_outcome(4, 'BTCUSDT', '1h', 'loss',
                                          entry=100, tp=110, sl=90,
                                          exit_price=90, holding_hours=6.0))

        conn.close()

        glob = get_global_performance(db_path=db_path)

        assert glob['wins'] == 3, f"Expected 3 wins, got {glob['wins']}"
        assert glob['losses'] == 1, f"Expected 1 loss, got {glob['losses']}"
        assert glob['total_signals'] == 4
        # win_rate = 3/4 = 0.75
        assert glob['win_rate'] == 0.75, f"Expected win_rate 0.75, got {glob['win_rate']}"
        print(f"  PASS: global wins={glob['wins']} losses={glob['losses']} "
              f"win_rate={glob['win_rate']}")

        # profit_factor: (10 + 8 + 5) / 10 = 2.3
        # gross_win = |110-100| + |108-100| + |105-100| = 10+8+5 = 23
        # gross_loss = |100-90| = 10
        # PF = 23/10 = 2.3
        assert glob['profit_factor_proxy'] == 2.3, \
            f"Expected PF 2.3, got {glob['profit_factor_proxy']}"
        print(f"  PASS: global profit_factor_proxy = {glob['profit_factor_proxy']}")

        # avg_holding_hours = (10+12+8+6)/4 = 9.0
        assert glob['avg_holding_hours'] == 9.0, \
            f"Expected avg_holding_hours 9.0, got {glob['avg_holding_hours']}"
        print(f"  PASS: global avg_holding_hours = {glob['avg_holding_hours']}")

        # pairs breakdown
        assert 'pairs' in glob and len(glob['pairs']) >= 1
        print(f"  PASS: pairs breakdown contains {len(glob['pairs'])} entries")
    finally:
        os.unlink(db_path)

    print("  TEST 5 PASSED")


# ============================================================
# TEST 6: Re-saving (correction) doesn't double-count
# ============================================================
def test_correction_no_double_count():
    print("\n" + "="*60)
    print("TEST 6: Re-saving an outcome (correction) doesn't double-count")
    print("="*60)

    db_path = setup_test_db()
    try:
        engine = OutcomeEngine(db_path)
        conn = sqlite3.connect(db_path)

        insert_signal(conn, 1, 'BTCUSDT', '1h')

        # First save as timeout
        engine.save_outcome(make_outcome(1, 'BTCUSDT', '1h', 'timeout',
                                          entry=100, tp=110, sl=90))

        # Then correct to win (e.g. after late candle data arrives)
        engine.save_outcome(make_outcome(1, 'BTCUSDT', '1h', 'win',
                                          entry=100, tp=110, sl=90,
                                          exit_price=110, holding_hours=50.0))
        conn.close()

        perf = get_model_performance('BTCUSDT', '1h', db_path=db_path)
        # signal_outcomes has UNIQUE(signal_id) so only one row exists.
        # Summary is recomputed from signal_outcomes, so no double-count.
        assert perf['total_signals'] == 1, \
            f"Expected total 1 after correction, got {perf['total_signals']}"
        assert perf['wins'] == 1, f"Expected 1 win, got {perf['wins']}"
        assert perf['timeouts'] == 0, f"Expected 0 timeouts, got {perf['timeouts']}"
        print(f"  PASS: After correction -> wins={perf['wins']} timeouts={perf['timeouts']} "
              f"total={perf['total_signals']}")
    finally:
        os.unlink(db_path)

    print("  TEST 6 PASSED")


# ============================================================
# RUN ALL TESTS
# ============================================================
if __name__ == '__main__':
    print("\n" + "="*60)
    print("PERFORMANCE MEASUREMENT FOUNDATION - VALIDATION TESTS")
    print("="*60)

    passed = 0
    failed = 0

    for test in [
        test_table_auto_created,
        test_counters_increment,
        test_profit_factor_proxy,
        test_multiple_pairs_independent,
        test_global_performance,
        test_correction_no_double_count,
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
