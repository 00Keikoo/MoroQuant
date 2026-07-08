"""Service layer for trade explorer queries.

Orchestrates repository calls for trade list, detail, summary, and metadata.
NO analytics. NO SQL. Only repository orchestration.
"""

from typing import List, Optional, Set
from dataclasses import dataclass

from ml_service.repositories.trade_repository import TradeRepository, TradePosition
from ml_service.repositories.signal_repository import SignalRepository, Signal
from ml_service.repositories.equity_repository import EquityRepository, PaperAccount
from ml_service.analytics import TradeAnalyticsResult, calculate_trade_analytics


@dataclass
class TradeWithSignal:
    """Trade position with its linked signal."""
    trade: TradePosition
    signal: Optional[Signal]


@dataclass
class TradeListResult:
    """Paginated trade list with metadata."""
    trades: List[TradePosition]
    total: int
    limit: int
    offset: int


@dataclass
class MetadataResult:
    """Available filter values."""
    symbols: Set[str]
    directions: Set[str]
    statuses: Set[str]


class ExplorerQueryService:
    """Orchestrates repositories for trade explorer queries."""

    def __init__(
        self,
        trade_repository: TradeRepository,
        signal_repository: SignalRepository,
        equity_repository: EquityRepository
    ):
        self.trade_repo = trade_repository
        self.signal_repo = signal_repository
        self.equity_repo = equity_repository

    def get_trade_list(
        self,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        direction: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "opened_at",
        sort_order: str = "DESC"
    ) -> TradeListResult:
        """Query trades with filtering, pagination, and sorting.

        Args:
            status: Filter by position status
            symbol: Filter by trading symbol
            direction: Filter by direction
            limit: Maximum results
            offset: Results to skip
            sort_by: Column to sort by
            sort_order: Sort order (ASC or DESC)

        Returns:
            TradeListResult with trades and pagination metadata
        """
        trades = self.trade_repo.find_all(
            status=status,
            symbol=symbol,
            direction=direction,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )

        total = self.trade_repo.count(
            status=status,
            symbol=symbol,
            direction=direction
        )

        return TradeListResult(
            trades=trades,
            total=total,
            limit=limit,
            offset=offset
        )

    def get_trade_detail(self, trade_id: int) -> Optional[TradeWithSignal]:
        """Get trade with linked signal.

        Args:
            trade_id: Trade position ID

        Returns:
            TradeWithSignal if trade exists, None otherwise
        """
        trade = self.trade_repo.find_by_id(trade_id)
        if not trade:
            return None

        signal = None
        if trade.signal_id:
            signal = self.signal_repo.find_by_id(trade.signal_id)

        return TradeWithSignal(trade=trade, signal=signal)

    def get_summary(self) -> TradeAnalyticsResult:
        """Calculate trade analytics by delegating to TradeAnalytics.

        Returns:
            TradeAnalyticsResult with calculated metrics
        """
        all_trades = self.trade_repo.find_all(limit=10000)
        return calculate_trade_analytics(all_trades)

    def get_metadata(self) -> MetadataResult:
        """Get available filter values from all trades.

        Returns:
            MetadataResult with unique symbols, directions, and statuses
        """
        all_trades = self.trade_repo.find_all(limit=10000)

        symbols = {t.symbol for t in all_trades}
        directions = {t.direction for t in all_trades}
        statuses = {t.status for t in all_trades}

        return MetadataResult(
            symbols=symbols,
            directions=directions,
            statuses=statuses
        )
