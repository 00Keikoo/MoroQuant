"""Unit tests for SignalRepository."""

import sqlite3
import tempfile
from pathlib import Path
import pytest

from ml_service.repositories.signal_repository import SignalRepository, Signal


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            direction TEXT NOT NULL CHECK(direction IN ('long', 'short', 'neutral')),
            confidence INTEGER NOT NULL CHECK(confidence >= 0 AND confidence <= 100),
            features_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("CREATE INDEX idx_signals_symbol_timeframe ON signals(symbol, timeframe, timestamp DESC)")

    conn.commit()
    conn.close()

    yield db_path

    Path(db_path).unlink()


@pytest.fixture
def repository(temp_db):
    """Create a SignalRepository instance with temporary database."""
    return SignalRepository(db_path=temp_db)


@pytest.fixture
def sample_signals(temp_db):
    """Insert sample signals into the database."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    signals = [
        ('BTCUSDT', '4h', 1719820800, 'long', 85, '{"feature1": 0.5}', '2026-07-01 10:00:00'),
        ('ETHUSDT', '1h', 1719824400, 'short', 90, '{"feature1": 0.8}', '2026-07-01 11:00:00'),
        ('BTCUSDT', '4h', 1719828000, 'long', 75, '{"feature1": 0.6}', '2026-07-01 12:00:00'),
        ('ADAUSDT', '1h', 1719831600, 'neutral', 60, '{"feature1": 0.4}', '2026-07-01 13:00:00'),
        ('BTCUSDT', '1h', 1719835200, 'short', 80, '{"feature1": 0.7}', '2026-07-01 14:00:00'),
    ]

    for sig in signals:
        cursor.execute("""
            INSERT INTO signals (symbol, timeframe, timestamp, direction, confidence, features_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, sig)

    conn.commit()
    conn.close()


def test_find_by_id(repository, sample_signals):
    """Test finding a signal by ID."""
    signal = repository.find_by_id(1)

    assert signal is not None
    assert signal.id == 1
    assert signal.symbol == 'BTCUSDT'
    assert signal.timeframe == '4h'
    assert signal.direction == 'long'
    assert signal.confidence == 85


def test_find_by_id_not_found(repository, sample_signals):
    """Test finding a non-existent signal."""
    signal = repository.find_by_id(999)
    assert signal is None


def test_find_by_symbol_and_timeframe(repository, sample_signals):
    """Test finding signals by symbol and timeframe."""
    signals = repository.find_by_symbol_and_timeframe('BTCUSDT', '4h')

    assert len(signals) == 2
    assert all(s.symbol == 'BTCUSDT' and s.timeframe == '4h' for s in signals)
    assert signals[0].timestamp > signals[1].timestamp


def test_find_by_symbol_and_timeframe_limit(repository, sample_signals):
    """Test limiting results."""
    signals = repository.find_by_symbol_and_timeframe('BTCUSDT', '4h', limit=1)

    assert len(signals) == 1


def test_find_recent(repository, sample_signals):
    """Test finding recent signals."""
    signals = repository.find_recent(limit=3)

    assert len(signals) == 3
    assert signals[0].timestamp > signals[1].timestamp > signals[2].timestamp


def test_find_recent_with_symbol_filter(repository, sample_signals):
    """Test finding recent signals filtered by symbol."""
    signals = repository.find_recent(symbol='BTCUSDT')

    assert len(signals) == 3
    assert all(s.symbol == 'BTCUSDT' for s in signals)


def test_find_recent_with_direction_filter(repository, sample_signals):
    """Test finding recent signals filtered by direction."""
    signals = repository.find_recent(direction='long')

    assert len(signals) == 2
    assert all(s.direction == 'long' for s in signals)


def test_find_recent_with_min_confidence(repository, sample_signals):
    """Test finding recent signals with minimum confidence."""
    signals = repository.find_recent(min_confidence=80)

    assert len(signals) == 3
    assert all(s.confidence >= 80 for s in signals)


def test_find_recent_with_multiple_filters(repository, sample_signals):
    """Test combining multiple filters."""
    signals = repository.find_recent(symbol='BTCUSDT', direction='long', min_confidence=80)

    assert len(signals) == 1
    assert signals[0].symbol == 'BTCUSDT'
    assert signals[0].direction == 'long'
    assert signals[0].confidence >= 80


def test_count_by_symbol(repository, sample_signals):
    """Test counting signals by symbol."""
    btc_count = repository.count_by_symbol('BTCUSDT')
    assert btc_count == 3

    eth_count = repository.count_by_symbol('ETHUSDT')
    assert eth_count == 1

    unknown_count = repository.count_by_symbol('XRPUSDT')
    assert unknown_count == 0


def test_empty_result(repository):
    """Test querying an empty database."""
    signals = repository.find_recent()
    assert len(signals) == 0

    assert repository.count_by_symbol('BTCUSDT') == 0


def test_signal_attributes(repository, sample_signals):
    """Test that all signal attributes are correctly mapped."""
    signal = repository.find_by_id(2)

    assert signal.id == 2
    assert signal.symbol == 'ETHUSDT'
    assert signal.timeframe == '1h'
    assert signal.timestamp == 1719824400
    assert signal.direction == 'short'
    assert signal.confidence == 90
    assert signal.features_json == '{"feature1": 0.8}'
    assert signal.created_at == '2026-07-01 11:00:00'


def test_sql_injection_protection(repository, sample_signals):
    """Test that parameterized queries prevent SQL injection."""
    signals = repository.find_recent(symbol="'; DROP TABLE signals; --")
    assert len(signals) == 0
