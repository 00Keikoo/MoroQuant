"""Repository for Execution Analytics Platform data access."""

from typing import List, Optional
from datetime import datetime

from ml_service.repositories.database import get_connection
from ml_service.analytics.execution_analytics.types import (
    ExecutionDecisionRecord,
    TradePositionRecord,
    SignalRecord,
)


class ExecutionAnalyticsRepository:
    """Repository for querying execution analytics data."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse timestamp string to datetime."""
        if timestamp_str is None:
            return None
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None

    def get_execution_decisions(
        self,
        source: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        symbol: Optional[str] = None,
        decision: Optional[str] = None,
    ) -> List[ExecutionDecisionRecord]:
        """Retrieve execution decisions with optional filters.

        Args:
            source: Source filter ('PAPER', 'LIVE', 'BACKTEST', 'RESEARCH')
            start_time: Optional start time filter
            end_time: Optional end time filter
            symbol: Optional symbol filter
            decision: Optional decision filter ('ACCEPTED', 'REJECTED')

        Returns:
            List of ExecutionDecisionRecord objects
        """
        query = """
            SELECT
                id, symbol, direction, decision, reason, reason_detail,
                signal_id, position_id, confidence, regime, timeframe,
                execution_edge, signal_price, execution_price, slippage_pct,
                execution_latency_ms, created_at, source, execution_policy
            FROM execution_decisions
            WHERE source = ?
        """
        params = [source]

        if start_time is not None:
            query += " AND created_at >= ?"
            params.append(start_time.isoformat())

        if end_time is not None:
            query += " AND created_at <= ?"
            params.append(end_time.isoformat())

        if symbol is not None:
            query += " AND symbol = ?"
            params.append(symbol)

        if decision is not None:
            query += " AND decision = ?"
            params.append(decision)

        query += " ORDER BY created_at DESC"

        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_execution_decision(row) for row in rows]
        finally:
            conn.close()

    def _row_to_execution_decision(self, row) -> ExecutionDecisionRecord:
        """Convert database row to ExecutionDecisionRecord."""
        created_at = self._parse_timestamp(row['created_at'])
        if created_at is None:
            created_at = datetime.now()

        return ExecutionDecisionRecord(
            id=row['id'],
            symbol=row['symbol'],
            direction=row['direction'],
            decision=row['decision'],
            reason=row['reason'],
            reason_detail=row['reason_detail'],
            signal_id=row['signal_id'],
            position_id=row['position_id'],
            confidence=row['confidence'],
            regime=row['regime'],
            timeframe=row['timeframe'],
            execution_edge=row['execution_edge'],
            signal_price=row['signal_price'],
            execution_price=row['execution_price'],
            slippage_pct=row['slippage_pct'],
            execution_latency_ms=row['execution_latency_ms'],
            created_at=created_at,
            source=row['source'],
            execution_policy=row['execution_policy'],
        )

    def get_paper_positions(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[TradePositionRecord]:
        """Retrieve paper positions with optional filters.

        Args:
            start_time: Optional start time filter (opened_at)
            end_time: Optional end time filter (opened_at)
            symbol: Optional symbol filter
            status: Optional status filter

        Returns:
            List of TradePositionRecord objects
        """
        query = """
            SELECT
                id, symbol, direction, entry_price, current_price, size_usdt, qty,
                stop_loss, take_profit, status, realized_pnl, opened_at, closed_at,
                confidence, regime, timeframe, execution_edge, mae, mfe,
                final_exit_reason, execution_policy, signal_price, execution_price,
                slippage_pct, execution_latency_ms
            FROM paper_positions
            WHERE 1=1
        """
        params = []

        if start_time is not None:
            query += " AND opened_at >= ?"
            params.append(start_time.isoformat())

        if end_time is not None:
            query += " AND opened_at <= ?"
            params.append(end_time.isoformat())

        if symbol is not None:
            query += " AND symbol = ?"
            params.append(symbol)

        if status is not None:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY opened_at DESC"

        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_position(row) for row in rows]
        finally:
            conn.close()

    def _row_to_position(self, row) -> TradePositionRecord:
        """Convert database row to TradePositionRecord."""
        opened_at = self._parse_timestamp(row['opened_at'])
        if opened_at is None:
            opened_at = datetime.now()

        closed_at = self._parse_timestamp(row['closed_at'])

        return TradePositionRecord(
            id=row['id'],
            symbol=row['symbol'],
            direction=row['direction'],
            entry_price=row['entry_price'],
            current_price=row['current_price'],
            size_usdt=row['size_usdt'],
            qty=row['qty'],
            stop_loss=row['stop_loss'],
            take_profit=row['take_profit'],
            status=row['status'],
            realized_pnl=row['realized_pnl'],
            opened_at=opened_at,
            closed_at=closed_at,
            confidence=row['confidence'],
            regime=row['regime'],
            timeframe=row['timeframe'],
            execution_edge=row['execution_edge'],
            mae=row['mae'] if row['mae'] is not None else 0.0,
            mfe=row['mfe'] if row['mfe'] is not None else 0.0,
            final_exit_reason=row['final_exit_reason'],
            execution_policy=row['execution_policy'] if row['execution_policy'] else 'FIXED_SL',
            signal_price=row['signal_price'],
            execution_price=row['execution_price'],
            slippage_pct=row['slippage_pct'],
            execution_latency_ms=row['execution_latency_ms'],
        )

    def get_signals(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        symbol: Optional[str] = None,
    ) -> List[SignalRecord]:
        """Retrieve signals with optional filters.

        Args:
            start_time: Optional start time filter (created_at)
            end_time: Optional end time filter (created_at)
            symbol: Optional symbol filter

        Returns:
            List of SignalRecord objects
        """
        query = """
            SELECT
                id, symbol, timeframe, timestamp, direction, confidence,
                created_at, regime, entry_price
            FROM signals
            WHERE 1=1
        """
        params = []

        if start_time is not None:
            query += " AND created_at >= ?"
            params.append(start_time.isoformat())

        if end_time is not None:
            query += " AND created_at <= ?"
            params.append(end_time.isoformat())

        if symbol is not None:
            query += " AND symbol = ?"
            params.append(symbol)

        query += " ORDER BY created_at DESC"

        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_signal(row) for row in rows]
        finally:
            conn.close()

    def _row_to_signal(self, row) -> SignalRecord:
        """Convert database row to SignalRecord."""
        created_at = self._parse_timestamp(row['created_at'])
        if created_at is None:
            created_at = datetime.now()

        return SignalRecord(
            id=row['id'],
            symbol=row['symbol'],
            timeframe=row['timeframe'],
            timestamp=row['timestamp'],
            direction=row['direction'],
            confidence=row['confidence'],
            created_at=created_at,
            regime=row['regime'],
            entry_price=row['entry_price'],
        )

    def count_execution_decisions(
        self,
        source: str,
        decision: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """Count execution decisions matching filters.

        Args:
            source: Source filter ('PAPER', 'LIVE', 'BACKTEST', 'RESEARCH')
            decision: Optional decision filter ('ACCEPTED', 'REJECTED')
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            Count of matching execution decisions
        """
        query = "SELECT COUNT(*) as count FROM execution_decisions WHERE source = ?"
        params = [source]

        if decision is not None:
            query += " AND decision = ?"
            params.append(decision)

        if start_time is not None:
            query += " AND created_at >= ?"
            params.append(start_time.isoformat())

        if end_time is not None:
            query += " AND created_at <= ?"
            params.append(end_time.isoformat())

        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(query, params)
            return cursor.fetchone()['count']
        finally:
            conn.close()
