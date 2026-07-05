"""Regression tests for paper broker lifecycle engineering audit fixes.

Tests cover:
1. SHORT closes immediately after SL hit
2. LONG closes immediately after SL hit
3. One failed symbol does not stop remaining symbols
4. Mark Price endpoint is used instead of Last Price
5. Missed stop scenario (price gaps through SL)
"""

import sys
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import ml_service.trading.mode_manager as mm
import ml_service.trading.paper_broker as pb
from ml_service.trading.paper_broker import (
    update_open_positions,
    _fetch_mark_price,
)


@pytest.fixture(autouse=True)
def db_path(monkeypatch):
    """Each test gets its own temp DB."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    test_db = Path(tmp.name)
    saved_mm = mm._DB_PATH
    saved_pb = pb._DB_PATH
    monkeypatch.setattr(mm, "_DB_PATH", test_db)
    monkeypatch.setattr(pb, "_DB_PATH", test_db)
    yield test_db
    mm._DB_PATH = saved_mm
    pb._DB_PATH = saved_pb
    if test_db.exists():
        test_db.unlink()


def _reset_db(db_path: Path):
    """Wipe and recreate all tables."""
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS trading_system_state (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            trading_mode TEXT NOT NULL DEFAULT 'OFF',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO trading_system_state (id, trading_mode) VALUES (1, 'PAPER');

        CREATE TABLE IF NOT EXISTS paper_account (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            balance REAL NOT NULL DEFAULT 10000.0,
            equity REAL NOT NULL DEFAULT 10000.0,
            unrealized_pnl REAL NOT NULL DEFAULT 0.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO paper_account (id, balance, equity, unrealized_pnl)
        VALUES (1, 10000.0, 10000.0, 0.0);

        CREATE TABLE IF NOT EXISTS paper_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL NOT NULL,
            current_price REAL,
            size_usdt REAL NOT NULL,
            qty REAL NOT NULL,
            stop_loss REAL,
            take_profit REAL,
            signal_id INTEGER,
            status TEXT NOT NULL DEFAULT 'OPEN',
            realized_pnl REAL NOT NULL DEFAULT 0.0,
            opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP,
            confidence INTEGER,
            regime TEXT,
            timeframe TEXT,
            prob_short REAL,
            prob_neutral REAL,
            prob_long REAL,
            execution_edge REAL,
            skip_reason TEXT,
            mae REAL DEFAULT 0.0,
            mfe REAL DEFAULT 0.0,
            mae_timestamp TIMESTAMP,
            mfe_timestamp TIMESTAMP,
            profit_capture_ratio REAL,
            final_exit_reason TEXT,
            trailing_stop_activated INTEGER DEFAULT 0,
            sl_move_count INTEGER DEFAULT 0,
            break_even_triggered INTEGER DEFAULT 0,
            execution_policy TEXT DEFAULT 'FIXED_SL'
        );
    """)
    conn.commit()
    conn.close()


def _insert_open_position(db_path: Path, symbol, direction, entry_price,
                          qty=1.0, current_price=None, tp=None, sl=None,
                          opened_at=None):
    """Insert a raw OPEN position bypassing the open() logic."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """INSERT INTO paper_positions
           (symbol, direction, entry_price, current_price, size_usdt, qty,
            stop_loss, take_profit, status, realized_pnl, opened_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', 0.0, ?)""",
        (symbol, direction, entry_price, current_price or entry_price,
         qty * entry_price, qty, sl, tp,
         opened_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


def _get_position_status(db_path: Path, position_id: int):
    """Get position status."""
    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT status FROM paper_positions WHERE id = ?", (position_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else None


# ─── Test 1: SHORT closes immediately after SL ──────────────────────────────


def test_short_closes_immediately_on_sl_hit(db_path, monkeypatch):
    """Regression: SHORT position closes immediately when mark price hits SL."""
    _reset_db(db_path)

    # SHORT entry=100, sl=110 (above entry)
    # Mark price moves to 111 → SL_HIT
    _insert_open_position(db_path, "ETHUSDT", "SHORT", 100.0, qty=1.0,
                         current_price=100.0, tp=90.0, sl=110.0)

    # Mock mark price to return 111 (above SL)
    monkeypatch.setattr(pb, "_fetch_mark_price", lambda symbol: 111.0)
    monkeypatch.setattr(pb, "_fetch_price", lambda symbol: 111.0)

    summary = update_open_positions()

    assert summary["sl"] == 1, "SHORT should close on SL hit"
    assert summary["checked"] == 1
    assert _get_position_status(db_path, 1) == "SL_HIT"
    print("✓ SHORT closes immediately on SL hit")


# ─── Test 2: LONG closes immediately after SL ───────────────────────────────


def test_long_closes_immediately_on_sl_hit(db_path, monkeypatch):
    """Regression: LONG position closes immediately when mark price hits SL."""
    _reset_db(db_path)

    # LONG entry=100, sl=90 (below entry)
    # Mark price moves to 89 → SL_HIT
    _insert_open_position(db_path, "BTCUSDT", "LONG", 100.0, qty=1.0,
                         current_price=100.0, tp=110.0, sl=90.0)

    # Mock mark price to return 89 (below SL)
    monkeypatch.setattr(pb, "_fetch_mark_price", lambda symbol: 89.0)
    monkeypatch.setattr(pb, "_fetch_price", lambda symbol: 89.0)

    summary = update_open_positions()

    assert summary["sl"] == 1, "LONG should close on SL hit"
    assert summary["checked"] == 1
    assert _get_position_status(db_path, 1) == "SL_HIT"
    print("✓ LONG closes immediately on SL hit")


# ─── Test 3: One failed symbol does not stop remaining symbols ──────────────


def test_failed_symbol_does_not_stop_remaining_symbols(db_path, monkeypatch):
    """Regression: Exception in one position evaluation doesn't stop others."""
    _reset_db(db_path)

    # Insert 3 positions
    _insert_open_position(db_path, "BTCUSDT", "LONG", 100.0, qty=1.0,
                         current_price=100.0, tp=110.0, sl=90.0)
    _insert_open_position(db_path, "ETHUSDT", "LONG", 200.0, qty=1.0,
                         current_price=200.0, tp=220.0, sl=180.0)
    _insert_open_position(db_path, "BNBUSDT", "LONG", 300.0, qty=1.0,
                         current_price=300.0, tp=330.0, sl=270.0)

    call_count = {"count": 0}

    def failing_mark_price(symbol):
        call_count["count"] += 1
        # Fail on ETHUSDT
        if symbol == "ETHUSDT":
            raise Exception("Network timeout")
        # Close BNBUSDT on SL
        if symbol == "BNBUSDT":
            return 260.0  # Below SL
        return 105.0  # Safe for BTCUSDT

    monkeypatch.setattr(pb, "_fetch_mark_price", failing_mark_price)
    monkeypatch.setattr(pb, "_fetch_price", lambda symbol: 100.0)

    summary = update_open_positions()

    # All 3 positions should be checked
    assert summary["checked"] == 3, "All positions should be evaluated"
    # BNBUSDT should close on SL despite ETHUSDT failure
    assert summary["sl"] == 1, "BNBUSDT should close on SL"
    assert _get_position_status(db_path, 1) == "OPEN", "BTCUSDT still open"
    assert _get_position_status(db_path, 2) == "OPEN", "ETHUSDT still open (failed)"
    assert _get_position_status(db_path, 3) == "SL_HIT", "BNBUSDT closed on SL"
    print("✓ Failed symbol isolation works - remaining positions processed")


# ─── Test 4: Mark Price endpoint is used ─────────────────────────────────────


def test_mark_price_endpoint_used_for_tp_sl_evaluation(db_path, monkeypatch):
    """Regression: TP/SL evaluation uses Mark Price, not Last Price."""
    _reset_db(db_path)

    # LONG entry=100, sl=90, tp=110
    _insert_open_position(db_path, "BTCUSDT", "LONG", 100.0, qty=1.0,
                         current_price=100.0, tp=110.0, sl=90.0)

    # Mock Last Price = 95 (safe), Mark Price = 89 (below SL)
    # If using Last Price → HOLD
    # If using Mark Price → SL_HIT
    monkeypatch.setattr(pb, "_fetch_price", lambda symbol: 95.0)
    monkeypatch.setattr(pb, "_fetch_mark_price", lambda symbol: 89.0)

    summary = update_open_positions()

    # Position should close because Mark Price hit SL
    assert summary["sl"] == 1, "Position should close on Mark Price SL hit"
    assert _get_position_status(db_path, 1) == "SL_HIT"
    print("✓ Mark Price endpoint used for TP/SL evaluation")


def test_mark_price_fallback_to_last_price(db_path, monkeypatch):
    """Regression: If Mark Price unavailable, fallback to Last Price."""
    _reset_db(db_path)

    _insert_open_position(db_path, "BTCUSDT", "LONG", 100.0, qty=1.0,
                         current_price=100.0, tp=110.0, sl=90.0)

    # Mock Mark Price fetch failure, Last Price = 89 (below SL)
    monkeypatch.setattr(pb, "_fetch_mark_price", lambda symbol: None)
    monkeypatch.setattr(pb, "_fetch_price", lambda symbol: 89.0)

    summary = update_open_positions()

    # Should still close using fallback Last Price
    assert summary["sl"] == 1, "Should close using fallback Last Price"
    print("✓ Mark Price fallback to Last Price works")


# ─── Test 5: Missed stop scenario ───────────────────────────────────────────


def test_missed_stop_scenario_with_1min_lifecycle(db_path, monkeypatch):
    """Regression: Price gaps through SL, caught by 1-minute lifecycle.

    Scenario:
    - Entry = 100, SL = 102
    - Price moves: 100 → 102.2 → 101
    - With 1-hour lifecycle: missed stop (price back below SL)
    - With 1-minute lifecycle: caught at 102.2
    """
    _reset_db(db_path)

    # SHORT entry=100, sl=102
    _insert_open_position(db_path, "BTCUSDT", "SHORT", 100.0, qty=1.0,
                         current_price=100.0, tp=90.0, sl=102.0)

    # Simulate 3 lifecycle checks at 1-minute intervals

    # Check 1: Price at 100 (entry) → HOLD
    monkeypatch.setattr(pb, "_fetch_mark_price", lambda symbol: 100.0)
    monkeypatch.setattr(pb, "_fetch_price", lambda symbol: 100.0)
    summary1 = update_open_positions()
    assert summary1["sl"] == 0
    assert _get_position_status(db_path, 1) == "OPEN"

    # Check 2: Price gaps to 102.2 (above SL) → SL_HIT
    monkeypatch.setattr(pb, "_fetch_mark_price", lambda symbol: 102.2)
    monkeypatch.setattr(pb, "_fetch_price", lambda symbol: 102.2)
    summary2 = update_open_positions()
    assert summary2["sl"] == 1, "Should catch stop at 102.2"
    assert _get_position_status(db_path, 1) == "SL_HIT"

    print("✓ Missed stop scenario caught with 1-minute lifecycle")


def test_missed_stop_not_caught_with_hourly_lifecycle(db_path, monkeypatch):
    """Demonstration: Price gap missed with hourly checks.

    This simulates the OLD behavior before 1-minute lifecycle.
    """
    _reset_db(db_path)

    # SHORT entry=100, sl=102
    _insert_open_position(db_path, "BTCUSDT", "SHORT", 100.0, qty=1.0,
                         current_price=100.0, tp=90.0, sl=102.0)

    # Simulate only one check per hour
    # Price is at 101 when checked (after gapping through 102.2)
    monkeypatch.setattr(pb, "_fetch_mark_price", lambda symbol: 101.0)
    monkeypatch.setattr(pb, "_fetch_price", lambda symbol: 101.0)

    summary = update_open_positions()

    # Position stays open because price is below SL when checked
    assert summary["sl"] == 0, "Stop missed with hourly checks"
    assert _get_position_status(db_path, 1) == "OPEN"
    print("✓ Demonstrated: hourly lifecycle can miss stops")


# ─── Test 6: Scheduler frequency verification ───────────────────────────────


def test_scheduler_uses_1_minute_interval():
    """Regression: Verify scheduler is configured for 1-minute lifecycle."""
    import ml_service.scheduler as scheduler_module
    from apscheduler.triggers.interval import IntervalTrigger

    try:
        scheduler_module.start_scheduler()

        # Access _scheduler before it gets set to None
        sched = scheduler_module._scheduler
        assert sched is not None, "Scheduler should be running"

        job = sched.get_job('paper_lifecycle_job')
        assert job is not None, "paper_lifecycle_job not found"

        trigger = job.trigger
        assert isinstance(trigger, IntervalTrigger), "Wrong trigger type"
        assert trigger.interval.total_seconds() == 60, "Should be 1 minute (60 seconds)"

        print("✓ Scheduler configured for 1-minute lifecycle")
    finally:
        scheduler_module.stop_scheduler()


# ─── Test 7: Multiple positions, mixed outcomes ─────────────────────────────


def test_multiple_positions_mixed_outcomes(db_path, monkeypatch):
    """Regression: Multiple positions with different outcomes in one pass."""
    _reset_db(db_path)

    # Position 1: LONG, TP hit
    _insert_open_position(db_path, "BTCUSDT", "LONG", 100.0, qty=1.0,
                         current_price=100.0, tp=110.0, sl=90.0)
    # Position 2: SHORT, SL hit
    _insert_open_position(db_path, "ETHUSDT", "SHORT", 200.0, qty=1.0,
                         current_price=200.0, tp=180.0, sl=210.0)
    # Position 3: LONG, HOLD
    _insert_open_position(db_path, "BNBUSDT", "LONG", 300.0, qty=1.0,
                         current_price=300.0, tp=330.0, sl=270.0)

    def mark_price_by_symbol(symbol):
        if symbol == "BTCUSDT":
            return 111.0  # Above TP
        elif symbol == "ETHUSDT":
            return 211.0  # Above SL
        elif symbol == "BNBUSDT":
            return 305.0  # In range
        return 100.0

    monkeypatch.setattr(pb, "_fetch_mark_price", mark_price_by_symbol)
    monkeypatch.setattr(pb, "_fetch_price", mark_price_by_symbol)

    summary = update_open_positions()

    assert summary["checked"] == 3
    assert summary["tp"] == 1, "BTCUSDT TP hit"
    assert summary["sl"] == 1, "ETHUSDT SL hit"
    assert _get_position_status(db_path, 1) == "TP_HIT"
    assert _get_position_status(db_path, 2) == "SL_HIT"
    assert _get_position_status(db_path, 3) == "OPEN"
    print("✓ Multiple positions with mixed outcomes processed correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
