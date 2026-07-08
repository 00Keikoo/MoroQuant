"""Unit tests for EquityRepository."""

import sqlite3
import tempfile
from pathlib import Path
import pytest

from ml_service.repositories.equity_repository import (
    EquityRepository,
    PaperAccount,
    EquitySnapshot
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE paper_account (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            balance REAL NOT NULL DEFAULT 10000.0,
            equity REAL NOT NULL DEFAULT 10000.0,
            unrealized_pnl REAL NOT NULL DEFAULT 0.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE paper_equity_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equity REAL NOT NULL,
            balance REAL NOT NULL,
            unrealized_pnl REAL NOT NULL,
            snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("CREATE INDEX idx_paper_equity_snapshot_time ON paper_equity_history(snapshot_time)")

    conn.commit()
    conn.close()

    yield db_path

    Path(db_path).unlink()


@pytest.fixture
def repository(temp_db):
    """Create an EquityRepository instance with temporary database."""
    return EquityRepository(db_path=temp_db)


@pytest.fixture
def sample_account(temp_db):
    """Insert sample account data."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO paper_account (id, balance, equity, unrealized_pnl, updated_at)
        VALUES (1, 10500.0, 11200.0, 700.0, '2026-07-06 14:00:00')
    """)

    conn.commit()
    conn.close()


@pytest.fixture
def sample_equity_history(temp_db):
    """Insert sample equity history data."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    snapshots = [
        (10000.0, 10000.0, 0.0, '2026-07-01 00:00:00'),
        (10100.0, 10200.0, 100.0, '2026-07-01 05:00:00'),
        (10200.0, 10500.0, 300.0, '2026-07-01 10:00:00'),
        (10300.0, 10800.0, 500.0, '2026-07-01 15:00:00'),
        (10400.0, 11000.0, 600.0, '2026-07-01 20:00:00'),
        (10500.0, 11200.0, 700.0, '2026-07-02 00:00:00'),
    ]

    for snap in snapshots:
        cursor.execute("""
            INSERT INTO paper_equity_history (equity, balance, unrealized_pnl, snapshot_time)
            VALUES (?, ?, ?, ?)
        """, snap)

    conn.commit()
    conn.close()


def test_get_account(repository, sample_account):
    """Test getting the paper account singleton."""
    account = repository.get_account()

    assert account is not None
    assert isinstance(account, PaperAccount)
    assert account.id == 1
    assert account.balance == 10500.0
    assert account.equity == 11200.0
    assert account.unrealized_pnl == 700.0


def test_get_account_empty(repository):
    """Test getting account when it doesn't exist."""
    account = repository.get_account()
    assert account is None


def test_get_equity_history(repository, sample_equity_history):
    """Test getting equity history."""
    snapshots = repository.get_equity_history(limit=10)

    assert len(snapshots) == 6
    assert all(isinstance(s, EquitySnapshot) for s in snapshots)
    assert snapshots[0].snapshot_time > snapshots[-1].snapshot_time


def test_get_equity_history_pagination(repository, sample_equity_history):
    """Test pagination of equity history."""
    page1 = repository.get_equity_history(limit=3, offset=0)
    page2 = repository.get_equity_history(limit=3, offset=3)

    assert len(page1) == 3
    assert len(page2) == 3
    assert page1[0].id != page2[0].id


def test_get_equity_history_range(repository, sample_equity_history):
    """Test getting equity history within a time range."""
    snapshots = repository.get_equity_history_range(
        '2026-07-01 06:00:00',
        '2026-07-01 18:00:00'
    )

    assert len(snapshots) == 2
    assert snapshots[0].snapshot_time >= '2026-07-01 06:00:00'
    assert snapshots[-1].snapshot_time <= '2026-07-01 18:00:00'


def test_get_latest_snapshot(repository, sample_equity_history):
    """Test getting the most recent snapshot."""
    snapshot = repository.get_latest_snapshot()

    assert snapshot is not None
    assert snapshot.equity == 10500.0
    assert snapshot.balance == 11200.0
    assert snapshot.unrealized_pnl == 700.0
    assert snapshot.snapshot_time == '2026-07-02 00:00:00'


def test_get_latest_snapshot_empty(repository):
    """Test getting latest snapshot when none exist."""
    snapshot = repository.get_latest_snapshot()
    assert snapshot is None


def test_count_snapshots(repository, sample_equity_history):
    """Test counting equity snapshots."""
    count = repository.count_snapshots()
    assert count == 6


def test_count_snapshots_empty(repository):
    """Test counting snapshots in empty database."""
    count = repository.count_snapshots()
    assert count == 0


def test_account_attributes(repository, sample_account):
    """Test that all account attributes are correctly mapped."""
    account = repository.get_account()

    assert account.id == 1
    assert account.balance == 10500.0
    assert account.equity == 11200.0
    assert account.unrealized_pnl == 700.0
    assert account.updated_at == '2026-07-06 14:00:00'


def test_snapshot_attributes(repository, sample_equity_history):
    """Test that all snapshot attributes are correctly mapped."""
    snapshot = repository.get_latest_snapshot()

    assert snapshot.id == 6
    assert snapshot.equity == 10500.0
    assert snapshot.balance == 11200.0
    assert snapshot.unrealized_pnl == 700.0
    assert snapshot.snapshot_time == '2026-07-02 00:00:00'
