"""Tests for Trade Explorer REST API routes.

Tests route behavior with mocked ExplorerQueryService.
Does NOT test repository or database layer.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock

from ml_service.api.main import app
from ml_service.api.explorer_routes import get_explorer_service
from ml_service.services.explorer_query_service import (
    TradeListResult,
    TradeWithSignal,
    MetadataResult
)
from ml_service.repositories.trade_repository import TradePosition
from ml_service.repositories.signal_repository import Signal
from ml_service.analytics import TradeAnalyticsResult


@pytest.fixture
def mock_service():
    """Mock ExplorerQueryService."""
    return Mock()


@pytest.fixture
def client(mock_service):
    """Test client with mocked service."""
    app.dependency_overrides[get_explorer_service] = lambda: mock_service
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_trade():
    """Sample trade position."""
    return TradePosition(
        id=1,
        symbol="BTCUSDT",
        direction="LONG",
        entry_price=50000.0,
        current_price=51000.0,
        size_usdt=1000.0,
        qty=0.02,
        stop_loss=49000.0,
        take_profit=52000.0,
        signal_id=10,
        status="OPEN",
        realized_pnl=0.0,
        opened_at="2024-01-01T00:00:00",
        closed_at=None,
        confidence=85,
        regime="TRENDING",
        timeframe="1h",
        prob_short=0.1,
        prob_neutral=0.2,
        prob_long=0.7,
        execution_edge=0.5,
        skip_reason=None,
        mae=None,
        mfe=None,
        mae_timestamp=None,
        mfe_timestamp=None,
        profit_capture_ratio=None,
        final_exit_reason=None,
        trailing_stop_activated=0,
        sl_move_count=0,
        break_even_triggered=0,
        execution_policy="DEFAULT"
    )


@pytest.fixture
def sample_signal():
    """Sample signal."""
    return Signal(
        id=10,
        symbol="BTCUSDT",
        timeframe="1h",
        timestamp=1704067200,
        direction="LONG",
        confidence=85,
        features_json=None,
        created_at="2024-01-01T00:00:00"
    )


class TestGetTrades:
    """Test GET /api/v1/explorer/trades."""

    def test_get_trades_success(self, client, mock_service, sample_trade):
        """Should return paginated trade list."""
        mock_service.get_trade_list.return_value = TradeListResult(
            trades=[sample_trade],
            total=1,
            limit=100,
            offset=0
        )

        response = client.get("/api/v1/explorer/trades")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["limit"] == 100
        assert data["offset"] == 0
        assert len(data["trades"]) == 1
        assert data["trades"][0]["id"] == 1
        assert data["trades"][0]["symbol"] == "BTCUSDT"

    def test_get_trades_with_filters(self, client, mock_service, sample_trade):
        """Should pass filters to service."""
        mock_service.get_trade_list.return_value = TradeListResult(
            trades=[sample_trade],
            total=1,
            limit=50,
            offset=10
        )

        response = client.get(
            "/api/v1/explorer/trades",
            params={
                "status": "OPEN",
                "symbol": "BTCUSDT",
                "direction": "LONG",
                "limit": 50,
                "offset": 10,
                "sort_by": "opened_at",
                "sort_order": "DESC"
            }
        )

        assert response.status_code == 200
        mock_service.get_trade_list.assert_called_once_with(
            status="OPEN",
            symbol="BTCUSDT",
            direction="LONG",
            limit=50,
            offset=10,
            sort_by="opened_at",
            sort_order="DESC"
        )

    def test_get_trades_empty_result(self, client, mock_service):
        """Should handle empty trade list."""
        mock_service.get_trade_list.return_value = TradeListResult(
            trades=[],
            total=0,
            limit=100,
            offset=0
        )

        response = client.get("/api/v1/explorer/trades")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["trades"]) == 0

    def test_get_trades_limit_validation(self, client, mock_service):
        """Should validate limit parameter."""
        response = client.get("/api/v1/explorer/trades?limit=2000")
        assert response.status_code == 422

    def test_get_trades_offset_validation(self, client, mock_service):
        """Should validate offset parameter."""
        response = client.get("/api/v1/explorer/trades?offset=-1")
        assert response.status_code == 422


class TestGetTradeDetail:
    """Test GET /api/v1/explorer/trades/{id}."""

    def test_get_trade_detail_success(self, client, mock_service, sample_trade, sample_signal):
        """Should return trade with signal."""
        mock_service.get_trade_detail.return_value = TradeWithSignal(
            trade=sample_trade,
            signal=sample_signal
        )

        response = client.get("/api/v1/explorer/trades/1")

        assert response.status_code == 200
        data = response.json()
        assert data["trade"]["id"] == 1
        assert data["trade"]["symbol"] == "BTCUSDT"
        assert data["signal"]["id"] == 10
        assert data["signal"]["confidence"] == 85

    def test_get_trade_detail_without_signal(self, client, mock_service, sample_trade):
        """Should handle trade without signal."""
        mock_service.get_trade_detail.return_value = TradeWithSignal(
            trade=sample_trade,
            signal=None
        )

        response = client.get("/api/v1/explorer/trades/1")

        assert response.status_code == 200
        data = response.json()
        assert data["trade"]["id"] == 1
        assert data["signal"] is None

    def test_get_trade_detail_not_found(self, client, mock_service):
        """Should return 404 for non-existent trade."""
        mock_service.get_trade_detail.return_value = None

        response = client.get("/api/v1/explorer/trades/999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetSummary:
    """Test GET /api/v1/explorer/summary."""

    def test_get_summary_success(self, client, mock_service):
        """Should return trade analytics summary."""
        mock_service.get_summary.return_value = TradeAnalyticsResult(
            total_trades=100,
            winning_trades=65,
            losing_trades=35,
            win_rate=0.65,
            gross_profit=20000.0,
            gross_loss=5000.0,
            net_profit=15000.0,
            average_profit=307.69,
            average_loss=142.86,
            average_hold_duration_seconds=88200.0,
            average_trade_duration_seconds=88200.0,
            largest_win=1000.0,
            largest_loss=-500.0,
            long_count=60,
            short_count=40,
            open_count=0,
            closed_count=100
        )

        response = client.get("/api/v1/explorer/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_trades"] == 100
        assert data["win_rate"] == 0.65
        assert data["net_profit"] == 15000.0

    def test_get_summary_no_trades(self, client, mock_service):
        """Should handle zero trades."""
        mock_service.get_summary.return_value = TradeAnalyticsResult(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            gross_profit=0.0,
            gross_loss=0.0,
            net_profit=0.0,
            average_profit=0.0,
            average_loss=0.0,
            average_hold_duration_seconds=0.0,
            average_trade_duration_seconds=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            long_count=0,
            short_count=0,
            open_count=0,
            closed_count=0
        )

        response = client.get("/api/v1/explorer/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_trades"] == 0


class TestGetMetadata:
    """Test GET /api/v1/explorer/metadata."""

    def test_get_metadata_success(self, client, mock_service):
        """Should return filter metadata."""
        mock_service.get_metadata.return_value = MetadataResult(
            symbols={"BTCUSDT", "ETHUSDT"},
            directions={"LONG", "SHORT"},
            statuses={"OPEN", "TP_HIT", "SL_HIT"}
        )

        response = client.get("/api/v1/explorer/metadata")

        assert response.status_code == 200
        data = response.json()
        assert "BTCUSDT" in data["symbols"]
        assert "ETHUSDT" in data["symbols"]
        assert "LONG" in data["directions"]
        assert "SHORT" in data["directions"]
        assert "OPEN" in data["statuses"]

    def test_get_metadata_empty(self, client, mock_service):
        """Should handle empty metadata."""
        mock_service.get_metadata.return_value = MetadataResult(
            symbols=set(),
            directions=set(),
            statuses=set()
        )

        response = client.get("/api/v1/explorer/metadata")

        assert response.status_code == 200
        data = response.json()
        assert data["symbols"] == []
        assert data["directions"] == []
        assert data["statuses"] == []


class TestDependencyInjection:
    """Test dependency injection wiring."""

    def test_dependency_override_works(self, mock_service):
        """Should use overridden service."""
        app.dependency_overrides[get_explorer_service] = lambda: mock_service

        mock_service.get_trade_list.return_value = TradeListResult(
            trades=[],
            total=0,
            limit=100,
            offset=0
        )

        client = TestClient(app)
        response = client.get("/api/v1/explorer/trades")

        assert response.status_code == 200
        mock_service.get_trade_list.assert_called_once()

        app.dependency_overrides.clear()


class TestEndpointIntegration:
    """Test that all endpoints are properly registered."""

    def test_all_endpoints_registered(self):
        """Should have all required endpoints."""
        client = TestClient(app)

        routes = [route.path for route in app.routes]

        assert "/api/v1/explorer/trades" in routes
        assert "/api/v1/explorer/trades/{trade_id}" in routes
        assert "/api/v1/explorer/summary" in routes
        assert "/api/v1/explorer/metadata" in routes
