"""Unit tests for TradeRepository."""

import sqlite3
import tempfile
from pathlib import Path
import pytest

from ml_service.repositories.trade_repository import TradeRepository, TradePosition


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE paper_positions (
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
            execution_policy TEXT DEFAULT 'FIXED_SL'
        )
    """)

    cursor.execute("CREATE INDEX idx_paper_positions_status ON paper_positions(status)")
    cursor.execute("CREATE INDEX idx_paper_positions_symbol ON paper_positions(symbol)")

    conn.commit()
    conn.close()

    yield db_path

    Path(db_path).unlink()


@pytest.fixture
def repository(temp_db):
    """Create a TradeRepository instance with temporary database."""
    return TradeRepository(db_path=temp_db)


@pytest.fixture
def sample_positions(temp_db):
    """Insert sample positions into the database."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    positions = [
        ('BTCUSDT', 'LONG', 45000.0, 46000.0, 1000.0, 0.022, 44000.0, 47000.0, 1, 'OPEN', 0.0, '2026-07-01 10:00:00', None, 85, 'BULL', '4h', 0.1, 0.2, 0.7, 0.05, None, 100.0, 500.0, None, None, None, None, 0, 0, 0, 'FIXED_SL'),
        ('ETHUSDT', 'SHORT', 3000.0, 2950.0, 500.0, 0.167, 3100.0, 2900.0, 2, 'TP_HIT', 50.0, '2026-07-01 11:00:00', '2026-07-01 15:00:00', 90, 'BEAR', '1h', 0.8, 0.15, 0.05, 0.08, None, 50.0, 150.0, '2026-07-01 13:00:00', '2026-07-01 14:00:00', 0.95, 'TP_HIT', 0, 0, 0, 'TRAILING'),
        ('BTCUSDT', 'LONG', 44500.0, 43000.0, 1000.0, 0.022, 43500.0, 46000.0, 3, 'SL_HIT', -100.0, '2026-07-02 09:00:00', '2026-07-02 10:00:00', 70, 'BULL', '4h', 0.2, 0.3, 0.5, 0.03, None, 200.0, 50.0, '2026-07-02 09:30:00', '2026-07-02 09:15:00', 0.1, 'SL_HIT', 0, 1, 0, 'BREAK_EVEN'),
        ('ADAUSDT', 'SHORT', 0.5, 0.48, 200.0, 400.0, 0.52, 0.47, 4, 'OPEN', 0.0, '2026-07-03 08:00:00', None, 75, 'NEUTRAL', '1h', 0.4, 0.4, 0.2, 0.02, None, 10.0, 20.0, None, None, None, None, 0, 0, 0, 'FIXED_SL'),
    ]

    for pos in positions:
        cursor.execute("""
            INSERT INTO paper_positions (
                symbol, direction, entry_price, current_price, size_usdt, qty,
                stop_loss, take_profit, signal_id, status, realized_pnl,
                opened_at, closed_at, confidence, regime, timeframe,
                prob_short, prob_neutral, prob_long, execution_edge, skip_reason,
                mae, mfe, mae_timestamp, mfe_timestamp, profit_capture_ratio,
                final_exit_reason, trailing_stop_activated, sl_move_count,
                break_even_triggered, execution_policy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, pos)

    conn.commit()
    conn.close()


def test_find_all_no_filters(repository, sample_positions):
    """Test finding all positions without filters."""
    positions = repository.find_all()

    assert len(positions) == 4
    assert all(isinstance(p, TradePosition) for p in positions)


def test_find_all_with_status_filter(repository, sample_positions):
    """Test filtering by status."""
    open_positions = repository.find_all(status='OPEN')

    assert len(open_positions) == 2
    assert all(p.status == 'OPEN' for p in open_positions)

    closed_positions = repository.find_all(status='TP_HIT')
    assert len(closed_positions) == 1
    assert closed_positions[0].symbol == 'ETHUSDT'


def test_find_all_with_symbol_filter(repository, sample_positions):
    """Test filtering by symbol."""
    btc_positions = repository.find_all(symbol='BTCUSDT')

    assert len(btc_positions) == 2
    assert all(p.symbol == 'BTCUSDT' for p in btc_positions)


def test_find_all_with_direction_filter(repository, sample_positions):
    """Test filtering by direction."""
    long_positions = repository.find_all(direction='LONG')

    assert len(long_positions) == 2
    assert all(p.direction == 'LONG' for p in long_positions)

    short_positions = repository.find_all(direction='SHORT')
    assert len(short_positions) == 2


def test_find_all_with_multiple_filters(repository, sample_positions):
    """Test combining multiple filters."""
    positions = repository.find_all(status='OPEN', symbol='BTCUSDT')

    assert len(positions) == 1
    assert positions[0].symbol == 'BTCUSDT'
    assert positions[0].status == 'OPEN'


def test_find_all_pagination(repository, sample_positions):
    """Test pagination with limit and offset."""
    page1 = repository.find_all(limit=2, offset=0)
    page2 = repository.find_all(limit=2, offset=2)

    assert len(page1) == 2
    assert len(page2) == 2
    assert page1[0].id != page2[0].id


def test_find_all_sorting(repository, sample_positions):
    """Test sorting by different columns."""
    by_id_asc = repository.find_all(sort_by='id', sort_order='ASC')
    assert by_id_asc[0].id < by_id_asc[-1].id

    by_id_desc = repository.find_all(sort_by='id', sort_order='DESC')
    assert by_id_desc[0].id > by_id_desc[-1].id

    by_pnl = repository.find_all(sort_by='realized_pnl', sort_order='DESC')
    assert by_pnl[0].realized_pnl >= by_pnl[-1].realized_pnl


def test_find_by_id(repository, sample_positions):
    """Test finding a position by ID."""
    position = repository.find_by_id(1)

    assert position is not None
    assert position.id == 1
    assert position.symbol == 'BTCUSDT'
    assert position.direction == 'LONG'


def test_find_by_id_not_found(repository, sample_positions):
    """Test finding a non-existent position."""
    position = repository.find_by_id(999)
    assert position is None


def test_find_by_signal_id(repository, sample_positions):
    """Test finding positions by signal ID."""
    positions = repository.find_by_signal_id(1)

    assert len(positions) == 1
    assert positions[0].signal_id == 1


def test_count_all(repository, sample_positions):
    """Test counting all positions."""
    total = repository.count()
    assert total == 4


def test_count_with_filters(repository, sample_positions):
    """Test counting with filters."""
    open_count = repository.count(status='OPEN')
    assert open_count == 2

    btc_count = repository.count(symbol='BTCUSDT')
    assert btc_count == 2

    long_btc_count = repository.count(symbol='BTCUSDT', direction='LONG')
    assert long_btc_count == 2


def test_empty_result(repository):
    """Test querying an empty database."""
    positions = repository.find_all()
    assert len(positions) == 0

    assert repository.count() == 0


def test_sql_injection_protection(repository, sample_positions):
    """Test that parameterized queries prevent SQL injection."""
    positions = repository.find_all(symbol="'; DROP TABLE paper_positions; --")
    assert len(positions) == 0


def test_invalid_sort_column(repository, sample_positions):
    """Test that invalid sort columns are rejected."""
    positions = repository.find_all(sort_by='invalid_column')
    assert len(positions) == 4


def test_position_attributes(repository, sample_positions):
    """Test that all position attributes are correctly mapped."""
    position = repository.find_by_id(2)

    assert position.symbol == 'ETHUSDT'
    assert position.direction == 'SHORT'
    assert position.entry_price == 3000.0
    assert position.current_price == 2950.0
    assert position.size_usdt == 500.0
    assert position.qty == 0.167
    assert position.stop_loss == 3100.0
    assert position.take_profit == 2900.0
    assert position.signal_id == 2
    assert position.status == 'TP_HIT'
    assert position.realized_pnl == 50.0
    assert position.confidence == 90
    assert position.regime == 'BEAR'
    assert position.timeframe == '1h'
    assert position.execution_policy == 'TRAILING'
