"""
Portfolio Adapter

Receives ExecutionFill events and forwards to PortfolioService.
Creates portfolio snapshots and exposes current portfolio state.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple

from ml_service.portfolio.models import Portfolio, PositionType, PositionMarginContext
from ml_service.portfolio.service import FillEvent, PortfolioService
from ml_service.portfolio.snapshot import PortfolioSnapshot, PortfolioSnapshotService
from ml_service.simulation.execution.execution_models import ExecutionFill


@dataclass(frozen=True)
class PortfolioAdapterResult:
    """Result of applying a fill to the portfolio."""
    portfolio: Portfolio
    snapshot: PortfolioSnapshot
    events: List[object]


class PortfolioAdapter:
    """
    Adapter connecting execution fills to portfolio updates.

    Responsibilities:
    - Convert ExecutionFill to FillEvent
    - Apply fills to portfolio via PortfolioService
    - Create snapshots after each fill
    - Maintain immutable state transitions
    """

    def __init__(
        self,
        portfolio_service: PortfolioService,
        snapshot_service: PortfolioSnapshotService,
    ):
        self.portfolio_service = portfolio_service
        self.snapshot_service = snapshot_service

    def apply_fill(
        self,
        portfolio: Portfolio,
        fill_event: ExecutionFill,
        position_type: PositionType = PositionType.FUTURES,
        leverage: float = 10.0,
    ) -> PortfolioAdapterResult:
        """
        Apply an execution fill to the portfolio.

        Args:
            portfolio: Current portfolio state
            fill_event: Execution fill from simulator
            position_type: Position type (SPOT, MARGIN, FUTURES)
            leverage: Leverage for margin/futures positions (default 10x)

        Returns:
            PortfolioAdapterResult with updated portfolio and snapshot
        """
        margin_context = None
        if position_type in (PositionType.MARGIN, PositionType.FUTURES):
            initial_margin_ratio = 1.0 / leverage
            maintenance_margin_ratio = initial_margin_ratio * 0.5

            notional_value = abs(fill_event.quantity) * fill_event.price
            allocated_margin = notional_value * initial_margin_ratio

            margin_context = PositionMarginContext(
                leverage=leverage,
                initial_margin_ratio=initial_margin_ratio,
                maintenance_margin_ratio=maintenance_margin_ratio,
                allocated_margin=allocated_margin,
            )

        portfolio_fill = FillEvent(
            symbol=fill_event.symbol,
            position_type=position_type,
            quantity=fill_event.quantity if fill_event.side == "BUY" else -fill_event.quantity,
            execution_price=fill_event.price,
            fee_amount=fill_event.commission,
            timestamp=fill_event.executed_at,
            margin_context=margin_context,
        )

        updated_portfolio, events = self.portfolio_service.apply_fill(
            portfolio, portfolio_fill
        )

        snapshot, snapshot_event = self.snapshot_service.create_snapshot(
            updated_portfolio, fill_event.executed_at
        )
        events.append(snapshot_event)

        return PortfolioAdapterResult(
            portfolio=updated_portfolio,
            snapshot=snapshot,
            events=events,
        )

    def snapshot(
        self,
        portfolio: Portfolio,
        timestamp: datetime,
    ) -> Tuple[PortfolioSnapshot, object]:
        """
        Create a portfolio snapshot at the given timestamp.

        Args:
            portfolio: Current portfolio state
            timestamp: Snapshot timestamp

        Returns:
            Tuple of (PortfolioSnapshot, SnapshotCreated event)
        """
        return self.snapshot_service.create_snapshot(portfolio, timestamp)
