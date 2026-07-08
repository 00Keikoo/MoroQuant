"""Repository for querying paper trading positions."""

from typing import List, Optional, Any
from dataclasses import dataclass

from ml_service.repositories.database import get_connection


@dataclass
class TradePosition:
    """Represents a paper trading position."""
    id: int
    symbol: str
    direction: str
    entry_price: float
    current_price: Optional[float]
    size_usdt: float
    qty: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    signal_id: Optional[int]
    status: str
    realized_pnl: float
    opened_at: str
    closed_at: Optional[str]
    confidence: Optional[int]
    regime: Optional[str]
    timeframe: Optional[str]
    prob_short: Optional[float]
    prob_neutral: Optional[float]
    prob_long: Optional[float]
    execution_edge: Optional[float]
    skip_reason: Optional[str]
    mae: Optional[float]
    mfe: Optional[float]
    mae_timestamp: Optional[str]
    mfe_timestamp: Optional[str]
    profit_capture_ratio: Optional[float]
    final_exit_reason: Optional[str]
    trailing_stop_activated: Optional[int]
    sl_move_count: Optional[int]
    break_even_triggered: Optional[int]
    execution_policy: Optional[str]


class TradeRepository:
    """Repository for querying paper_positions table."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path

    def _row_to_position(self, row) -> TradePosition:
        """Convert database row to TradePosition."""
        return TradePosition(
            id=row['id'],
            symbol=row['symbol'],
            direction=row['direction'],
            entry_price=row['entry_price'],
            current_price=row['current_price'],
            size_usdt=row['size_usdt'],
            qty=row['qty'],
            stop_loss=row['stop_loss'],
            take_profit=row['take_profit'],
            signal_id=row['signal_id'],
            status=row['status'],
            realized_pnl=row['realized_pnl'],
            opened_at=row['opened_at'],
            closed_at=row['closed_at'],
            confidence=row['confidence'],
            regime=row['regime'],
            timeframe=row['timeframe'],
            prob_short=row['prob_short'],
            prob_neutral=row['prob_neutral'],
            prob_long=row['prob_long'],
            execution_edge=row['execution_edge'],
            skip_reason=row['skip_reason'],
            mae=row['mae'],
            mfe=row['mfe'],
            mae_timestamp=row['mae_timestamp'],
            mfe_timestamp=row['mfe_timestamp'],
            profit_capture_ratio=row['profit_capture_ratio'],
            final_exit_reason=row['final_exit_reason'],
            trailing_stop_activated=row['trailing_stop_activated'],
            sl_move_count=row['sl_move_count'],
            break_even_triggered=row['break_even_triggered'],
            execution_policy=row['execution_policy']
        )

    def find_all(
        self,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        direction: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "opened_at",
        sort_order: str = "DESC"
    ) -> List[TradePosition]:
        """Query paper_positions with filtering, pagination, and sorting.

        Args:
            status: Filter by position status (OPEN, TP_HIT, SL_HIT, EXPIRED, MANUAL_CLOSE)
            symbol: Filter by trading symbol
            direction: Filter by direction (LONG, SHORT)
            limit: Maximum number of results (1-10000)
            offset: Number of results to skip (must be non-negative)
            sort_by: Column to sort by
            sort_order: Sort order (ASC or DESC)

        Returns:
            List of TradePosition objects

        Raises:
            ValueError: If limit or offset are out of valid range
        """
        if limit < 1 or limit > 10000:
            raise ValueError(f"Limit must be between 1 and 10000, got {limit}")
        if offset < 0:
            raise ValueError(f"Offset must be non-negative, got {offset}")
        query = """
            SELECT
                id, symbol, direction, entry_price, current_price, size_usdt, qty,
                stop_loss, take_profit, signal_id, status, realized_pnl, opened_at, closed_at,
                confidence, regime, timeframe, prob_short, prob_neutral, prob_long,
                execution_edge, skip_reason, mae, mfe, mae_timestamp, mfe_timestamp,
                profit_capture_ratio, final_exit_reason, trailing_stop_activated,
                sl_move_count, break_even_triggered, execution_policy
            FROM paper_positions
            WHERE 1=1
        """
        params: List[Any] = []

        if status is not None:
            query += " AND status = ?"
            params.append(status)

        if symbol is not None:
            query += " AND symbol = ?"
            params.append(symbol)

        if direction is not None:
            query += " AND direction = ?"
            params.append(direction)

        allowed_sort_columns = {
            "id", "symbol", "direction", "entry_price", "size_usdt", "status",
            "realized_pnl", "opened_at", "closed_at", "confidence"
        }
        if sort_by not in allowed_sort_columns:
            sort_by = "opened_at"

        if sort_order.upper() not in ("ASC", "DESC"):
            sort_order = "DESC"

        query += f" ORDER BY {sort_by} {sort_order.upper()}"
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(query, params)
            return [self._row_to_position(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def find_by_id(self, position_id: int) -> Optional[TradePosition]:
        """Find a single position by ID.

        Args:
            position_id: Position ID (must be positive)

        Returns:
            TradePosition if found, None otherwise

        Raises:
            ValueError: If position_id is not positive
        """
        if position_id < 1:
            raise ValueError(f"Position ID must be positive, got {position_id}")
        query = """
            SELECT
                id, symbol, direction, entry_price, current_price, size_usdt, qty,
                stop_loss, take_profit, signal_id, status, realized_pnl, opened_at, closed_at,
                confidence, regime, timeframe, prob_short, prob_neutral, prob_long,
                execution_edge, skip_reason, mae, mfe, mae_timestamp, mfe_timestamp,
                profit_capture_ratio, final_exit_reason, trailing_stop_activated,
                sl_move_count, break_even_triggered, execution_policy
            FROM paper_positions
            WHERE id = ?
        """

        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(query, (position_id,))
            row = cursor.fetchone()
            return self._row_to_position(row) if row else None
        finally:
            conn.close()

    def find_by_signal_id(self, signal_id: int) -> List[TradePosition]:
        """Find all positions associated with a signal.

        Args:
            signal_id: Signal ID (must be positive)

        Returns:
            List of TradePosition objects

        Raises:
            ValueError: If signal_id is not positive
        """
        if signal_id < 1:
            raise ValueError(f"Signal ID must be positive, got {signal_id}")
        query = """
            SELECT
                id, symbol, direction, entry_price, current_price, size_usdt, qty,
                stop_loss, take_profit, signal_id, status, realized_pnl, opened_at, closed_at,
                confidence, regime, timeframe, prob_short, prob_neutral, prob_long,
                execution_edge, skip_reason, mae, mfe, mae_timestamp, mfe_timestamp,
                profit_capture_ratio, final_exit_reason, trailing_stop_activated,
                sl_move_count, break_even_triggered, execution_policy
            FROM paper_positions
            WHERE signal_id = ?
            ORDER BY opened_at DESC
        """

        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(query, (signal_id,))
            return [self._row_to_position(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def count(
        self,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        direction: Optional[str] = None
    ) -> int:
        """Count positions matching the given filters.

        Args:
            status: Filter by position status
            symbol: Filter by trading symbol
            direction: Filter by direction

        Returns:
            Count of matching positions
        """
        query = "SELECT COUNT(*) as count FROM paper_positions WHERE 1=1"
        params: List[Any] = []

        if status is not None:
            query += " AND status = ?"
            params.append(status)

        if symbol is not None:
            query += " AND symbol = ?"
            params.append(symbol)

        if direction is not None:
            query += " AND direction = ?"
            params.append(direction)

        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(query, params)
            return cursor.fetchone()['count']
        finally:
            conn.close()
