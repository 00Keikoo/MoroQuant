"""SQLite storage layer for experiment registry."""

import sqlite3
from typing import List, Dict, Any, Optional
from pathlib import Path


DB_PATH = Path(__file__).parent.parent.parent.parent / "storage" / "database.db"


def get_connection() -> sqlite3.Connection:
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def insert_experiment(experiment_id: str, snapshot_id: str, created_at: str):
    """Insert experiment metadata."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO experiments (experiment_id, snapshot_id, created_at) VALUES (?, ?, ?)",
            (experiment_id, snapshot_id, created_at)
        )
        conn.commit()
    finally:
        conn.close()


def insert_config(
    experiment_id: str,
    config_id: str,
    threshold_long: float,
    threshold_short: float,
    regime_filter: Optional[str]
):
    """Insert strategy config."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO experiment_configs
               (experiment_id, config_id, threshold_long, threshold_short, regime_filter)
               VALUES (?, ?, ?, ?, ?)""",
            (experiment_id, config_id, threshold_long, threshold_short, regime_filter)
        )
        conn.commit()
    finally:
        conn.close()


def insert_result(
    experiment_id: str,
    config_id: str,
    pnl: float,
    winrate: float,
    sharpe: float,
    max_drawdown: float,
    consistency_score: float,
    trade_count: int
):
    """Insert strategy result."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO experiment_results
               (experiment_id, config_id, pnl, winrate, sharpe, max_drawdown, consistency_score, trade_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (experiment_id, config_id, pnl, winrate, sharpe, max_drawdown, consistency_score, trade_count)
        )
        conn.commit()
    finally:
        conn.close()


def select_experiment(experiment_id: str) -> Optional[Dict[str, Any]]:
    """Load experiment metadata."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT experiment_id, snapshot_id, created_at FROM experiments WHERE experiment_id = ?",
            (experiment_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def select_configs(experiment_id: str) -> List[Dict[str, Any]]:
    """Load all configs for an experiment."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """SELECT config_id, threshold_long, threshold_short, regime_filter
               FROM experiment_configs WHERE experiment_id = ?""",
            (experiment_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def select_results(experiment_id: str) -> List[Dict[str, Any]]:
    """Load all results for an experiment."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """SELECT config_id, pnl, winrate, sharpe, max_drawdown, consistency_score, trade_count
               FROM experiment_results WHERE experiment_id = ?""",
            (experiment_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def select_all_experiments() -> List[Dict[str, Any]]:
    """List all experiments."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT experiment_id, snapshot_id, created_at FROM experiments ORDER BY created_at DESC"
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
