"""Integration tests for Trade Explorer API.

Tests full request/response flow with mocked repositories.
Covers pagination, sorting, filtering, validation, and edge cases.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock

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
def sample_trades():
    """Generate sample trade positions."""
    return [
        TradePosition(
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
            realized_pnl=100.0,
            opened_at="2026-07-06T08:00:00",
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
        ),
        TradePosition(
            id=2,
            symbol="ETHUSDT",
            direction="SHORT",
            entry_price=3000.0,
            current_price=2950.0,
            size_usdt=500.0,
            qty=0.16,
            stop_loss=3050.0,
            take_profit=2900.0,
            signal_id=11,
            status="CLOSED",
            realized_pnl=50.0,
            opened_at="2026-07-05T10:00:00",
            closed_at="2026-07-06T10:00:00",
            confidence=75,
            regime="RANGING",
            timeframe="4h",
            prob_short=0.6,
            prob_neutral=0.3,
            prob_long=0.1,
            execution_edge=0.3,
            skip_reason=None,
            mae=-20.0,
            mfe=60.0,
            mae_timestamp="2026-07-05T12:00:00",
            mfe_timestamp="2026-07-06T09:00:00",
            profit_capture_ratio=0.83,
            final_exit_reason="TP_HIT",
            trailing_stop_activated=0,
            sl_move_count=1,
            break_even_triggered=0,
            execution_policy="AGGRESSIVE"
        ),
        TradePosition(
            id=3,
            symbol="BTCUSDT",
            direction="SHORT",
            entry_price=51000.0,
            current_price=50500.0,
            size_usdt=800.0,
            qty=0.016,
            stop_loss=51500.0,
            take_profit=50000.0,
            signal_id=None,
            status="CLOSED",
            realized_pnl=-50.0,
            opened_at="2026-07-04T14:00:00",
            closed_at="2026-07-05T16:00:00",
            confidence=None,
            regime=None,
            timeframe=None,
            prob_short=None,
            prob_neutral=None,
            prob_long=None,
            execution_edge=None,
            skip_reason=None,
            mae=-80.0,
            mfe=30.0,
            mae_timestamp="2026-07-04T18:00:00",
            mfe_timestamp="2026-07-05T10:00:00",
            profit_capture_ratio=0.38,
            final_exit_reason="SL_HIT",
            trailing_stop_activated=0,
            sl_move_count=0,
            break_even_triggered=0,
            execution_policy="DEFAULT"
        ),
    ]


@pytest.fixture
def sample_signal():
    """Sample signal."""
    return Signal(
        id=10,
        symbol="BTCUSDT",
        timeframe="1h",
        timestamp=1720252800,
        direction="LONG",
        confidence=85,
        features_json=None,
        created_at="2026-07-06T08:00:00"
    )


class TestTradesListEndpoint:
    """Integration tests for GET /api/v1/explorer/trades."""

    def test_get_all_trades_default_params(self, client, mock_service, sample_trades):
        """Should return trades with default pagination."""
        mock_service.get_trade_list.return_value = TradeListResult(
            trades=sample_trades,
            total=3,
            limit=100,
            offset=0
        )

        response = client.get("/api/v1/explorer/trades")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["limit"] == 100
        assert data["offset"] == 0
        assert len(data["trades"]) == 3
        assert data["trades"][0]["id"] == 1
        assert data["trades"][1]["id"] == 2
        assert data["trades"][2]["id"] == 3

    def test_pagination_first_page(self, client, mock_service, sample_trades):
        """Should return first page of results."""
        mock_service.get_trade_list.return_value = TradeListResult(
            trades=sample_trades[:2],
            total=10,
            limit=2,
            offset=0
        )

        response = client.get("/api/v1/explorer/trades?limit=2&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert data["limit"] == 2
        assert data["offset"] == 0
        assert len(data["trades"]) == 2

    def test_pagination_second_page(self, client, mock_service, sample_trades):
        """Should return second page of results."""
        mock_service.get_trade_list.return_value = TradeListResult(
            trades=[sample_trades[2]],
            total=10,
            limit=2,
            offset=2
        )

        response = client.get("/api/v1/explorer/trades?limit=2&offset=2")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert data["limit"] == 2
        assert data["offset"] == 2
        assert len(data["trades"]) == 1
        assert data["trades"][0]["id"] == 3

    def test_empty_result_set(self, client, mock_service):
        """Should handle empty trade list gracefully."""
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

    def test_filter_by_status(self, client, mock_service, sample_trades):
        """Should filter trades by status."""
        mock_service.get_trade_list.return_value = TradeListResult(
            trades=[sample_trades[1], sample_trades[2]],
            total=2,
            limit=100,
            offset=0
        )

        response = client.get("/api/v1/explorer/trades?status=CLOSED")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(t["status"] == "CLOSED" for t in data["trades"])
        mock_service.get_trade_list.assert_called_once_with(
            status="CLOSED",
            symbol=None,
            direction=None,
            limit=100,
            offset=0,
            sort_by="opened_at",
            sort_order="DESC"
        )

    def test_filter_by_symbol(self, client, mock_service, sample_trades):
        """Should filter trades by symbol."""
        mock_service.get_trade_list.return_value = TradeListResult(
            trades=[sample_trades[0], sample_trades[2]],
            total=2,
            limit=100,
            offset=0
        )

        response = client.get("/api/v1/explorer/trades?symbol=BTCUSDT")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(t["symbol"] == "BTCUSDT" for t in data["trades"])

    def test_filter_by_direction(self, client, mock_service, sample_trades):
        """Should filter trades by direction."""
        mock_service.get_trade_list.return_value = TradeListResult(
            trades=[sample_trades[0]],
            total=1,
            limit=100,
            offset=0
        )

        response = client.get("/api/v1/explorer/trades?direction=LONG")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["trades"][0]["direction"] == "LONG"

    def test_multiple_filters(self, client, mock_service, sample_trades):
        """Should apply multiple filters simultaneously."""
        mock_service.get_trade_list.return_value = TradeListResult(
            trades=[sample_trades[2]],
            total=1,
            limit=100,
            offset=0
        )

        response = client.get(
            "/api/v1/explorer/trades?symbol=BTCUSDT&direction=SHORT&status=CLOSED"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["trades"][0]["symbol"] == "BTCUSDT"
        assert data["trades"][0]["direction"] == "SHORT"
        assert data["trades"][0]["status"] == "CLOSED"

    def test_sort_by_realized_pnl_asc(self, client, mock_service, sample_trades):
        """Should sort trades by realized PnL ascending."""
        sorted_trades = sorted(sample_trades, key=lambda t: t.realized_pnl)
        mock_service.get_trade_list.return_value = TradeListResult(
            trades=sorted_trades,
            total=3,
            limit=100,
            offset=0
        )

        response = client.get("/api/v1/explorer/trades?sort_by=realized_pnl&sort_order=ASC")

        assert response.status_code == 200
        data = response.json()
        assert data["trades"][0]["realized_pnl"] == -50.0
        assert data["trades"][1]["realized_pnl"] == 50.0
        assert data["trades"][2]["realized_pnl"] == 100.0
        mock_service.get_trade_list.assert_called_once_with(
            status=None,
            symbol=None,
            direction=None,
            limit=100,
            offset=0,
            sort_by="realized_pnl",
            sort_order="ASC"
        )

    def test_sort_by_opened_at_desc(self, client, mock_service, sample_trades):
        """Should sort trades by opened_at descending."""
        mock_service.get_trade_list.return_value = TradeListResult(
            trades=sample_trades,
            total=3,
            limit=100,
            offset=0
        )

        response = client.get("/api/v1/explorer/trades?sort_by=opened_at&sort_order=DESC")

        assert response.status_code == 200
        mock_service.get_trade_list.assert_called_once_with(
            status=None,
            symbol=None,
            direction=None,
            limit=100,
            offset=0,
            sort_by="opened_at",
            sort_order="DESC"
        )


class TestTradesValidation:
    """Test request validation for trades endpoint."""

    def test_limit_exceeds_maximum(self, client, mock_service):
        """Should reject limit > 1000 with 422."""
        response = client.get("/api/v1/explorer/trades?limit=2000")

        assert response.status_code == 422
        assert "detail" in response.json()

    def test_limit_below_minimum(self, client, mock_service):
        """Should reject limit < 1 with 422."""
        response = client.get("/api/v1/explorer/trades?limit=0")

        assert response.status_code == 422

    def test_negative_offset(self, client, mock_service):
        """Should reject negative offset with 422."""
        response = client.get("/api/v1/explorer/trades?offset=-1")

        assert response.status_code == 422

    def test_invalid_limit_type(self, client, mock_service):
        """Should reject non-integer limit with 422."""
        response = client.get("/api/v1/explorer/trades?limit=invalid")

        assert response.status_code == 422

    def test_invalid_offset_type(self, client, mock_service):
        """Should reject non-integer offset with 422."""
        response = client.get("/api/v1/explorer/trades?offset=abc")

        assert response.status_code == 422


class TestTradeDetailEndpoint:
    """Integration tests for GET /api/v1/explorer/trades/{id}."""

    def test_get_trade_with_signal(self, client, mock_service, sample_trades, sample_signal):
        """Should return trade detail with linked signal."""
        mock_service.get_trade_detail.return_value = TradeWithSignal(
            trade=sample_trades[0],
            signal=sample_signal
        )

        response = client.get("/api/v1/explorer/trades/1")

        assert response.status_code == 200
        data = response.json()
        assert data["trade"]["id"] == 1
        assert data["trade"]["symbol"] == "BTCUSDT"
        assert data["signal"] is not None
        assert data["signal"]["id"] == 10
        assert data["signal"]["confidence"] == 85

    def test_get_trade_without_signal(self, client, mock_service, sample_trades):
        """Should return trade detail without signal."""
        mock_service.get_trade_detail.return_value = TradeWithSignal(
            trade=sample_trades[2],
            signal=None
        )

        response = client.get("/api/v1/explorer/trades/3")

        assert response.status_code == 200
        data = response.json()
        assert data["trade"]["id"] == 3
        assert data["trade"]["signal_id"] is None
        assert data["signal"] is None

    def test_trade_not_found(self, client, mock_service):
        """Should return 404 for non-existent trade."""
        mock_service.get_trade_detail.return_value = None

        response = client.get("/api/v1/explorer/trades/999")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_invalid_trade_id(self, client, mock_service):
        """Should return 422 for invalid trade ID type."""
        response = client.get("/api/v1/explorer/trades/invalid")

        assert response.status_code == 422


class TestSummaryEndpoint:
    """Integration tests for GET /api/v1/explorer/summary."""

    def test_get_summary_with_trades(self, client, mock_service):
        """Should return complete analytics summary."""
        mock_service.get_summary.return_value = TradeAnalyticsResult(
            total_trades=100,
            winning_trades=65,
            losing_trades=35,
            win_rate=0.65,
            gross_profit=25000.0,
            gross_loss=8000.0,
            net_profit=17000.0,
            average_profit=384.62,
            average_loss=228.57,
            average_hold_duration_seconds=72000.0,
            average_trade_duration_seconds=86400.0,
            largest_win=1500.0,
            largest_loss=-800.0,
            long_count=58,
            short_count=42,
            open_count=5,
            closed_count=95
        )

        response = client.get("/api/v1/explorer/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_trades"] == 100
        assert data["winning_trades"] == 65
        assert data["losing_trades"] == 35
        assert data["win_rate"] == 0.65
        assert data["net_profit"] == 17000.0
        assert data["gross_profit"] == 25000.0
        assert data["gross_loss"] == 8000.0
        assert data["long_count"] == 58
        assert data["short_count"] == 42

    def test_get_summary_empty_dataset(self, client, mock_service):
        """Should return zero values for empty dataset."""
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
        assert data["win_rate"] == 0.0
        assert data["net_profit"] == 0.0


class TestMetadataEndpoint:
    """Integration tests for GET /api/v1/explorer/metadata."""

    def test_get_metadata_with_data(self, client, mock_service):
        """Should return available filter values."""
        mock_service.get_metadata.return_value = MetadataResult(
            symbols={"BTCUSDT", "ETHUSDT", "SOLUSDT"},
            directions={"LONG", "SHORT"},
            statuses={"OPEN", "CLOSED", "TP_HIT", "SL_HIT"}
        )

        response = client.get("/api/v1/explorer/metadata")

        assert response.status_code == 200
        data = response.json()
        assert len(data["symbols"]) == 3
        assert "BTCUSDT" in data["symbols"]
        assert "ETHUSDT" in data["symbols"]
        assert "SOLUSDT" in data["symbols"]
        assert len(data["directions"]) == 2
        assert "LONG" in data["directions"]
        assert "SHORT" in data["directions"]
        assert len(data["statuses"]) == 4

    def test_get_metadata_empty_dataset(self, client, mock_service):
        """Should return empty sets for empty dataset."""
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


class TestEndToEndScenarios:
    """End-to-end integration test scenarios."""

    def test_paginate_through_all_trades(self, client, mock_service, sample_trades):
        """Should paginate through entire trade list."""
        mock_service.get_trade_list.side_effect = [
            TradeListResult(trades=sample_trades[:2], total=3, limit=2, offset=0),
            TradeListResult(trades=[sample_trades[2]], total=3, limit=2, offset=2),
        ]

        page1 = client.get("/api/v1/explorer/trades?limit=2&offset=0")
        assert page1.status_code == 200
        assert len(page1.json()["trades"]) == 2

        page2 = client.get("/api/v1/explorer/trades?limit=2&offset=2")
        assert page2.status_code == 200
        assert len(page2.json()["trades"]) == 1

    def test_filter_then_get_detail(self, client, mock_service, sample_trades, sample_signal):
        """Should filter trades then fetch detail."""
        mock_service.get_trade_list.return_value = TradeListResult(
            trades=[sample_trades[0]],
            total=1,
            limit=100,
            offset=0
        )

        list_response = client.get("/api/v1/explorer/trades?status=OPEN")
        assert list_response.status_code == 200
        trade_id = list_response.json()["trades"][0]["id"]

        mock_service.get_trade_detail.return_value = TradeWithSignal(
            trade=sample_trades[0],
            signal=sample_signal
        )

        detail_response = client.get(f"/api/v1/explorer/trades/{trade_id}")
        assert detail_response.status_code == 200
        assert detail_response.json()["trade"]["id"] == trade_id

    def test_metadata_reflects_filtered_results(self, client, mock_service, sample_trades):
        """Should use metadata to validate filter values."""
        mock_service.get_metadata.return_value = MetadataResult(
            symbols={"BTCUSDT", "ETHUSDT"},
            directions={"LONG", "SHORT"},
            statuses={"OPEN", "CLOSED"}
        )

        metadata_response = client.get("/api/v1/explorer/metadata")
        available_symbols = metadata_response.json()["symbols"]

        mock_service.get_trade_list.return_value = TradeListResult(
            trades=[sample_trades[0]],
            total=1,
            limit=100,
            offset=0
        )

        for symbol in available_symbols:
            trades_response = client.get(f"/api/v1/explorer/trades?symbol={symbol}")
            assert trades_response.status_code == 200
