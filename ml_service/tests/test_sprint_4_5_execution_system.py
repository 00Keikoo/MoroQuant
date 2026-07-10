"""Sprint 4.5 Execution System Blocker Fixes Verification.

Tests that validate:
1. Scheduler provides current market price to signal lifecycle
2. TP_HIT and SL_HIT transitions work correctly
3. Exit events (TP/SL/EXPIRED/MANUAL_CLOSE) are logged to execution_decisions
"""

import sqlite3
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from pathlib import Path

from ml_service.signal_lifecycle import bulk_update_signal_statuses
from ml_service.trading import paper_broker


@pytest.fixture
def test_db(tmp_path):
    """Create temporary test database with all required tables."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    conn.execute("""
        CREATE TABLE paper_positions (
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
            profit_capture_ratio REAL,
            final_exit_reason TEXT,
            execution_policy TEXT DEFAULT 'FIXED_SL',
            signal_price REAL,
            execution_price REAL,
            slippage_pct REAL
        )
    """)

    conn.execute("""
        CREATE TABLE paper_account (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            balance REAL NOT NULL DEFAULT 10000.0,
            equity REAL NOT NULL DEFAULT 10000.0,
            unrealized_pnl REAL NOT NULL DEFAULT 0.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE execution_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            direction TEXT,
            decision TEXT NOT NULL,
            reason TEXT,
            signal_id INTEGER,
            position_id INTEGER,
            confidence INTEGER,
            regime TEXT,
            timeframe TEXT,
            prob_short REAL,
            prob_neutral REAL,
            prob_long REAL,
            execution_edge REAL,
            signal_price REAL,
            execution_price REAL,
            slippage_pct REAL,
            execution_latency_ms INTEGER,
            source TEXT NOT NULL DEFAULT 'PAPER',
            signal_timestamp INTEGER,
            execution_policy TEXT,
            reason_detail TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            direction TEXT NOT NULL,
            signal_status TEXT NOT NULL DEFAULT 'ACTIVE',
            take_profit REAL,
            stop_loss REAL,
            valid_until TEXT,
            status_updated_at TIMESTAMP
        )
    """)

    conn.execute("INSERT INTO paper_account (id, balance, equity) VALUES (1, 10000.0, 10000.0)")
    conn.commit()
    conn.close()

    return db_path


def test_signal_lifecycle_tp_hit_long(test_db):
    """Verify LONG signal transitions to TP_HIT when price >= take_profit."""
    conn = sqlite3.connect(str(test_db))
    conn.row_factory = sqlite3.Row

    valid_until = (datetime.now() + timedelta(hours=24)).isoformat()
    conn.execute("""
        INSERT INTO signals (symbol, timeframe, direction, signal_status, take_profit, stop_loss, valid_until)
        VALUES ('BTCUSDT', '1h', 'long', 'ACTIVE', 50000.0, 48000.0, ?)
    """, (valid_until,))
    conn.commit()
    signal_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    signal = {
        'signal_id': signal_id,
        'symbol': 'BTCUSDT',
        'timeframe': '1h',
        'direction': 'long',
        'signal_status': 'ACTIVE',
        'take_profit': 50000.0,
        'stop_loss': 48000.0,
        'valid_until': valid_until,
    }

    items = [{'signal': signal, 'current_price': 50100.0}]

    with patch('ml_service.signal_lifecycle.get_database') as mock_db:
        mock_db.return_value.get_connection.return_value.__enter__.return_value = conn
        updated = bulk_update_signal_statuses(items)

    assert updated == 1
    row = conn.execute("SELECT signal_status FROM signals WHERE id = ?", (signal_id,)).fetchone()
    assert row['signal_status'] == 'TP_HIT'
    conn.close()


def test_signal_lifecycle_sl_hit_short(test_db):
    """Verify SHORT signal transitions to SL_HIT when price >= stop_loss."""
    conn = sqlite3.connect(str(test_db))
    conn.row_factory = sqlite3.Row

    valid_until = (datetime.now() + timedelta(hours=24)).isoformat()
    conn.execute("""
        INSERT INTO signals (symbol, timeframe, direction, signal_status, take_profit, stop_loss, valid_until)
        VALUES ('BTCUSDT', '1h', 'short', 'ACTIVE', 48000.0, 52000.0, ?)
    """, (valid_until,))
    conn.commit()
    signal_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    signal = {
        'signal_id': signal_id,
        'symbol': 'BTCUSDT',
        'timeframe': '1h',
        'direction': 'short',
        'signal_status': 'ACTIVE',
        'take_profit': 48000.0,
        'stop_loss': 52000.0,
        'valid_until': valid_until,
    }

    items = [{'signal': signal, 'current_price': 52100.0}]

    with patch('ml_service.signal_lifecycle.get_database') as mock_db:
        mock_db.return_value.get_connection.return_value.__enter__.return_value = conn
        updated = bulk_update_signal_statuses(items)

    assert updated == 1
    row = conn.execute("SELECT signal_status FROM signals WHERE id = ?", (signal_id,)).fetchone()
    assert row['signal_status'] == 'SL_HIT'
    conn.close()


def test_exit_event_tp_hit_logged(test_db):
    """Verify TP_HIT exit event is logged to execution_decisions."""
    with patch('ml_service.trading.paper_broker._DB_PATH', test_db), \
         patch('ml_service.trading.execution_audit._DB_PATH', test_db):
        conn = sqlite3.connect(str(test_db))
        conn.row_factory = sqlite3.Row

        conn.execute("""
            INSERT INTO paper_positions
                (symbol, direction, entry_price, current_price, size_usdt, qty,
                 stop_loss, take_profit, signal_id, status, confidence, regime, timeframe)
            VALUES ('BTCUSDT', 'LONG', 49000.0, 50000.0, 100.0, 0.00204, 48000.0, 51000.0, 1, 'OPEN', 65, 'TRENDING_UP', '1h')
        """)
        conn.commit()
        position_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()

        result = paper_broker.close_paper_position(position_id, status="TP_HIT", close_price=51000.0)

        assert result is not None
        assert result['status'] == 'TP_HIT'

        conn = sqlite3.connect(str(test_db))
        conn.row_factory = sqlite3.Row
        row = conn.execute("""
            SELECT * FROM execution_decisions
            WHERE position_id = ? AND reason = 'TP_HIT'
        """, (position_id,)).fetchone()

        assert row is not None
        assert row['decision'] == 'ACCEPTED'
        assert row['symbol'] == 'BTCUSDT'
        assert row['direction'] == 'LONG'
        assert row['reason'] == 'TP_HIT'
        assert 'exit_reason=TP_HIT' in row['reason_detail']
        conn.close()


def test_exit_event_sl_hit_logged(test_db):
    """Verify SL_HIT exit event is logged to execution_decisions."""
    with patch('ml_service.trading.paper_broker._DB_PATH', test_db), \
         patch('ml_service.trading.execution_audit._DB_PATH', test_db):
        conn = sqlite3.connect(str(test_db))
        conn.row_factory = sqlite3.Row

        conn.execute("""
            INSERT INTO paper_positions
                (symbol, direction, entry_price, current_price, size_usdt, qty,
                 stop_loss, take_profit, signal_id, status, confidence, regime, timeframe)
            VALUES ('ETHUSDT', 'SHORT', 2500.0, 2450.0, 100.0, 0.04, 2550.0, 2400.0, 2, 'OPEN', 70, 'TRENDING_DOWN', '4h')
        """)
        conn.commit()
        position_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()

        result = paper_broker.close_paper_position(position_id, status="SL_HIT", close_price=2550.0)

        assert result is not None
        assert result['status'] == 'SL_HIT'

        conn = sqlite3.connect(str(test_db))
        conn.row_factory = sqlite3.Row
        row = conn.execute("""
            SELECT * FROM execution_decisions
            WHERE position_id = ? AND reason = 'SL_HIT'
        """, (position_id,)).fetchone()

        assert row is not None
        assert row['reason'] == 'SL_HIT'
        assert 'exit_reason=SL_HIT' in row['reason_detail']
        conn.close()


def test_scheduler_fetches_current_price():
    """Verify scheduler's signal_lifecycle_job fetches current price for evaluation."""
    with patch('ml_service.scheduler.get_database') as mock_db, \
         patch('ml_service.signal_lifecycle.bulk_update_signal_statuses') as mock_bulk_update, \
         patch('ml_service.trading.paper_broker._fetch_mark_price') as mock_fetch_price:

        mock_fetch_price.return_value = 49500.0

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        valid_until = (datetime.now() + timedelta(hours=24)).isoformat()
        mock_cursor.fetchall.return_value = [
            (1, 'BTCUSDT', '1h', 'long', 'ACTIVE', 50000.0, 48000.0, valid_until)
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.get_connection.return_value.__enter__.return_value = mock_conn

        from ml_service.scheduler import signal_lifecycle_job
        signal_lifecycle_job()

        mock_fetch_price.assert_called_once_with('BTCUSDT')

        mock_bulk_update.assert_called_once()
        items = mock_bulk_update.call_args[0][0]
        assert len(items) == 1
        assert items[0]['current_price'] == 49500.0
        assert items[0]['signal']['symbol'] == 'BTCUSDT'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
