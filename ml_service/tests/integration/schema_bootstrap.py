"""Bootstrap real SQLite schema for integration tests.

Based on migration 026 - complete schema with 32 columns.
"""

import sqlite3
from pathlib import Path
from typing import Optional


def create_test_schema(db_path: str) -> None:
    """Initialize test database with complete schema."""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paper_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL CHECK(direction IN ('LONG', 'SHORT')),
                entry_price REAL NOT NULL,
                current_price REAL,
                size_usdt REAL NOT NULL,
                qty REAL NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                signal_id INTEGER,
                status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'TP_HIT', 'SL_HIT', 'EXPIRED', 'MANUAL_CLOSE')),
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
                execution_policy TEXT DEFAULT 'FIXED_SL' CHECK(execution_policy IN ('OFF', 'FIXED_SL', 'BREAK_EVEN', 'TRAILING'))
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_paper_positions_status ON paper_positions(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_paper_positions_symbol ON paper_positions(symbol)
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                direction TEXT NOT NULL,
                confidence INTEGER NOT NULL,
                features_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paper_account (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                balance REAL NOT NULL DEFAULT 10000.0,
                equity REAL NOT NULL DEFAULT 10000.0,
                unrealized_pnl REAL NOT NULL DEFAULT 0.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paper_equity_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equity REAL NOT NULL,
                balance REAL NOT NULL,
                unrealized_pnl REAL NOT NULL,
                snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            INSERT OR IGNORE INTO paper_account (id, balance, equity, unrealized_pnl)
            VALUES (1, 10000.0, 10000.0, 0.0)
        """)

        conn.commit()
    finally:
        conn.close()


def drop_all_tables(db_path: str) -> None:
    """Drop all tables for clean teardown."""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS paper_positions")
        cursor.execute("DROP TABLE IF EXISTS signals")
        cursor.execute("DROP TABLE IF EXISTS paper_account")
        cursor.execute("DROP TABLE IF EXISTS paper_equity_history")
        conn.commit()
    finally:
        conn.close()
