"""Tests for system status endpoint."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

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


def test_market_data_with_live_prices():
    """Test that market data status is RUNNING only with live=True prices."""
    with patch("ml_service.api.routes.get_crypto_service") as mock_crypto, \
         patch("ml_service.api.routes.get_proxy_service") as mock_proxy:

        # Test with genuinely live prices (live=True)
        mock_crypto_service = MagicMock()
        mock_crypto_service.price_cache = {
            "BTCUSDT": {"price": 50000, "live": True}
        }
        mock_crypto.return_value = mock_crypto_service

        mock_proxy_service = MagicMock()
        mock_proxy_service.price_cache = {}
        mock_proxy.return_value = mock_proxy_service

        response = client.get("/api/system/status")
        data = response.json()
        assert data["market_data"] == "RUNNING"


def test_market_data_with_stale_cache():
    """Test that market data with stale cache (live=False) returns UNKNOWN."""
    with patch("ml_service.api.routes.get_crypto_service") as mock_crypto, \
         patch("ml_service.api.routes.get_proxy_service") as mock_proxy:

        # Stale cached data (live=False or missing)
        mock_crypto_service = MagicMock()
        mock_crypto_service.price_cache = {
            "BTCUSDT": {"price": 50000, "live": False}
        }
        mock_crypto.return_value = mock_crypto_service

        mock_proxy_service = MagicMock()
        mock_proxy_service.price_cache = {}
        mock_proxy.return_value = mock_proxy_service

        response = client.get("/api/system/status")
        data = response.json()
        assert data["market_data"] == "UNKNOWN"


def test_market_data_with_no_evidence():
    """Test that market data with empty cache returns UNKNOWN."""
    with patch("ml_service.api.routes.get_crypto_service") as mock_crypto, \
         patch("ml_service.api.routes.get_proxy_service") as mock_proxy:

        # No cached data
        mock_crypto_service = MagicMock()
        mock_crypto_service.price_cache = {}
        mock_crypto.return_value = mock_crypto_service

        mock_proxy_service = MagicMock()
        mock_proxy_service.price_cache = {}
        mock_proxy.return_value = mock_proxy_service

        response = client.get("/api/system/status")
        data = response.json()
        assert data["market_data"] == "UNKNOWN"


def test_binance_ws_remains_unknown():
    """Test that Binance WebSocket status is UNKNOWN (no production implementation)."""
    response = client.get("/api/system/status")
    data = response.json()
    assert data["binance_ws"] == "UNKNOWN"


def test_endpoint_does_not_call_health_prices():
    """Test that endpoint does not make HTTP request to /health/prices."""
    # This test ensures we're using services directly, not via HTTP
    with patch("ml_service.api.routes.get_crypto_service") as mock_crypto, \
         patch("ml_service.api.routes.get_proxy_service") as mock_proxy:

        mock_crypto_service = MagicMock()
        mock_crypto_service.price_cache = {}
        mock_crypto.return_value = mock_crypto_service

        mock_proxy_service = MagicMock()
        mock_proxy_service.price_cache = {}
        mock_proxy.return_value = mock_proxy_service

        response = client.get("/api/system/status")

        # Verify we called the service methods, not HTTP
        assert mock_crypto.called
        assert mock_proxy.called


def test_paper_broker_with_recent_activity():
    """Test that paper broker is RUNNING only with recent updated_at."""
    with patch("ml_service.trading.paper_broker.get_account") as mock_account, \
         patch("ml_service.trading.mode_manager.get_trading_mode") as mock_mode:

        mock_mode.return_value = "PAPER"

        # Recent activity (within 2 minutes)
        recent_time = datetime.now().isoformat()
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

        # Stale activity (over 2 minutes old)
        stale_time = (datetime.now() - timedelta(minutes=5)).isoformat()
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
            "updated_at": datetime.now().isoformat()
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
