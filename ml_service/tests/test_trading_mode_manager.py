"""Unit tests for ml_service.trading.mode_manager."""

import sys
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

# Ensure ml_service root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import trading.mode_manager as mm
from ml_service.trading.mode_manager import (
    VALID_MODES,
    get_trading_mode,
    set_trading_mode,
    can_open_new_positions,
    can_execute_live_orders,
    is_maintenance_mode,
    emergency_stop,
)


@pytest.fixture(autouse=True)
def db_path(monkeypatch):
    """Each test gets its own temp DB; module-level _DB_PATH is saved & restored."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    test_db = Path(tmp.name)
    saved = mm._DB_PATH
    monkeypatch.setattr(mm, "_DB_PATH", test_db)
    yield test_db
    mm._DB_PATH = saved
    if test_db.exists():
        test_db.unlink()


def _reset_db(db_path: Path):
    """Wipe the test DB so each test starts clean."""
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trading_system_state (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            trading_mode TEXT NOT NULL DEFAULT 'OFF',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute(
        "INSERT OR IGNORE INTO trading_system_state (id, trading_mode) VALUES (1, 'OFF')"
    )
    conn.commit()
    conn.close()


# ─── 1. Default mode ─────────────────────────────────────────────────────

def test_default_mode_is_off(db_path):
    """Fresh DB should return OFF."""
    _reset_db(db_path)
    assert get_trading_mode() == "OFF"
    print("✓ Default mode is OFF")


# ─── 2. Set / Get ────────────────────────────────────────────────────────

def test_set_get_roundtrip(db_path):
    """set_trading_mode persists and get_trading_mode reads it back."""
    _reset_db(db_path)
    for mode in VALID_MODES:
        assert set_trading_mode(mode) is True
        assert get_trading_mode() == mode
    print(f"✓ Set/get roundtrip for all modes: {VALID_MODES}")


def test_set_mode_case_insensitive(db_path):
    """set_trading_mode should reject lowercase (validation is caller-side)."""
    _reset_db(db_path)
    # The function accepts the literal string; lowercase is NOT in VALID_MODES
    assert set_trading_mode("paper") is False
    assert get_trading_mode() == "OFF"  # unchanged
    print("✓ Invalid (lowercase) mode rejected")


# ─── 3. Invalid mode rejection ────────────────────────────────────────────

def test_invalid_mode_rejected(db_path):
    """Arbitrary strings are rejected."""
    _reset_db(db_path)
    for bad in ["", "DEMO", "TRADING", "Live", "off", None]:
        result = set_trading_mode(bad)
        assert result is False, f"Expected False for {bad!r}, got {result}"
    assert get_trading_mode() == "OFF"
    print("✓ All invalid modes rejected")


# ─── 4. Persistence after reload ──────────────────────────────────────────

def test_persistence_after_reload(db_path):
    """Mode survives closing and reopening the DB connection."""
    _reset_db(db_path)
    set_trading_mode("LIVE")
    assert get_trading_mode() == "LIVE"

    # Simulate "reload" by wiping the module-level cache (mode_manager uses
    # direct connections, not a singleton, so just reading again is enough).
    mode = get_trading_mode()
    assert mode == "LIVE"
    print("✓ Mode persists across reads (simulated reload)")


def test_persists_across_db_reopen(db_path):
    """Mode survives physical DB file close/reopen."""
    _reset_db(db_path)
    set_trading_mode("PAPER")

    # Reopen the DB from scratch
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT trading_mode FROM trading_system_state WHERE id = 1"
    ).fetchone()
    conn.close()
    assert row["trading_mode"] == "PAPER"
    print("✓ Mode persists across physical DB reopen")


# ─── 5. Emergency stop ────────────────────────────────────────────────────

def test_emergency_stop_from_live(db_path):
    """Emergency stop from LIVE → OFF."""
    _reset_db(db_path)
    set_trading_mode("LIVE")
    result = emergency_stop()
    assert result["success"] is True
    assert result["old_mode"] == "LIVE"
    assert result["new_mode"] == "OFF"
    assert get_trading_mode() == "OFF"
    print("✓ Emergency stop: LIVE → OFF")


def test_emergency_stop_from_paper(db_path):
    """Emergency stop from PAPER → OFF."""
    _reset_db(db_path)
    set_trading_mode("PAPER")
    result = emergency_stop()
    assert result["old_mode"] == "PAPER"
    assert result["new_mode"] == "OFF"
    print("✓ Emergency stop: PAPER → OFF")


def test_emergency_stop_when_already_off(db_path):
    """Emergency stop when already OFF is still a success."""
    _reset_db(db_path)
    result = emergency_stop()
    assert result["success"] is True
    assert result["old_mode"] == "OFF"
    assert result["new_mode"] == "OFF"
    print("✓ Emergency stop when already OFF: idempotent")


# ─── 6. Permission matrix ────────────────────────────────────────────────

def test_permission_matrix_off(db_path):
    _reset_db(db_path)
    set_trading_mode("OFF")
    assert can_open_new_positions() is False
    assert can_execute_live_orders() is False
    assert is_maintenance_mode() is False
    print("✓ OFF: can_open=F, can_execute=F, maintenance=F")


def test_permission_matrix_paper(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    assert can_open_new_positions() is True
    assert can_execute_live_orders() is False
    assert is_maintenance_mode() is False
    print("✓ PAPER: can_open=T, can_execute=F, maintenance=F")


def test_permission_matrix_live(db_path):
    _reset_db(db_path)
    set_trading_mode("LIVE")
    assert can_open_new_positions() is True
    assert can_execute_live_orders() is True
    assert is_maintenance_mode() is False
    print("✓ LIVE: can_open=T, can_execute=T, maintenance=F")


def test_permission_matrix_maintenance(db_path):
    _reset_db(db_path)
    set_trading_mode("MAINTENANCE")
    assert can_open_new_positions() is False
    assert can_execute_live_orders() is False
    assert is_maintenance_mode() is True
    print("✓ MAINTENANCE: can_open=F, can_execute=F, maintenance=T")


def test_full_permission_matrix(db_path):
    """Comprehensive matrix check."""
    _reset_db(db_path)
    expected = {
        "OFF":         {"open": False, "live": False, "maint": False},
        "PAPER":       {"open": True,  "live": False, "maint": False},
        "LIVE":        {"open": True,  "live": True,  "maint": False},
        "MAINTENANCE": {"open": False, "live": False, "maint": True},
    }
    for mode, perm in expected.items():
        set_trading_mode(mode)
        assert can_open_new_positions() == perm["open"], f"{mode} can_open mismatch"
        assert can_execute_live_orders() == perm["live"], f"{mode} can_execute mismatch"
        assert is_maintenance_mode() == perm["maint"], f"{mode} maintenance mismatch"
    print("✓ Full permission matrix validated")


# ─── 7. Table auto-creation ──────────────────────────────────────────────

def test_table_auto_created(db_path):
    """Mode manager creates the table and row if they don't exist."""
    if db_path.exists():
        db_path.unlink()
    # No manual table creation — mode_manager should handle it
    assert get_trading_mode() == "OFF"
    print("✓ Table and row auto-created on first access")
