"""Integration tests for Snapshot persistence through SnapshotService."""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from ml_service.research.snapshot_engine.service import SnapshotService
from ml_service.research.snapshot_engine.types import Snapshot


def test_service_persists_snapshot_on_create():
    """Test that SnapshotService persists snapshot when create_snapshot is called."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create snapshots table
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE snapshots (
                snapshot_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                snapshot_data TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

        # Mock capture_snapshot to return a test snapshot
        test_snapshot = Snapshot(
            snapshot_id="mock-snapshot-123",
            timestamp="2026-09-13T10:00:00.000000",
            trades=[{"id": 1, "symbol": "BTCUSDT"}],
            signals=[{"id": 1, "direction": "LONG"}],
            account_state={"balance": 10000.0}
        )

        with patch('ml_service.research.snapshot_engine.service.capture_snapshot', return_value=test_snapshot):
            service = SnapshotService(db_path=db_path)
            result = service.create_snapshot(symbol="BTCUSDT")

            assert result.snapshot_id == "mock-snapshot-123"

            # Verify persistence
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT snapshot_id FROM snapshots WHERE snapshot_id = ?", ("mock-snapshot-123",))
            row = cursor.fetchone()
            conn.close()

            assert row is not None
            assert row["snapshot_id"] == "mock-snapshot-123"

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_service_retrieves_persisted_snapshot():
    """Test that SnapshotService.get_snapshot retrieves persisted snapshot."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create snapshots table
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE snapshots (
                snapshot_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                snapshot_data TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

        # Create and persist a snapshot using mocked capture
        test_snapshot = Snapshot(
            snapshot_id="mock-snapshot-456",
            timestamp="2026-09-13T11:00:00.000000",
            trades=[{"id": 2}],
            signals=[{"id": 2}]
        )

        with patch('ml_service.research.snapshot_engine.service.capture_snapshot', return_value=test_snapshot):
            service = SnapshotService(db_path=db_path)
            service.create_snapshot(symbol="ETHUSDT")

        # Retrieve using get_snapshot
        service2 = SnapshotService(db_path=db_path)
        retrieved = service2.get_snapshot("mock-snapshot-456")

        assert retrieved is not None
        assert retrieved.snapshot_id == "mock-snapshot-456"
        assert retrieved.timestamp == "2026-09-13T11:00:00.000000"

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_service_get_returns_none_for_missing_snapshot():
    """Test that get_snapshot returns None for non-existent snapshot."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create empty snapshots table
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE snapshots (
                snapshot_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                snapshot_data TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

        # Try to retrieve non-existent snapshot
        service = SnapshotService(db_path=db_path)
        result = service.get_snapshot("non-existent-id")

        assert result is None

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_complete_create_persist_retrieve_cycle():
    """Test complete cycle: create→persist→new_service→retrieve."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create snapshots table
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE snapshots (
                snapshot_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                snapshot_data TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

        # Create snapshot with all fields populated
        test_snapshot = Snapshot(
            snapshot_id="complete-test-789",
            timestamp="2026-09-13T12:00:00.000000",
            trades=[{"id": 3, "symbol": "BTCUSDT", "pnl": 100.0}],
            signals=[{"id": 3, "direction": "LONG"}],
            account_state={"balance": 10000.0, "equity": 10100.0},
            signal_state={"total_signals": 5},
            regime_state={"regime": "TRENDING"}
        )

        with patch('ml_service.research.snapshot_engine.service.capture_snapshot', return_value=test_snapshot):
            service1 = SnapshotService(db_path=db_path)
            created = service1.create_snapshot(symbol="BTCUSDT")

        # New service instance - simulates process restart
        service2 = SnapshotService(db_path=db_path)
        loaded = service2.get_snapshot(created.snapshot_id)

        # Verify complete round-trip
        assert loaded is not None
        assert loaded.snapshot_id == created.snapshot_id
        assert loaded.timestamp == created.timestamp
        assert loaded.trades == created.trades
        assert loaded.signals == created.signals
        assert loaded.account_state == created.account_state
        assert loaded.signal_state == created.signal_state
        assert loaded.regime_state == created.regime_state

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_replay_service_can_retrieve_snapshot():
    """Test that ReplayService can retrieve snapshots via SnapshotService."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create snapshots table
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE snapshots (
                snapshot_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                snapshot_data TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

        # Create snapshot
        test_snapshot = Snapshot(
            snapshot_id="replay-test-001",
            timestamp="2026-09-13T13:00:00.000000",
            trades=[],
            signals=[]
        )

        with patch('ml_service.research.snapshot_engine.service.capture_snapshot', return_value=test_snapshot):
            snapshot_service = SnapshotService(db_path=db_path)
            snapshot_service.create_snapshot(symbol="BTCUSDT")

        # Import and verify ReplayService can retrieve
        from ml_service.research.replay_engine.service import ReplayService

        replay_service = ReplayService(db_path=db_path)
        retrieved = replay_service.snapshot_service.get_snapshot("replay-test-001")

        assert retrieved is not None
        assert retrieved.snapshot_id == "replay-test-001"

    finally:
        Path(db_path).unlink(missing_ok=True)


if __name__ == "__main__":
    test_service_persists_snapshot_on_create()
    test_service_retrieves_persisted_snapshot()
    test_service_get_returns_none_for_missing_snapshot()
    test_complete_create_persist_retrieve_cycle()
    test_replay_service_can_retrieve_snapshot()
    print("✓ All Snapshot service integration tests passed")
