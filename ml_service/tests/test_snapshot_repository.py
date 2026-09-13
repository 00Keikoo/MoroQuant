"""Unit tests for SnapshotRepository."""

import json
import sqlite3
import tempfile
from pathlib import Path

from ml_service.repositories.snapshot_repository import SnapshotRepository
from ml_service.research.snapshot_engine.types import Snapshot


def test_save_persists_snapshot():
    """Test that save() persists snapshot to database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create table
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

        # Create and save snapshot
        snapshot = Snapshot(
            snapshot_id="test-snap-123",
            timestamp="2026-09-13T10:00:00.000000",
            trades=[{"id": 1, "symbol": "BTCUSDT"}],
            signals=[{"id": 1, "direction": "LONG"}],
            account_state={"balance": 10000.0},
            signal_state={"total_signals": 1}
        )

        repo = SnapshotRepository(db_path=db_path)
        result = repo.save(snapshot)

        assert result.snapshot_id == snapshot.snapshot_id

        # Verify persistence
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM snapshots WHERE snapshot_id = ?", ("test-snap-123",))
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row["snapshot_id"] == "test-snap-123"
        assert row["timestamp"] == "2026-09-13T10:00:00.000000"

        data = json.loads(row["snapshot_data"])
        assert data["snapshot_id"] == "test-snap-123"
        assert len(data["trades"]) == 1
        assert len(data["signals"]) == 1

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_get_retrieves_snapshot():
    """Test that get() retrieves snapshot by ID."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create table and insert snapshot
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE snapshots (
                snapshot_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                snapshot_data TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        snapshot_data = json.dumps({
            "snapshot_id": "test-snap-456",
            "timestamp": "2026-09-13T11:00:00.000000",
            "trades": [{"id": 2, "symbol": "ETHUSDT"}],
            "signals": [{"id": 2, "direction": "SHORT"}],
            "account_state": {"balance": 15000.0},
            "market_state": None,
            "model_state": None,
            "signal_state": {"total_signals": 2},
            "feature_state": None,
            "regime_state": None,
            "risk_state": None,
            "execution_state": None,
            "position_state": None,
            "execution_constraints": None,
            "regime_statistics": None
        })

        conn.execute(
            "INSERT INTO snapshots (snapshot_id, timestamp, snapshot_data, created_at) VALUES (?, ?, ?, ?)",
            ("test-snap-456", "2026-09-13T11:00:00.000000", snapshot_data, "2026-09-13T11:00:00.000000")
        )
        conn.commit()
        conn.close()

        # Retrieve snapshot
        repo = SnapshotRepository(db_path=db_path)
        snapshot = repo.get("test-snap-456")

        assert snapshot is not None
        assert snapshot.snapshot_id == "test-snap-456"
        assert snapshot.timestamp == "2026-09-13T11:00:00.000000"
        assert len(snapshot.trades) == 1
        assert snapshot.trades[0]["symbol"] == "ETHUSDT"
        assert len(snapshot.signals) == 1
        assert snapshot.signals[0]["direction"] == "SHORT"
        assert snapshot.account_state["balance"] == 15000.0
        assert snapshot.signal_state["total_signals"] == 2

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_get_returns_none_for_missing_snapshot():
    """Test that get() returns None for missing snapshot ID."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create empty table
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
        repo = SnapshotRepository(db_path=db_path)
        snapshot = repo.get("non-existent-id")

        assert snapshot is None

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_save_is_idempotent():
    """Test that saving same snapshot twice is idempotent."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create table
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
        snapshot = Snapshot(
            snapshot_id="test-snap-789",
            timestamp="2026-09-13T12:00:00.000000",
            trades=[{"id": 3}],
            signals=[{"id": 3}]
        )

        repo = SnapshotRepository(db_path=db_path)

        # Save twice
        repo.save(snapshot)
        repo.save(snapshot)

        # Verify only one row exists
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM snapshots WHERE snapshot_id = ?", ("test-snap-789",))
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_round_trip_preserves_all_fields():
    """Test that save/get round-trip preserves all snapshot fields."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create table
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

        # Create snapshot with all fields
        original = Snapshot(
            snapshot_id="test-complete",
            timestamp="2026-09-13T13:00:00.000000",
            trades=[{"id": 1, "symbol": "BTCUSDT", "pnl": 100.0}],
            signals=[{"id": 1, "direction": "LONG", "confidence": 0.8}],
            account_state={"balance": 10000.0, "equity": 10100.0},
            market_state={"volatility": 0.05},
            model_state={"version": "v1.0"},
            signal_state={"total_signals": 10, "executed": 5},
            feature_state={"features": ["rsi", "macd"]},
            regime_state={"regime": "TRENDING"},
            risk_state={"exposure": 0.1},
            execution_state={"policy": "AGGRESSIVE"},
            position_state={"open_count": 2},
            execution_constraints={"max_positions": 5},
            regime_statistics={"trending": {"sharpe": 1.5}}
        )

        repo = SnapshotRepository(db_path=db_path)
        repo.save(original)

        # Retrieve and verify
        loaded = repo.get("test-complete")

        assert loaded is not None
        assert loaded.snapshot_id == original.snapshot_id
        assert loaded.timestamp == original.timestamp
        assert loaded.trades == original.trades
        assert loaded.signals == original.signals
        assert loaded.account_state == original.account_state
        assert loaded.market_state == original.market_state
        assert loaded.model_state == original.model_state
        assert loaded.signal_state == original.signal_state
        assert loaded.feature_state == original.feature_state
        assert loaded.regime_state == original.regime_state
        assert loaded.risk_state == original.risk_state
        assert loaded.execution_state == original.execution_state
        assert loaded.position_state == original.position_state
        assert loaded.execution_constraints == original.execution_constraints
        assert loaded.regime_statistics == original.regime_statistics

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_persistence_survives_connection_close():
    """Test that persisted snapshot survives closing and reopening connection."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create table
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

        # Save snapshot
        snapshot = Snapshot(
            snapshot_id="test-persistence",
            timestamp="2026-09-13T14:00:00.000000",
            trades=[],
            signals=[]
        )

        repo1 = SnapshotRepository(db_path=db_path)
        repo1.save(snapshot)

        # Create new repository instance (simulates closing/reopening)
        repo2 = SnapshotRepository(db_path=db_path)
        loaded = repo2.get("test-persistence")

        assert loaded is not None
        assert loaded.snapshot_id == "test-persistence"

    finally:
        Path(db_path).unlink(missing_ok=True)


if __name__ == "__main__":
    test_save_persists_snapshot()
    test_get_retrieves_snapshot()
    test_get_returns_none_for_missing_snapshot()
    test_save_is_idempotent()
    test_round_trip_preserves_all_fields()
    test_persistence_survives_connection_close()
    print("✓ All SnapshotRepository tests passed")
