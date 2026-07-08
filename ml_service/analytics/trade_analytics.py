"""Trade analytics calculation engine.

Pure functions that compute trading performance metrics from domain objects.
No database access, no side effects, no global state.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List

from ml_service.repositories.trade_repository import TradePosition


@dataclass
class TradeAnalyticsResult:
    """Calculated trading performance metrics."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    gross_profit: float
    gross_loss: float
    net_profit: float
    average_profit: float
    average_loss: float
    average_hold_duration_seconds: float
    average_trade_duration_seconds: float
    largest_win: float
    largest_loss: float
    long_count: int
    short_count: int
    open_count: int
    closed_count: int


def calculate_trade_analytics(trades: List[TradePosition]) -> TradeAnalyticsResult:
    """Calculate trading analytics from a list of TradePosition objects.

    Pure function with no side effects. All calculations operate on the provided
    trade list without accessing external state.

    Args:
        trades: List of TradePosition domain objects

    Returns:
        TradeAnalyticsResult containing calculated metrics

    Notes:
        - Win/loss metrics only include closed trades (status != "OPEN")
        - Duration calculations only include trades with valid closed_at timestamps
        - Empty list returns zero values for all metrics
    """
    if not trades:
        return _empty_result()

    total_trades = len(trades)
    open_count = sum(1 for t in trades if t.status == "OPEN")
    closed_count = total_trades - open_count

    long_count = sum(1 for t in trades if t.direction == "LONG")
    short_count = sum(1 for t in trades if t.direction == "SHORT")

    closed_trades = [t for t in trades if t.status != "OPEN"]

    winning_trades = sum(1 for t in closed_trades if t.realized_pnl > 0)
    losing_trades = sum(1 for t in closed_trades if t.realized_pnl < 0)

    profits = [t.realized_pnl for t in closed_trades if t.realized_pnl > 0]
    losses = [t.realized_pnl for t in closed_trades if t.realized_pnl < 0]

    gross_profit = sum(profits) if profits else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    net_profit = sum(t.realized_pnl for t in closed_trades)

    average_profit = gross_profit / winning_trades if winning_trades > 0 else 0.0
    average_loss = gross_loss / losing_trades if losing_trades > 0 else 0.0

    largest_win = max(profits) if profits else 0.0
    largest_loss = min(losses) if losses else 0.0

    win_rate = winning_trades / closed_count if closed_count > 0 else 0.0

    avg_hold_duration, avg_trade_duration = _calculate_durations(closed_trades)

    return TradeAnalyticsResult(
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=win_rate,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        net_profit=net_profit,
        average_profit=average_profit,
        average_loss=average_loss,
        average_hold_duration_seconds=avg_hold_duration,
        average_trade_duration_seconds=avg_trade_duration,
        largest_win=largest_win,
        largest_loss=largest_loss,
        long_count=long_count,
        short_count=short_count,
        open_count=open_count,
        closed_count=closed_count,
    )


def _calculate_durations(closed_trades: List[TradePosition]) -> tuple[float, float]:
    """Calculate average hold and trade durations for closed trades."""
    trades_with_times = [t for t in closed_trades if t.closed_at is not None]

    if not trades_with_times:
        return 0.0, 0.0

    durations = []
    for trade in trades_with_times:
        opened = datetime.fromisoformat(trade.opened_at)
        closed = datetime.fromisoformat(trade.closed_at)
        duration_seconds = (closed - opened).total_seconds()
        durations.append(duration_seconds)

    avg_duration = sum(durations) / len(durations)
    return avg_duration, avg_duration


def _empty_result() -> TradeAnalyticsResult:
    """Return zero-initialized analytics result for empty trade list."""
    return TradeAnalyticsResult(
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
        closed_count=0,
    )
