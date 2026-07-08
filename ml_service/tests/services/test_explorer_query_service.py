"""Unit tests for ExplorerQueryService.

Tests repository orchestration without database access.
All repositories are mocked.
"""

import pytest
from unittest.mock import Mock, MagicMock

from ml_service.services.explorer_query_service import (
    ExplorerQueryService,
    TradeListResult,
    TradeWithSignal,
    MetadataResult
)
from ml_service.repositories.trade_repository import TradePosition
from ml_service.repositories.signal_repository import Signal
from ml_service.repositories.equity_repository import PaperAccount
from ml_service.analytics import TradeAnalyticsResult


@pytest.fixture
def mock_trade_repo():
    """Mock TradeRepository."""
    return Mock()


@pytest.fixture
def mock_signal_repo():
    """Mock SignalRepository."""
    return Mock()


@pytest.fixture
def mock_equity_repo():
    """Mock EquityRepository."""
    return Mock()


@pytest.fixture
def service(mock_trade_repo, mock_signal_repo, mock_equity_repo):
    """ExplorerQueryService with mocked dependencies."""
    return ExplorerQueryService(
        trade_repository=mock_trade_repo,
        signal_repository=mock_signal_repo,
        equity_repository=mock_equity_repo
    )


@pytest.fixture
def sample_trade():
    """Sample TradePosition."""
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
        opened_at="2026-07-06 10:00:00",
        closed_at=None,
        confidence=85,
        regime="BULLISH",
        timeframe="1h",
        prob_short=0.1,
        prob_neutral=0.2,
        prob_long=0.7,
        execution_edge=0.05,
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
        execution_policy="STANDARD"
    )


@pytest.fixture
def sample_signal():
    """Sample Signal."""
    return Signal(
        id=10,
        symbol="BTCUSDT",
        timeframe="1h",
        timestamp=1720249200,
        direction="long",
        confidence=85,
        features_json='{"feature1": 0.5}',
        created_at="2026-07-06 09:00:00"
    )


@pytest.fixture
def sample_account():
    """Sample PaperAccount."""
    return PaperAccount(
        id=1,
        balance=10000.0,
        equity=11500.0,
        unrealized_pnl=500.0,
        updated_at="2026-07-06 12:00:00"
    )


class TestDependencyInjection:
    """Test dependency injection."""

    def test_repositories_injected(self, mock_trade_repo, mock_signal_repo, mock_equity_repo):
        """Repositories are injected via constructor."""
        service = ExplorerQueryService(
            trade_repository=mock_trade_repo,
            signal_repository=mock_signal_repo,
            equity_repository=mock_equity_repo
        )

        assert service.trade_repo is mock_trade_repo
        assert service.signal_repo is mock_signal_repo
        assert service.equity_repo is mock_equity_repo


class TestGetTradeList:
    """Test get_trade_list method."""

    def test_forwards_all_parameters(self, service, mock_trade_repo, sample_trade):
        """Forwards filtering, pagination, and sorting to repository."""
        mock_trade_repo.find_all.return_value = [sample_trade]
        mock_trade_repo.count.return_value = 1

        result = service.get_trade_list(
            status="OPEN",
            symbol="BTCUSDT",
            direction="LONG",
            limit=50,
            offset=10,
            sort_by="realized_pnl",
            sort_order="ASC"
        )

        mock_trade_repo.find_all.assert_called_once_with(
            status="OPEN",
            symbol="BTCUSDT",
            direction="LONG",
            limit=50,
            offset=10,
            sort_by="realized_pnl",
            sort_order="ASC"
        )

        mock_trade_repo.count.assert_called_once_with(
            status="OPEN",
            symbol="BTCUSDT",
            direction="LONG"
        )

    def test_returns_trade_list_result(self, service, mock_trade_repo, sample_trade):
        """Returns TradeListResult with trades and metadata."""
        mock_trade_repo.find_all.return_value = [sample_trade]
        mock_trade_repo.count.return_value = 42

        result = service.get_trade_list(limit=10, offset=20)

        assert isinstance(result, TradeListResult)
        assert result.trades == [sample_trade]
        assert result.total == 42
        assert result.limit == 10
        assert result.offset == 20

    def test_empty_result(self, service, mock_trade_repo):
        """Handles empty trade list."""
        mock_trade_repo.find_all.return_value = []
        mock_trade_repo.count.return_value = 0

        result = service.get_trade_list()

        assert result.trades == []
        assert result.total == 0

    def test_default_parameters(self, service, mock_trade_repo):
        """Uses default parameters when not specified."""
        mock_trade_repo.find_all.return_value = []
        mock_trade_repo.count.return_value = 0

        service.get_trade_list()

        mock_trade_repo.find_all.assert_called_once_with(
            status=None,
            symbol=None,
            direction=None,
            limit=100,
            offset=0,
            sort_by="opened_at",
            sort_order="DESC"
        )


class TestGetTradeDetail:
    """Test get_trade_detail method."""

    def test_returns_trade_with_signal(self, service, mock_trade_repo, mock_signal_repo, sample_trade, sample_signal):
        """Returns trade with linked signal."""
        mock_trade_repo.find_by_id.return_value = sample_trade
        mock_signal_repo.find_by_id.return_value = sample_signal

        result = service.get_trade_detail(1)

        assert isinstance(result, TradeWithSignal)
        assert result.trade == sample_trade
        assert result.signal == sample_signal

        mock_trade_repo.find_by_id.assert_called_once_with(1)
        mock_signal_repo.find_by_id.assert_called_once_with(10)

    def test_trade_without_signal(self, service, mock_trade_repo, mock_signal_repo, sample_trade):
        """Handles trade without signal_id."""
        trade_no_signal = TradePosition(
            id=2,
            symbol="ETHUSDT",
            direction="SHORT",
            entry_price=3000.0,
            current_price=2900.0,
            size_usdt=500.0,
            qty=0.167,
            stop_loss=3100.0,
            take_profit=2800.0,
            signal_id=None,
            status="TP_HIT",
            realized_pnl=100.0,
            opened_at="2026-07-05 10:00:00",
            closed_at="2026-07-05 12:00:00",
            confidence=None,
            regime=None,
            timeframe=None,
            prob_short=None,
            prob_neutral=None,
            prob_long=None,
            execution_edge=None,
            skip_reason=None,
            mae=-50.0,
            mfe=150.0,
            mae_timestamp="2026-07-05 10:30:00",
            mfe_timestamp="2026-07-05 11:45:00",
            profit_capture_ratio=0.67,
            final_exit_reason="TP_HIT",
            trailing_stop_activated=0,
            sl_move_count=0,
            break_even_triggered=0,
            execution_policy="STANDARD"
        )

        mock_trade_repo.find_by_id.return_value = trade_no_signal

        result = service.get_trade_detail(2)

        assert result.trade == trade_no_signal
        assert result.signal is None
        mock_signal_repo.find_by_id.assert_not_called()

    def test_missing_trade(self, service, mock_trade_repo, mock_signal_repo):
        """Returns None when trade not found."""
        mock_trade_repo.find_by_id.return_value = None

        result = service.get_trade_detail(999)

        assert result is None
        mock_signal_repo.find_by_id.assert_not_called()

    def test_trade_with_missing_signal(self, service, mock_trade_repo, mock_signal_repo, sample_trade):
        """Handles trade with signal_id but signal not found."""
        mock_trade_repo.find_by_id.return_value = sample_trade
        mock_signal_repo.find_by_id.return_value = None

        result = service.get_trade_detail(1)

        assert result.trade == sample_trade
        assert result.signal is None


class TestGetSummary:
    """Test get_summary method."""

    def test_delegates_to_trade_analytics(self, service, mock_trade_repo):
        """Delegates calculation to TradeAnalytics."""
        trade1 = TradePosition(
            id=1, symbol="BTCUSDT", direction="LONG", entry_price=50000.0,
            current_price=51000.0, size_usdt=1000.0, qty=0.02, stop_loss=49000.0,
            take_profit=52000.0, signal_id=None, status="OPEN", realized_pnl=0.0,
            opened_at="2026-07-06T10:00:00", closed_at=None,
            confidence=None, regime=None, timeframe=None, prob_short=None,
            prob_neutral=None, prob_long=None, execution_edge=None, skip_reason=None,
            mae=None, mfe=None, mae_timestamp=None, mfe_timestamp=None,
            profit_capture_ratio=None, final_exit_reason=None,
            trailing_stop_activated=0, sl_move_count=0, break_even_triggered=0,
            execution_policy="STANDARD"
        )
        trade2 = TradePosition(
            id=2, symbol="ETHUSDT", direction="SHORT", entry_price=3000.0,
            current_price=2900.0, size_usdt=500.0, qty=0.167, stop_loss=3100.0,
            take_profit=2800.0, signal_id=None, status="TP_HIT", realized_pnl=50.0,
            opened_at="2026-07-05T10:00:00", closed_at="2026-07-05T12:00:00",
            confidence=None, regime=None, timeframe=None, prob_short=None,
            prob_neutral=None, prob_long=None, execution_edge=None, skip_reason=None,
            mae=-50.0, mfe=150.0, mae_timestamp=None, mfe_timestamp=None,
            profit_capture_ratio=0.67, final_exit_reason="TP_HIT",
            trailing_stop_activated=0, sl_move_count=0, break_even_triggered=0,
            execution_policy="STANDARD"
        )
        trade3 = TradePosition(
            id=3, symbol="SOLUSDT", direction="LONG", entry_price=100.0,
            current_price=95.0, size_usdt=300.0, qty=3.0, stop_loss=90.0,
            take_profit=110.0, signal_id=None, status="SL_HIT", realized_pnl=-25.0,
            opened_at="2026-07-04T10:00:00", closed_at="2026-07-04T14:00:00",
            confidence=None, regime=None, timeframe=None, prob_short=None,
            prob_neutral=None, prob_long=None, execution_edge=None, skip_reason=None,
            mae=-30.0, mfe=10.0, mae_timestamp=None, mfe_timestamp=None,
            profit_capture_ratio=None, final_exit_reason="SL_HIT",
            trailing_stop_activated=0, sl_move_count=0, break_even_triggered=0,
            execution_policy="STANDARD"
        )

        mock_trade_repo.find_all.return_value = [trade1, trade2, trade3]

        result = service.get_summary()

        assert isinstance(result, TradeAnalyticsResult)
        assert result.total_trades == 3
        assert result.open_count == 1
        assert result.closed_count == 2
        assert result.winning_trades == 1
        assert result.losing_trades == 1
        assert result.win_rate == 0.5
        assert result.gross_profit == 50.0
        assert result.gross_loss == 25.0
        assert result.net_profit == 25.0
        assert result.average_profit == 50.0
        assert result.average_loss == 25.0
        assert result.largest_win == 50.0
        assert result.largest_loss == -25.0
        assert result.long_count == 2
        assert result.short_count == 1
        assert result.average_hold_duration_seconds == 10800.0
        assert result.average_trade_duration_seconds == 10800.0

    def test_empty_dataset(self, service, mock_trade_repo):
        """Returns zero analytics for empty trade list."""
        mock_trade_repo.find_all.return_value = []

        result = service.get_summary()

        assert isinstance(result, TradeAnalyticsResult)
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

    def test_only_open_trades(self, service, mock_trade_repo):
        """Handles dataset with only open trades."""
        trade1 = TradePosition(
            id=1, symbol="BTCUSDT", direction="LONG", entry_price=50000.0,
            current_price=51000.0, size_usdt=1000.0, qty=0.02, stop_loss=49000.0,
            take_profit=52000.0, signal_id=None, status="OPEN", realized_pnl=0.0,
            opened_at="2026-07-06T10:00:00", closed_at=None,
            confidence=None, regime=None, timeframe=None, prob_short=None,
            prob_neutral=None, prob_long=None, execution_edge=None, skip_reason=None,
            mae=None, mfe=None, mae_timestamp=None, mfe_timestamp=None,
            profit_capture_ratio=None, final_exit_reason=None,
            trailing_stop_activated=0, sl_move_count=0, break_even_triggered=0,
            execution_policy="STANDARD"
        )
        trade2 = TradePosition(
            id=2, symbol="ETHUSDT", direction="SHORT", entry_price=3000.0,
            current_price=2900.0, size_usdt=500.0, qty=0.167, stop_loss=3100.0,
            take_profit=2800.0, signal_id=None, status="OPEN", realized_pnl=0.0,
            opened_at="2026-07-06T11:00:00", closed_at=None,
            confidence=None, regime=None, timeframe=None, prob_short=None,
            prob_neutral=None, prob_long=None, execution_edge=None, skip_reason=None,
            mae=None, mfe=None, mae_timestamp=None, mfe_timestamp=None,
            profit_capture_ratio=None, final_exit_reason=None,
            trailing_stop_activated=0, sl_move_count=0, break_even_triggered=0,
            execution_policy="STANDARD"
        )

        mock_trade_repo.find_all.return_value = [trade1, trade2]

        result = service.get_summary()

        assert result.total_trades == 2
        assert result.open_count == 2
        assert result.closed_count == 0
        assert result.winning_trades == 0
        assert result.losing_trades == 0
        assert result.win_rate == 0.0
        assert result.net_profit == 0.0

    def test_repository_error_propagates(self, service, mock_trade_repo):
        """Repository exceptions propagate to caller."""
        mock_trade_repo.find_all.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            service.get_summary()


class TestGetMetadata:
    """Test get_metadata method."""

    def test_extracts_unique_values(self, service, mock_trade_repo):
        """Extracts unique symbols, directions, and statuses."""
        trades = [
            TradePosition(
                id=1, symbol="BTCUSDT", direction="LONG", entry_price=50000.0,
                current_price=51000.0, size_usdt=1000.0, qty=0.02, stop_loss=49000.0,
                take_profit=52000.0, signal_id=None, status="OPEN", realized_pnl=0.0,
                opened_at="2026-07-06 10:00:00", closed_at=None, confidence=None,
                regime=None, timeframe=None, prob_short=None, prob_neutral=None,
                prob_long=None, execution_edge=None, skip_reason=None, mae=None,
                mfe=None, mae_timestamp=None, mfe_timestamp=None,
                profit_capture_ratio=None, final_exit_reason=None,
                trailing_stop_activated=0, sl_move_count=0, break_even_triggered=0,
                execution_policy="STANDARD"
            ),
            TradePosition(
                id=2, symbol="ETHUSDT", direction="SHORT", entry_price=3000.0,
                current_price=2900.0, size_usdt=500.0, qty=0.167, stop_loss=3100.0,
                take_profit=2800.0, signal_id=None, status="TP_HIT", realized_pnl=50.0,
                opened_at="2026-07-05 10:00:00", closed_at="2026-07-05 12:00:00",
                confidence=None, regime=None, timeframe=None, prob_short=None,
                prob_neutral=None, prob_long=None, execution_edge=None, skip_reason=None,
                mae=-50.0, mfe=150.0, mae_timestamp=None, mfe_timestamp=None,
                profit_capture_ratio=0.67, final_exit_reason="TP_HIT",
                trailing_stop_activated=0, sl_move_count=0, break_even_triggered=0,
                execution_policy="STANDARD"
            ),
            TradePosition(
                id=3, symbol="BTCUSDT", direction="LONG", entry_price=49000.0,
                current_price=48000.0, size_usdt=800.0, qty=0.016, stop_loss=47000.0,
                take_profit=51000.0, signal_id=None, status="SL_HIT", realized_pnl=-40.0,
                opened_at="2026-07-04 10:00:00", closed_at="2026-07-04 14:00:00",
                confidence=None, regime=None, timeframe=None, prob_short=None,
                prob_neutral=None, prob_long=None, execution_edge=None, skip_reason=None,
                mae=-60.0, mfe=20.0, mae_timestamp=None, mfe_timestamp=None,
                profit_capture_ratio=None, final_exit_reason="SL_HIT",
                trailing_stop_activated=0, sl_move_count=0, break_even_triggered=0,
                execution_policy="STANDARD"
            )
        ]

        mock_trade_repo.find_all.return_value = trades

        result = service.get_metadata()

        assert isinstance(result, MetadataResult)
        assert result.symbols == {"BTCUSDT", "ETHUSDT"}
        assert result.directions == {"LONG", "SHORT"}
        assert result.statuses == {"OPEN", "TP_HIT", "SL_HIT"}

    def test_empty_metadata(self, service, mock_trade_repo):
        """Handles empty trade list."""
        mock_trade_repo.find_all.return_value = []

        result = service.get_metadata()

        assert result.symbols == set()
        assert result.directions == set()
        assert result.statuses == set()

    def test_single_trade(self, service, mock_trade_repo, sample_trade):
        """Handles single trade."""
        mock_trade_repo.find_all.return_value = [sample_trade]

        result = service.get_metadata()

        assert result.symbols == {"BTCUSDT"}
        assert result.directions == {"LONG"}
        assert result.statuses == {"OPEN"}


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_repository_exception_propagates(self, service, mock_trade_repo):
        """Repository exceptions propagate to caller."""
        mock_trade_repo.find_all.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            service.get_trade_list()

    def test_negative_pagination_parameters(self, service, mock_trade_repo):
        """Accepts negative pagination (handled by repository)."""
        mock_trade_repo.find_all.return_value = []
        mock_trade_repo.count.return_value = 0

        result = service.get_trade_list(limit=-10, offset=-5)

        mock_trade_repo.find_all.assert_called_once()
        assert result.limit == -10
        assert result.offset == -5
