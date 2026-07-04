#!/usr/bin/env python3
"""Regression tests for Migration 027 (backfilling execution metadata)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
import tempfile
import pytest
from unittest.mock import patch

from ml_service.data.database import Database
from ml_service.migrations.run_migration import apply_migration

@pytest.fixture
def migration_027_db():
    """Create a temporary test database containing schema for signals and paper_positions (per 026 target state)."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    db = Database(db_path)

    with db.get_connection() as conn:
        cursor = conn.cursor()
        # schema_migrations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_name TEXT NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # signals table (Drop the default one and create the fully migrated one)
        cursor.execute("DROP TABLE IF EXISTS signals")
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
                sl_multiplier REAL,
                tp_multiplier REAL,
                labeling_method TEXT,
                atr REAL,
                regime TEXT,
                model_version TEXT,
                entry_price REAL,
                take_profit REAL,
                stop_loss REAL,
                prob_short REAL,
                prob_neutral REAL,
                prob_long REAL,
                mtf_alignment TEXT DEFAULT 'NEUTRAL',
                raw_probability_max REAL,
                calibrated_probability_max REAL,
                signal_status TEXT DEFAULT 'ACTIVE',
                status_updated_at TIMESTAMP
            )
        """)

        # paper_positions table (fully migrated target schema per 026)
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
        conn.commit()

    yield db

    Path(db_path).unlink()


def test_migration_027_backfill(migration_027_db):
    """Verify Case A: Rows with NULL metadata become populated (including timeframe).
    Verify Case B: Rows already populated remain unchanged (including timeframe).
    Verify Case C: Running Migration 027 twice produces identical database state.
    Verify Case D: signal_id without matching signal does not fail migration.
    """
    migration_file = Path(__file__).parent.parent / "migrations" / "027_backfill_execution_metadata.sql"

    with migration_027_db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Insert signals
        cursor.execute("""
            INSERT INTO signals (id, symbol, timeframe, timestamp, direction, confidence, regime, prob_short, prob_neutral, prob_long)
            VALUES 
                (101, 'BTCUSDT', '1h', 1700000000, 'long', 75, 'BULL_TREND', 0.1, 0.15, 0.75),
                (102, 'ETHUSDT', '4h', 1700000000, 'short', 65, 'RANGING', 0.65, 0.20, 0.15),
                (103, 'SOLUSDT', '15m', 1700000000, 'long', 80, 'BEAR_TREND', 0.05, 0.15, 0.80)
        """)
        
        # Insert paper_positions representing different test cases:
        # Row 1: Case A - All target metadata is NULL (including timeframe)
        cursor.execute("""
            INSERT INTO paper_positions (id, symbol, direction, entry_price, size_usdt, qty, signal_id, status,
                                         confidence, regime, timeframe, prob_short, prob_neutral, prob_long, execution_edge)
            VALUES (1, 'BTCUSDT', 'LONG', 60000.0, 100.0, 0.0016, 101, 'OPEN',
                    NULL, NULL, NULL, NULL, NULL, NULL, NULL)
        """)

        # Row 2: Case B - Already fully or partially populated rows MUST remain unchanged
        cursor.execute("""
            INSERT INTO paper_positions (id, symbol, direction, entry_price, size_usdt, qty, signal_id, status,
                                         confidence, regime, timeframe, prob_short, prob_neutral, prob_long, execution_edge)
            VALUES (2, 'ETHUSDT', 'SHORT', 3000.0, 100.0, 0.033, 102, 'OPEN',
                    99, 'CUSTOM_REGIME', '1d', 0.9, 0.05, 0.05, 0.85)
        """)

        # Row 3: Case D - signal_id without matching signal in signals table
        cursor.execute("""
            INSERT INTO paper_positions (id, symbol, direction, entry_price, size_usdt, qty, signal_id, status,
                                         confidence, regime, timeframe, prob_short, prob_neutral, prob_long, execution_edge)
            VALUES (3, 'XRPUSDT', 'LONG', 0.5, 100.0, 200.0, 999, 'OPEN',
                    NULL, NULL, NULL, NULL, NULL, NULL, NULL)
        """)

        # Row 4: Mixed - partially populated, check that only NULL fields get backfilled (checking timeframe)
        cursor.execute("""
            INSERT INTO paper_positions (id, symbol, direction, entry_price, size_usdt, qty, signal_id, status,
                                         confidence, regime, timeframe, prob_short, prob_neutral, prob_long, execution_edge)
            VALUES (4, 'SOLUSDT', 'LONG', 150.0, 100.0, 0.66, 103, 'OPEN',
                    50, NULL, NULL, 0.2, NULL, NULL, NULL)
        """)
        conn.commit()

    # 1. Apply Migration 027 first time
    with patch('ml_service.migrations.run_migration.get_database', return_value=migration_027_db):
        success = apply_migration(migration_file)
    assert success is True

    # Check database state after first run
    with migration_027_db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Case A: Row 1 (BTCUSDT) should be backfilled from signal 101
        cursor.execute("SELECT confidence, regime, timeframe, prob_short, prob_neutral, prob_long, execution_edge FROM paper_positions WHERE id = 1")
        row1 = cursor.fetchone()
        assert row1[0] == 75
        assert row1[1] == 'BULL_TREND'
        assert row1[2] == '1h'
        assert abs(row1[3] - 0.1) < 1e-5
        assert abs(row1[4] - 0.15) < 1e-5
        assert abs(row1[5] - 0.75) < 1e-5
        # Execution edge: max(0.1, 0.15, 0.75) - second_max(0.1, 0.15, 0.75) = 0.75 - 0.15 = 0.60
        assert abs(row1[6] - 0.60) < 1e-5

        # Case B: Row 2 (ETHUSDT) must remain unchanged (including timeframe)
        cursor.execute("SELECT confidence, regime, timeframe, prob_short, prob_neutral, prob_long, execution_edge FROM paper_positions WHERE id = 2")
        row2 = cursor.fetchone()
        assert row2[0] == 99
        assert row2[1] == 'CUSTOM_REGIME'
        assert row2[2] == '1d'
        assert abs(row2[3] - 0.9) < 1e-5
        assert abs(row2[4] - 0.05) < 1e-5
        assert abs(row2[5] - 0.05) < 1e-5
        assert abs(row2[6] - 0.85) < 1e-5

        # Case D: Row 3 (XRPUSDT with invalid signal_id) should not crash/fail. Values should remain NULL.
        cursor.execute("SELECT confidence, regime, timeframe, prob_short, prob_neutral, prob_long, execution_edge FROM paper_positions WHERE id = 3")
        row3 = cursor.fetchone()
        assert row3[0] is None
        assert row3[1] is None
        assert row3[2] is None

        # Mixed: Row 4 (SOLUSDT) confidence, prob_short pre-populated (should remain 50 and 0.2), rest backfilled from signal 103
        # Signal 103: confidence=80, regime='BEAR_TREND', timeframe='15m', prob_short=0.05, prob_neutral=0.15, prob_long=0.80
        cursor.execute("SELECT confidence, regime, timeframe, prob_short, prob_neutral, prob_long, execution_edge FROM paper_positions WHERE id = 4")
        row4 = cursor.fetchone()
        assert row4[0] == 50  # Unchanged
        assert row4[1] == 'BEAR_TREND'  # Backfilled
        assert row4[2] == '15m'  # Backfilled
        assert abs(row4[3] - 0.2) < 1e-5  # Unchanged
        assert abs(row4[4] - 0.15) < 1e-5  # Backfilled
        assert abs(row4[5] - 0.80) < 1e-5  # Backfilled
        # Execution edge computed from signal 103: 0.80 - 0.15 = 0.65
        assert abs(row4[6] - 0.65) < 1e-5  # Backfilled

    # 2. Case C: Apply Migration 027 a second time and verify database state is identical
    with migration_027_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM schema_migrations WHERE migration_name = '027_backfill_execution_metadata.sql'")
        conn.commit()

    with patch('ml_service.migrations.run_migration.get_database', return_value=migration_027_db):
        success = apply_migration(migration_file)
    assert success is True

    # Verify identical database state
    with migration_027_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT confidence, regime, timeframe, prob_short, prob_neutral, prob_long, execution_edge FROM paper_positions WHERE id = 1")
        row1_v2 = cursor.fetchone()
        assert row1_v2 == row1

        cursor.execute("SELECT confidence, regime, timeframe, prob_short, prob_neutral, prob_long, execution_edge FROM paper_positions WHERE id = 2")
        row2_v2 = cursor.fetchone()
        assert row2_v2 == row2

        cursor.execute("SELECT confidence, regime, timeframe, prob_short, prob_neutral, prob_long, execution_edge FROM paper_positions WHERE id = 3")
        row3_v2 = cursor.fetchone()
        assert row3_v2 == row3

        cursor.execute("SELECT confidence, regime, timeframe, prob_short, prob_neutral, prob_long, execution_edge FROM paper_positions WHERE id = 4")
        row4_v2 = cursor.fetchone()
        assert row4_v2 == row4
