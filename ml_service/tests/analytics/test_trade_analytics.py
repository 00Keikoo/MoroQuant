"""Unit tests for trade analytics calculation engine."""

from datetime import datetime, timedelta

import pytest

from ml_service.analytics import calculate_trade_analytics, TradeAnalyticsResult
from ml_service.repositories.trade_repository import TradePosition


def make_trade(
    trade_id: int = 1,
    symbol: str = "BTCUSDT",
    direction: str = "LONG",
    entry_price: float = 50000.0,
    realized_pnl: float = 100.0,
    status: str = "TP_HIT",
    opened_at: str = None,
    closed_at: str = None,
) -> TradePosition:
    """Factory function for creating synthetic TradePosition objects."""
    if opened_at is None:
        opened_at = "2026-07-01T10:00:00"
    if closed_at is None and status != "OPEN":
        closed_at = "2026-07-01T11:00:00"

    return TradePosition(
        id=trade_id,
        symbol=symbol,
        direction=direction,
        entry_price=entry_price,
        current_price=None,
        size_usdt=1000.0,
        qty=0.02,
        stop_loss=None,
        take_profit=None,
        signal_id=None,
        status=status,
        realized_pnl=realized_pnl,
        opened_at=opened_at,
        closed_at=closed_at,
        confidence=None,
        regime=None,
        timeframe=None,
        prob_short=None,
        prob_neutral=None,
        prob_long=None,
        execution_edge=None,
        skip_reason=None,
        mae=None,
        mfe=None,
        mae_timestamp=None,
        mfe_timestamp=None,
        profit_capture_ratio=None,
        final_exit_reason=None,
        trailing_stop_activated=None,
        sl_move_count=None,
        break_even_triggered=None,
        execution_policy=None,
    )


class TestEmptyTrades:
    """Test analytics with empty trade list."""

    def test_empty_list_returns_zeros(self):
        result = calculate_trade_analytics([])

        assert result.total_trades == 0
        assert result.winning_trades == 0
        assert result.losing_trades == 0
        assert result.win_rate == 0.0
        assert result.gross_profit == 0.0
        assert result.gross_loss == 0.0
        assert result.net_profit == 0.0
        assert result.average_profit == 0.0
        assert result.average_loss == 0.0
        assert result.largest_win == 0.0
        assert result.largest_loss == 0.0
        assert result.long_count == 0
        assert result.short_count == 0
        assert result.open_count == 0
        assert result.closed_count == 0
        assert result.average_hold_duration_seconds == 0.0
        assert result.average_trade_duration_seconds == 0.0


class TestSingleTrade:
    """Test analytics with single trades."""

    def test_one_winning_trade(self):
        trades = [make_trade(trade_id=1, realized_pnl=250.0, direction="LONG")]
        result = calculate_trade_analytics(trades)

        assert result.total_trades == 1
        assert result.winning_trades == 1
        assert result.losing_trades == 0
        assert result.win_rate == 1.0
        assert result.gross_profit == 250.0
        assert result.gross_loss == 0.0
        assert result.net_profit == 250.0
        assert result.average_profit == 250.0
        assert result.average_loss == 0.0
        assert result.largest_win == 250.0
        assert result.largest_loss == 0.0
        assert result.long_count == 1
        assert result.short_count == 0
        assert result.closed_count == 1

    def test_one_losing_trade(self):
        trades = [make_trade(trade_id=1, realized_pnl=-150.0, direction="SHORT")]
        result = calculate_trade_analytics(trades)

        assert result.total_trades == 1
        assert result.winning_trades == 0
        assert result.losing_trades == 1
        assert result.win_rate == 0.0
        assert result.gross_profit == 0.0
        assert result.gross_loss == 150.0
        assert result.net_profit == -150.0
        assert result.average_profit == 0.0
        assert result.average_loss == 150.0
        assert result.largest_win == 0.0
        assert result.largest_loss == -150.0
        assert result.long_count == 0
        assert result.short_count == 1
        assert result.closed_count == 1

    def test_one_breakeven_trade(self):
        trades = [make_trade(trade_id=1, realized_pnl=0.0)]
        result = calculate_trade_analytics(trades)

        assert result.total_trades == 1
        assert result.winning_trades == 0
        assert result.losing_trades == 0
        assert result.win_rate == 0.0
        assert result.net_profit == 0.0


class TestMixedTrades:
    """Test analytics with mixed winning and losing trades."""

    def test_multiple_winners_and_losers(self):
        trades = [
            make_trade(trade_id=1, realized_pnl=300.0),
            make_trade(trade_id=2, realized_pnl=-100.0),
            make_trade(trade_id=3, realized_pnl=200.0),
            make_trade(trade_id=4, realized_pnl=-50.0),
            make_trade(trade_id=5, realized_pnl=150.0),
        ]
        result = calculate_trade_analytics(trades)

        assert result.total_trades == 5
        assert result.winning_trades == 3
        assert result.losing_trades == 2
        assert result.win_rate == 0.6
        assert result.gross_profit == 650.0
        assert result.gross_loss == 150.0
        assert result.net_profit == 500.0
        assert result.average_profit == pytest.approx(216.67, rel=0.01)
        assert result.average_loss == 75.0
        assert result.largest_win == 300.0
        assert result.largest_loss == -100.0

    def test_win_rate_calculation(self):
        trades = [
            make_trade(trade_id=1, realized_pnl=100.0),
            make_trade(trade_id=2, realized_pnl=100.0),
            make_trade(trade_id=3, realized_pnl=-50.0),
        ]
        result = calculate_trade_analytics(trades)

        assert result.win_rate == pytest.approx(0.6667, rel=0.01)


class TestDirectionCounts:
    """Test long/short direction counting."""

    def test_long_and_short_counts(self):
        trades = [
            make_trade(trade_id=1, direction="LONG"),
            make_trade(trade_id=2, direction="LONG"),
            make_trade(trade_id=3, direction="SHORT"),
            make_trade(trade_id=4, direction="LONG"),
            make_trade(trade_id=5, direction="SHORT"),
        ]
        result = calculate_trade_analytics(trades)

        assert result.long_count == 3
        assert result.short_count == 2

    def test_all_longs(self):
        trades = [
            make_trade(trade_id=i, direction="LONG") for i in range(1, 6)
        ]
        result = calculate_trade_analytics(trades)

        assert result.long_count == 5
        assert result.short_count == 0

    def test_all_shorts(self):
        trades = [
            make_trade(trade_id=i, direction="SHORT") for i in range(1, 6)
        ]
        result = calculate_trade_analytics(trades)

        assert result.long_count == 0
        assert result.short_count == 5


class TestOpenPositions:
    """Test handling of open positions."""

    def test_open_positions_excluded_from_pnl(self):
        trades = [
            make_trade(trade_id=1, realized_pnl=100.0, status="TP_HIT"),
            make_trade(trade_id=2, realized_pnl=50.0, status="OPEN", closed_at=None),
            make_trade(trade_id=3, realized_pnl=-30.0, status="SL_HIT"),
        ]
        result = calculate_trade_analytics(trades)

        assert result.total_trades == 3
        assert result.open_count == 1
        assert result.closed_count == 2
        assert result.winning_trades == 1
        assert result.losing_trades == 1
        assert result.net_profit == 70.0

    def test_all_open_positions(self):
        trades = [
            make_trade(trade_id=1, status="OPEN", closed_at=None),
            make_trade(trade_id=2, status="OPEN", closed_at=None),
        ]
        result = calculate_trade_analytics(trades)

        assert result.total_trades == 2
        assert result.open_count == 2
        assert result.closed_count == 0
        assert result.winning_trades == 0
        assert result.losing_trades == 0
        assert result.win_rate == 0.0

    def test_mixed_status_types(self):
        trades = [
            make_trade(trade_id=1, status="TP_HIT", realized_pnl=100.0),
            make_trade(trade_id=2, status="SL_HIT", realized_pnl=-50.0),
            make_trade(trade_id=3, status="MANUAL_CLOSE", realized_pnl=25.0),
            make_trade(trade_id=4, status="EXPIRED", realized_pnl=-10.0),
            make_trade(trade_id=5, status="OPEN", realized_pnl=0.0, closed_at=None),
        ]
        result = calculate_trade_analytics(trades)

        assert result.total_trades == 5
        assert result.open_count == 1
        assert result.closed_count == 4
        assert result.winning_trades == 2
        assert result.losing_trades == 2


class TestDurationCalculation:
    """Test duration calculations."""

    def test_duration_one_hour(self):
        trades = [
            make_trade(
                trade_id=1,
                opened_at="2026-07-01T10:00:00",
                closed_at="2026-07-01T11:00:00",
            )
        ]
        result = calculate_trade_analytics(trades)

        assert result.average_hold_duration_seconds == 3600.0
        assert result.average_trade_duration_seconds == 3600.0

    def test_duration_multiple_trades(self):
        trades = [
            make_trade(
                trade_id=1,
                opened_at="2026-07-01T10:00:00",
                closed_at="2026-07-01T12:00:00",
            ),
            make_trade(
                trade_id=2,
                opened_at="2026-07-01T14:00:00",
                closed_at="2026-07-01T16:00:00",
            ),
        ]
        result = calculate_trade_analytics(trades)

        assert result.average_hold_duration_seconds == 7200.0

    def test_duration_ignores_open_trades(self):
        trades = [
            make_trade(
                trade_id=1,
                opened_at="2026-07-01T10:00:00",
                closed_at="2026-07-01T11:00:00",
            ),
            make_trade(
                trade_id=2,
                status="OPEN",
                opened_at="2026-07-01T12:00:00",
                closed_at=None,
            ),
        ]
        result = calculate_trade_analytics(trades)

        assert result.average_hold_duration_seconds == 3600.0

    def test_duration_with_no_closed_trades(self):
        trades = [
            make_trade(trade_id=1, status="OPEN", closed_at=None),
        ]
        result = calculate_trade_analytics(trades)

        assert result.average_hold_duration_seconds == 0.0
        assert result.average_trade_duration_seconds == 0.0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_large_profit(self):
        trades = [make_trade(trade_id=1, realized_pnl=1_000_000.0)]
        result = calculate_trade_analytics(trades)

        assert result.gross_profit == 1_000_000.0
        assert result.largest_win == 1_000_000.0

    def test_very_large_loss(self):
        trades = [make_trade(trade_id=1, realized_pnl=-500_000.0)]
        result = calculate_trade_analytics(trades)

        assert result.gross_loss == 500_000.0
        assert result.largest_loss == -500_000.0

    def test_tiny_profit(self):
        trades = [make_trade(trade_id=1, realized_pnl=0.01)]
        result = calculate_trade_analytics(trades)

        assert result.gross_profit == 0.01
        assert result.winning_trades == 1

    def test_tiny_loss(self):
        trades = [make_trade(trade_id=1, realized_pnl=-0.01)]
        result = calculate_trade_analytics(trades)

        assert result.gross_loss == 0.01
        assert result.losing_trades == 1

    def test_many_trades(self):
        trades = [
            make_trade(trade_id=i, realized_pnl=100.0 if i % 2 == 0 else -50.0)
            for i in range(1, 101)
        ]
        result = calculate_trade_analytics(trades)

        assert result.total_trades == 100
        assert result.winning_trades == 50
        assert result.losing_trades == 50
        assert result.win_rate == 0.5

    def test_all_breakeven_trades(self):
        trades = [
            make_trade(trade_id=i, realized_pnl=0.0) for i in range(1, 6)
        ]
        result = calculate_trade_analytics(trades)

        assert result.total_trades == 5
        assert result.winning_trades == 0
        assert result.losing_trades == 0
        assert result.net_profit == 0.0
        assert result.win_rate == 0.0

    def test_duration_less_than_one_second(self):
        trades = [
            make_trade(
                trade_id=1,
                opened_at="2026-07-01T10:00:00.000000",
                closed_at="2026-07-01T10:00:00.500000",
            )
        ]
        result = calculate_trade_analytics(trades)

        assert result.average_hold_duration_seconds == 0.5

    def test_duration_multiple_days(self):
        trades = [
            make_trade(
                trade_id=1,
                opened_at="2026-07-01T10:00:00",
                closed_at="2026-07-03T10:00:00",
            )
        ]
        result = calculate_trade_analytics(trades)

        assert result.average_hold_duration_seconds == 172800.0


class TestResultDataclass:
    """Test TradeAnalyticsResult dataclass."""

    def test_result_is_dataclass(self):
        from dataclasses import is_dataclass
        assert is_dataclass(TradeAnalyticsResult)

    def test_result_fields_accessible(self):
        result = TradeAnalyticsResult(
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            win_rate=0.6,
            gross_profit=1000.0,
            gross_loss=400.0,
            net_profit=600.0,
            average_profit=166.67,
            average_loss=100.0,
            average_hold_duration_seconds=3600.0,
            average_trade_duration_seconds=3600.0,
            largest_win=300.0,
            largest_loss=-150.0,
            long_count=7,
            short_count=3,
            open_count=0,
            closed_count=10,
        )

        assert result.total_trades == 10
        assert result.winning_trades == 6
        assert result.net_profit == 600.0
