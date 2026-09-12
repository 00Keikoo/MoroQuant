"""Tests for system status endpoint."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

from ml_service.api.main import app

client = TestClient(app)


def test_system_status_endpoint_exists():
    """Test that /api/system/status endpoint exists and returns 200."""
    response = client.get("/api/system/status")
    assert response.status_code == 200


def test_system_status_response_shape():
    """Test that response matches frontend SystemStatusResponse type."""
    response = client.get("/api/system/status")
    data = response.json()

    # Required fields from lib/types/system-status.ts
    assert "api" in data
    assert "db" in data
    assert "scheduler" in data
    assert "paper_broker" in data
    assert "market_data" in data
    assert "binance_ws" in data
    assert "timestamp" in data

    # Optional fields
    assert "latency_ms" in data

    # Validate status values are from allowed set
    valid_statuses = {"RUNNING", "STOPPED", "CONNECTED", "DISCONNECTED", "HEALTHY", "DOWN", "UNKNOWN"}
    assert data["api"] in valid_statuses
    assert data["db"] in valid_statuses
    assert data["scheduler"] in valid_statuses
    assert data["paper_broker"] in valid_statuses
    assert data["market_data"] in valid_statuses
    assert data["binance_ws"] in valid_statuses


def test_api_status_always_running():
    """Test that API status is RUNNING when endpoint executes."""
    response = client.get("/api/system/status")
    data = response.json()
    assert data["api"] == "RUNNING"


def test_scheduler_status_uses_get_scheduler_status():
    """Test that scheduler status comes from get_scheduler_status()."""
    with patch("ml_service.scheduler.get_scheduler_status") as mock_sched:
        # Test running state
        mock_sched.return_value = {"running": True}
        response = client.get("/api/system/status")
        data = response.json()
        assert data["scheduler"] == "RUNNING"

        # Test stopped state
        mock_sched.return_value = {"running": False}
        response = client.get("/api/system/status")
        data = response.json()
        assert data["scheduler"] == "STOPPED"

        # Test exception handling
        mock_sched.side_effect = Exception("Scheduler error")
        response = client.get("/api/system/status")
        data = response.json()
        assert data["scheduler"] == "UNKNOWN"


def test_db_status_reflects_connectivity():
    """Test that DB status reflects actual database connectivity."""
    response = client.get("/api/system/status")
    data = response.json()

    # With working database, should be RUNNING
    assert data["db"] in {"RUNNING", "DOWN"}


def test_db_failure_returns_down():
    """Test that DB failures are reflected as DOWN status."""
    with patch("ml_service.api.routes.get_database") as mock_db:
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(side_effect=Exception("DB connection failed"))
        mock_conn.__exit__ = MagicMock()
        mock_db.return_value.get_connection.return_value = mock_conn

        response = client.get("/api/system/status")
        data = response.json()
        assert data["db"] == "DOWN"


def test_market_data_with_fresh_ohlcv():
    """Test that market data status is RUNNING with fresh BTCUSDT 1h timestamp."""
    with patch("ml_service.data.ingestion.get_last_timestamp") as mock_get_ts:
        # Fresh timestamp (30 seconds ago) in milliseconds
        now_ms = datetime.now().timestamp() * 1000
        fresh_ts = now_ms - (30 * 1000)  # 30 seconds ago
        mock_get_ts.return_value = int(fresh_ts)

        response = client.get("/api/system/status")
        data = response.json()
        assert data["market_data"] == "RUNNING"


def test_market_data_with_stale_ohlcv():
    """Test that market data with stale OHLCV (>2h) returns UNKNOWN."""
    with patch("ml_service.data.ingestion.get_last_timestamp") as mock_get_ts:
        # Stale timestamp (3 hours ago) in milliseconds
        now_ms = datetime.now().timestamp() * 1000
        stale_ts = now_ms - (3 * 3600 * 1000)  # 3 hours ago
        mock_get_ts.return_value = int(stale_ts)

        response = client.get("/api/system/status")
        data = response.json()
        assert data["market_data"] == "UNKNOWN"


def test_market_data_with_no_evidence():
    """Test that market data with missing timestamp returns UNKNOWN."""
    with patch("ml_service.data.ingestion.get_last_timestamp") as mock_get_ts:
        # No timestamp data
        mock_get_ts.return_value = None

        response = client.get("/api/system/status")
        data = response.json()
        assert data["market_data"] == "UNKNOWN"


def test_market_data_at_threshold():
    """Test that market data exactly at 2h threshold returns UNKNOWN."""
    with patch("ml_service.data.ingestion.get_last_timestamp") as mock_get_ts:
        # Exactly 2 hours old (7200 seconds) in milliseconds
        now_ms = datetime.now().timestamp() * 1000
        threshold_ts = now_ms - (7200 * 1000)
        mock_get_ts.return_value = int(threshold_ts)

        response = client.get("/api/system/status")
        data = response.json()
        # At exact threshold, should be UNKNOWN (age > threshold)
        assert data["market_data"] == "UNKNOWN"


def test_market_data_exception_handling():
    """Test that market data check exceptions return UNKNOWN."""
    with patch("ml_service.data.ingestion.get_last_timestamp") as mock_get_ts:
        mock_get_ts.side_effect = Exception("Database error")

        response = client.get("/api/system/status")
        data = response.json()
        assert data["market_data"] == "UNKNOWN"


def test_binance_ws_remains_unknown():
    """Test that Binance WebSocket status is UNKNOWN (no production implementation)."""
    response = client.get("/api/system/status")
    data = response.json()
    assert data["binance_ws"] == "UNKNOWN"


def test_paper_broker_with_recent_activity():
    """Test that paper broker is RUNNING only with recent updated_at."""
    with patch("ml_service.trading.paper_broker.get_account") as mock_account, \
         patch("ml_service.trading.mode_manager.get_trading_mode") as mock_mode:

        mock_mode.return_value = "PAPER"

        # Recent activity (within 2 minutes) - use UTC timestamp
        recent_time = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', '')
        mock_account.return_value = {
            "balance": 10000,
            "equity": 10500,
            "updated_at": recent_time
        }
        response = client.get("/api/system/status")
        data = response.json()
        assert data["paper_broker"] == "RUNNING"


def test_paper_broker_with_stale_activity():
    """Test that paper broker with stale updated_at returns UNKNOWN."""
    with patch("ml_service.trading.paper_broker.get_account") as mock_account, \
         patch("ml_service.trading.mode_manager.get_trading_mode") as mock_mode:

        mock_mode.return_value = "PAPER"

        # Stale activity (over 2 minutes old) - use UTC timestamp
        stale_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).replace(microsecond=0).isoformat().replace('+00:00', '')
        mock_account.return_value = {
            "balance": 10000,
            "equity": 10500,
            "updated_at": stale_time
        }
        response = client.get("/api/system/status")
        data = response.json()
        assert data["paper_broker"] == "UNKNOWN"


def test_paper_broker_when_mode_not_paper():
    """Test that paper broker is STOPPED when mode is not PAPER."""
    with patch("ml_service.trading.paper_broker.get_account") as mock_account, \
         patch("ml_service.trading.mode_manager.get_trading_mode") as mock_mode:

        mock_mode.return_value = "OFF"
        mock_account.return_value = {
            "balance": 10000,
            "equity": 10500,
            "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', '')
        }
        response = client.get("/api/system/status")
        data = response.json()
        assert data["paper_broker"] == "STOPPED"


def test_paper_broker_with_exception():
    """Test that paper broker exceptions return UNKNOWN."""
    with patch("ml_service.trading.paper_broker.get_account") as mock_account:
        mock_account.side_effect = Exception("Broker error")
        response = client.get("/api/system/status")
        data = response.json()
        assert data["paper_broker"] == "UNKNOWN"


def test_latency_ms_included():
    """Test that latency_ms is included in response."""
    response = client.get("/api/system/status")
    data = response.json()
    assert isinstance(data["latency_ms"], int)
    assert data["latency_ms"] >= 0


def test_timestamp_format():
    """Test that timestamp is in ISO format."""
    response = client.get("/api/system/status")
    data = response.json()
    assert "timestamp" in data
    # Verify it's a valid ISO timestamp by parsing it
    from datetime import datetime
    try:
        datetime.fromisoformat(data["timestamp"])
    except ValueError:
        pytest.fail("timestamp is not valid ISO format")


def test_component_failure_isolation():
    """Test that one component failure does not crash the entire endpoint."""
    with patch("ml_service.api.routes.get_database") as mock_db, \
         patch("ml_service.scheduler.get_scheduler_status") as mock_sched:

        # Make DB fail
        mock_db_instance = MagicMock()
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(side_effect=Exception("DB connection failed"))
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_db_instance.get_connection.return_value = mock_conn
        mock_db.return_value = mock_db_instance

        # But scheduler should still work
        mock_sched.return_value = {"running": True}

        response = client.get("/api/system/status")

        # Endpoint should still return 200
        assert response.status_code == 200

        data = response.json()
        # DB should be DOWN
        assert data["db"] == "DOWN"
        # But other components should still report
        assert data["api"] == "RUNNING"
        assert data["scheduler"] == "RUNNING"
        assert "market_data" in data
        assert "paper_broker" in data
        assert "binance_ws" in data


def test_paper_broker_timezone_aware_fresh_utc():
    """Test that fresh UTC timestamp produces RUNNING regardless of local timezone."""
    with patch("ml_service.trading.paper_broker.get_account") as mock_account, \
         patch("ml_service.trading.mode_manager.get_trading_mode") as mock_mode:

        mock_mode.return_value = "PAPER"

        # Simulate a UTC timestamp from SQLite CURRENT_TIMESTAMP (30 seconds ago)
        utc_timestamp = (datetime.now(timezone.utc) - timedelta(seconds=30)).strftime('%Y-%m-%d %H:%M:%S')
        mock_account.return_value = {
            "balance": 10000,
            "equity": 10500,
            "updated_at": utc_timestamp
        }
        response = client.get("/api/system/status")
        data = response.json()
        assert data["paper_broker"] == "RUNNING"


def test_paper_broker_timezone_aware_stale_utc():
    """Test that stale UTC timestamp (>120s) produces UNKNOWN."""
    with patch("ml_service.trading.paper_broker.get_account") as mock_account, \
         patch("ml_service.trading.mode_manager.get_trading_mode") as mock_mode:

        mock_mode.return_value = "PAPER"

        # Simulate a UTC timestamp 3 minutes old (stale)
        utc_timestamp = (datetime.now(timezone.utc) - timedelta(seconds=180)).strftime('%Y-%m-%d %H:%M:%S')
        mock_account.return_value = {
            "balance": 10000,
            "equity": 10500,
            "updated_at": utc_timestamp
        }
        response = client.get("/api/system/status")
        data = response.json()
        assert data["paper_broker"] == "UNKNOWN"


def test_paper_broker_missing_account():
    """Test that missing account produces UNKNOWN."""
    with patch("ml_service.trading.paper_broker.get_account") as mock_account, \
         patch("ml_service.trading.mode_manager.get_trading_mode") as mock_mode:

        mock_mode.return_value = "PAPER"
        mock_account.return_value = None

        response = client.get("/api/system/status")
        data = response.json()
        assert data["paper_broker"] == "UNKNOWN"


def test_paper_broker_missing_updated_at():
    """Test that account without updated_at produces UNKNOWN."""
    with patch("ml_service.trading.paper_broker.get_account") as mock_account, \
         patch("ml_service.trading.mode_manager.get_trading_mode") as mock_mode:

        mock_mode.return_value = "PAPER"
        mock_account.return_value = {
            "balance": 10000,
            "equity": 10500
            # No updated_at field
        }

        response = client.get("/api/system/status")
        data = response.json()
        assert data["paper_broker"] == "UNKNOWN"


def test_paper_broker_invalid_timestamp():
    """Test that invalid timestamp produces UNKNOWN."""
    with patch("ml_service.trading.paper_broker.get_account") as mock_account, \
         patch("ml_service.trading.mode_manager.get_trading_mode") as mock_mode:

        mock_mode.return_value = "PAPER"
        mock_account.return_value = {
            "balance": 10000,
            "equity": 10500,
            "updated_at": "invalid-timestamp"
        }

        response = client.get("/api/system/status")
        data = response.json()
        assert data["paper_broker"] == "UNKNOWN"
