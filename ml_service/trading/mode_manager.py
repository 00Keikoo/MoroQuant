"""Trading Mode Manager for MoroQuant.

Controls the autonomous trading mode across the system. Provides a single
source of truth for whether the system may open new positions or execute
live orders, persisted in SQLite so mode survives restarts.

Modes
-----
OFF         – No new trades, no paper execution, no live execution.
PAPER       – Allow paper trades only (no live orders).
LIVE        – Allow real Binance execution.
MAINTENANCE – Block new trades; monitoring / analytics / attribution continue.
"""

import sqlite3
from pathlib import Path
from typing import Optional

from ml_service.utils.logger import get_logger

logger = get_logger()

# ── Valid modes ───────────────────────────────────────────────────────────

VALID_MODES = ["OFF", "PAPER", "LIVE", "MAINTENANCE"]

# ── Permission matrix ─────────────────────────────────────────────────────

_PERMISSION_MATRIX = {
    "OFF":         {"can_open": False, "can_execute_live": False},
    "PAPER":       {"can_open": True,  "can_execute_live": False},
    "LIVE":        {"can_open": True,  "can_execute_live": True},
    "MAINTENANCE": {"can_open": False, "can_execute_live": False},
}

# ── Internal helpers ───────────────────────────────────────────────────────

_DB_PATH: Path = Path(__file__).parent.parent / "storage" / "database.db"


def _get_connection():
    """Return a raw SQLite connection to the shared database."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_table(conn: sqlite3.Connection):
    """Create the trading_system_state table + singleton row if missing."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trading_system_state (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            trading_mode TEXT NOT NULL DEFAULT 'OFF',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Insert the singleton row when the table is fresh.
    conn.execute(
        "INSERT OR IGNORE INTO trading_system_state (id, trading_mode) VALUES (1, 'OFF')"
    )
    conn.commit()


# ── Public API ─────────────────────────────────────────────────────────────

def get_trading_mode() -> str:
    """Return the current trading mode (default 'OFF').

    On first call the table is created and the default mode is persisted.
    """
    conn = _get_connection()
    try:
        _ensure_table(conn)
        row = conn.execute(
            "SELECT trading_mode FROM trading_system_state WHERE id = 1"
        ).fetchone()
        return row["trading_mode"] if row else "OFF"
    finally:
        conn.close()


def set_trading_mode(mode: str) -> bool:
    """Persist a new trading mode.

    Returns True on success, False if *mode* is invalid.
    """
    if mode not in VALID_MODES:
        logger.warning(f"Rejected invalid trading mode: {mode}")
        return False

    conn = _get_connection()
    try:
        _ensure_table(conn)
        conn.execute(
            "UPDATE trading_system_state SET trading_mode = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
            (mode,),
        )
        conn.commit()
        logger.info(f"Trading mode changed to {mode}")
        return True
    finally:
        conn.close()


def can_open_new_positions() -> bool:
    """Whether the system is allowed to open new positions.

    OFF/Maintenance → False; Paper/Live → True.
    """
    mode = get_trading_mode()
    return _PERMISSION_MATRIX.get(mode, _PERMISSION_MATRIX["OFF"])["can_open"]


def can_execute_live_orders() -> bool:
    """Whether the system is allowed to send real orders to Binance.

    Only LIVE mode returns True.
    """
    mode = get_trading_mode()
    return _PERMISSION_MATRIX.get(mode, _PERMISSION_MATRIX["OFF"])["can_execute_live"]


def is_maintenance_mode() -> bool:
    """Whether the system is in maintenance mode."""
    return get_trading_mode() == "MAINTENANCE"


def emergency_stop() -> dict:
    """Immediately switch mode to OFF and return the transition details.

    Returns a dict with ``success``, ``old_mode``, and ``new_mode`` keys.
    """
    old_mode = get_trading_mode()
    conn = _get_connection()
    try:
        _ensure_table(conn)
        conn.execute(
            "UPDATE trading_system_state SET trading_mode = 'OFF', updated_at = CURRENT_TIMESTAMP WHERE id = 1"
        )
        conn.commit()
    finally:
        conn.close()

    logger.warning(f"EMERGENCY STOP executed: {old_mode} → OFF")
    return {"success": True, "old_mode": old_mode, "new_mode": "OFF"}
