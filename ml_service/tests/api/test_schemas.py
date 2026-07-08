"""Tests for Trade Explorer API schemas."""

import pytest
from pydantic import ValidationError

from ml_service.api.schemas import (
    TradeResponse,
    SignalResponse,
    TradeDetailResponse,
    TradeListResponse,
    SummaryResponse,
    MetadataResponse,
    ErrorResponse,
)


class TestTradeResponse:
    """Tests for TradeResponse schema."""

    def test_valid_trade_response(self):
        """Test valid trade response creation."""
        trade = TradeResponse(
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
            opened_at="2026-07-06T10:00:00",
            closed_at=None,
            confidence=85,
            regime="TRENDING",
            timeframe="1h",
        )

        assert trade.id == 1
        assert trade.symbol == "BTCUSDT"
        assert trade.direction == "LONG"
        assert trade.status == "OPEN"
        assert trade.realized_pnl == 0.0

    def test_minimal_trade_response(self):
        """Test trade response with minimal required fields."""
        trade = TradeResponse(
            id=1,
            symbol="BTCUSDT",
            direction="LONG",
            entry_price=50000.0,
            size_usdt=1000.0,
            qty=0.02,
            status="OPEN",
            realized_pnl=0.0,
            opened_at="2026-07-06T10:00:00",
        )

        assert trade.current_price is None
        assert trade.stop_loss is None
        assert trade.take_profit is None
        assert trade.signal_id is None
        assert trade.closed_at is None
        assert trade.confidence is None
        assert trade.regime is None
        assert trade.timeframe is None

    def test_missing_required_field(self):
        """Test validation error on missing required field."""
        with pytest.raises(ValidationError) as exc_info:
            TradeResponse(
                id=1,
                symbol="BTCUSDT",
                direction="LONG",
                entry_price=50000.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "size_usdt" for err in errors)


class TestSignalResponse:
    """Tests for SignalResponse schema."""

    def test_valid_signal_response(self):
        """Test valid signal response creation."""
        signal = SignalResponse(
            id=10,
            symbol="BTCUSDT",
            timeframe="1h",
            timestamp=1720252800,
            direction="LONG",
            confidence=85,
        )

        assert signal.id == 10
        assert signal.symbol == "BTCUSDT"
        assert signal.timeframe == "1h"
        assert signal.confidence == 85

    def test_confidence_bounds(self):
        """Test confidence field validation bounds."""
        with pytest.raises(ValidationError):
            SignalResponse(
                id=10,
                symbol="BTCUSDT",
                timeframe="1h",
                timestamp=1720252800,
                direction="LONG",
                confidence=101,
            )

        with pytest.raises(ValidationError):
            SignalResponse(
                id=10,
                symbol="BTCUSDT",
                timeframe="1h",
                timestamp=1720252800,
                direction="LONG",
                confidence=-1,
            )


class TestTradeDetailResponse:
    """Tests for TradeDetailResponse schema."""

    def test_trade_detail_with_signal(self):
        """Test trade detail response with signal."""
        trade = TradeResponse(
            id=1,
            symbol="BTCUSDT",
            direction="LONG",
            entry_price=50000.0,
            size_usdt=1000.0,
            qty=0.02,
            status="OPEN",
            realized_pnl=0.0,
            opened_at="2026-07-06T10:00:00",
        )

        signal = SignalResponse(
            id=10,
            symbol="BTCUSDT",
            timeframe="1h",
            timestamp=1720252800,
            direction="LONG",
            confidence=85,
        )

        detail = TradeDetailResponse(trade=trade, signal=signal)

        assert detail.trade.id == 1
        assert detail.signal.id == 10

    def test_trade_detail_without_signal(self):
        """Test trade detail response without signal."""
        trade = TradeResponse(
            id=1,
            symbol="BTCUSDT",
            direction="LONG",
            entry_price=50000.0,
            size_usdt=1000.0,
            qty=0.02,
            status="OPEN",
            realized_pnl=0.0,
            opened_at="2026-07-06T10:00:00",
        )

        detail = TradeDetailResponse(trade=trade, signal=None)

        assert detail.trade.id == 1
        assert detail.signal is None


class TestTradeListResponse:
    """Tests for TradeListResponse schema."""

    def test_valid_trade_list(self):
        """Test valid trade list response."""
        trades = [
            TradeResponse(
                id=1,
                symbol="BTCUSDT",
                direction="LONG",
                entry_price=50000.0,
                size_usdt=1000.0,
                qty=0.02,
                status="OPEN",
                realized_pnl=0.0,
                opened_at="2026-07-06T10:00:00",
            ),
            TradeResponse(
                id=2,
                symbol="ETHUSDT",
                direction="SHORT",
                entry_price=3000.0,
                size_usdt=500.0,
                qty=0.16,
                status="CLOSED",
                realized_pnl=50.0,
                opened_at="2026-07-05T10:00:00",
            ),
        ]

        response = TradeListResponse(
            trades=trades,
            total=100,
            limit=10,
            offset=0,
        )

        assert len(response.trades) == 2
        assert response.total == 100
        assert response.limit == 10
        assert response.offset == 0

    def test_empty_trade_list(self):
        """Test empty trade list response."""
        response = TradeListResponse(
            trades=[],
            total=0,
            limit=10,
            offset=0,
        )

        assert len(response.trades) == 0
        assert response.total == 0


class TestSummaryResponse:
    """Tests for SummaryResponse schema."""

    def test_valid_summary(self):
        """Test valid summary response."""
        summary = SummaryResponse(
            total_trades=100,
            winning_trades=60,
            losing_trades=40,
            win_rate=0.6,
            gross_profit=10000.0,
            gross_loss=-5000.0,
            net_profit=5000.0,
            average_profit=166.67,
            average_loss=-125.0,
            average_hold_duration_seconds=3600.0,
            average_trade_duration_seconds=7200.0,
            largest_win=500.0,
            largest_loss=-300.0,
            long_count=55,
            short_count=45,
            open_count=5,
            closed_count=95,
        )

        assert summary.total_trades == 100
        assert summary.winning_trades == 60
        assert summary.win_rate == 0.6
        assert summary.net_profit == 5000.0

    def test_win_rate_bounds(self):
        """Test win rate validation bounds."""
        with pytest.raises(ValidationError):
            SummaryResponse(
                total_trades=100,
                winning_trades=60,
                losing_trades=40,
                win_rate=1.5,
                gross_profit=10000.0,
                gross_loss=-5000.0,
                net_profit=5000.0,
                average_profit=166.67,
                average_loss=-125.0,
                average_hold_duration_seconds=3600.0,
                average_trade_duration_seconds=7200.0,
                largest_win=500.0,
                largest_loss=-300.0,
                long_count=55,
                short_count=45,
                open_count=5,
                closed_count=95,
            )

    def test_negative_counts_invalid(self):
        """Test negative count validation."""
        with pytest.raises(ValidationError):
            SummaryResponse(
                total_trades=-1,
                winning_trades=60,
                losing_trades=40,
                win_rate=0.6,
                gross_profit=10000.0,
                gross_loss=-5000.0,
                net_profit=5000.0,
                average_profit=166.67,
                average_loss=-125.0,
                average_hold_duration_seconds=3600.0,
                average_trade_duration_seconds=7200.0,
                largest_win=500.0,
                largest_loss=-300.0,
                long_count=55,
                short_count=45,
                open_count=5,
                closed_count=95,
            )


class TestMetadataResponse:
    """Tests for MetadataResponse schema."""

    def test_valid_metadata(self):
        """Test valid metadata response."""
        metadata = MetadataResponse(
            symbols={"BTCUSDT", "ETHUSDT", "SOLUSDT"},
            directions={"LONG", "SHORT"},
            statuses={"OPEN", "CLOSED"},
        )

        assert len(metadata.symbols) == 3
        assert "BTCUSDT" in metadata.symbols
        assert len(metadata.directions) == 2
        assert len(metadata.statuses) == 2

    def test_empty_sets(self):
        """Test metadata with empty sets."""
        metadata = MetadataResponse(
            symbols=set(),
            directions=set(),
            statuses=set(),
        )

        assert len(metadata.symbols) == 0
        assert len(metadata.directions) == 0
        assert len(metadata.statuses) == 0


class TestErrorResponse:
    """Tests for ErrorResponse schema."""

    def test_valid_error_response(self):
        """Test valid error response."""
        error = ErrorResponse(
            detail="Trade not found",
            status_code=404,
        )

        assert error.detail == "Trade not found"
        assert error.status_code == 404

    def test_status_code_bounds(self):
        """Test status code validation bounds."""
        with pytest.raises(ValidationError):
            ErrorResponse(
                detail="Invalid request",
                status_code=399,
            )

        with pytest.raises(ValidationError):
            ErrorResponse(
                detail="Invalid request",
                status_code=600,
            )

    def test_valid_status_codes(self):
        """Test various valid status codes."""
        codes = [400, 401, 403, 404, 422, 500, 503]

        for code in codes:
            error = ErrorResponse(
                detail="Error message",
                status_code=code,
            )
            assert error.status_code == code
