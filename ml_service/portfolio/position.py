"""
Position Engine - Responsible for position lifecycle management

Implements pure functional position operations:
- Opening positions
- Updating positions (increase/reduce)
- Closing positions
- PnL calculations (realized and unrealized)
- Long/short direction handling
- Spot/futures separation

All operations return new immutable Position objects and domain events.
"""

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Optional, Tuple
from ml_service.portfolio.models import (
    Position,
    PositionType,
    PositionLifecycle,
    PositionMarginContext,
)


@dataclass(frozen=True)
class PositionOpened:
    position_id: str
    timestamp: datetime
    quantity: float
    average_entry_price: float
    position_type: PositionType


@dataclass(frozen=True)
class PositionUpdated:
    position_id: str
    timestamp: datetime
    quantity: float
    average_entry_price: float
    realized_pnl: float


@dataclass(frozen=True)
class PositionClosed:
    position_id: str
    timestamp: datetime
    quantity: float
    average_entry_price: float
    realized_pnl: float


class PositionService:
    """
    Position Engine implementing pure functional position operations.
    All methods return new immutable Position objects and domain events.
    """

    @staticmethod
    def open_position(
        symbol: str,
        position_type: PositionType,
        quantity: float,
        entry_price: float,
        timestamp: datetime,
        margin_context: Optional[PositionMarginContext] = None,
    ) -> Tuple[Position, PositionOpened]:
        """
        Open a new position.

        Args:
            symbol: Trading symbol
            position_type: SPOT, MARGIN, or FUTURES
            quantity: Position quantity (positive for LONG, negative for SHORT)
            entry_price: Entry price
            timestamp: Position open timestamp
            margin_context: Required for MARGIN/FUTURES positions

        Returns:
            Tuple of (new Position, PositionOpened event)

        Raises:
            ValueError: If validation fails
        """
        PositionService._validate_open(
            position_type, quantity, entry_price, margin_context
        )

        margin_required = 0.0
        if margin_context:
            margin_required = margin_context.allocated_margin

        position = Position(
            symbol=symbol,
            position_type=position_type,
            status=PositionLifecycle.OPEN,
            quantity=quantity,
            average_entry_price=entry_price,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=margin_required,
            margin_context=margin_context,
            opened_at=timestamp,
            updated_at=timestamp,
        )

        event = PositionOpened(
            position_id=symbol,
            timestamp=timestamp,
            quantity=quantity,
            average_entry_price=entry_price,
            position_type=position_type,
        )

        return position, event

    @staticmethod
    def increase_position(
        position: Position,
        quantity: float,
        execution_price: float,
        timestamp: datetime,
    ) -> Tuple[Position, PositionUpdated]:
        """
        Increase an existing position (add to position size).

        Recalculates average entry price:
        new_avg = (old_qty * old_avg + new_qty * exec_price) / total_qty

        Args:
            position: Existing position
            quantity: Additional quantity (same sign as position.quantity)
            execution_price: Execution price for the increase
            timestamp: Update timestamp

        Returns:
            Tuple of (new Position, PositionUpdated event)

        Raises:
            ValueError: If validation fails
        """
        PositionService._validate_increase(position, quantity, execution_price)

        old_quantity = position.quantity
        old_average = position.average_entry_price

        new_quantity = old_quantity + quantity

        new_average_entry = (
            old_quantity * old_average + quantity * execution_price
        ) / new_quantity

        new_position = replace(
            position,
            quantity=new_quantity,
            average_entry_price=new_average_entry,
            updated_at=timestamp,
        )

        event = PositionUpdated(
            position_id=position.symbol,
            timestamp=timestamp,
            quantity=new_quantity,
            average_entry_price=new_average_entry,
            realized_pnl=0.0,
        )

        return new_position, event

    @staticmethod
    def reduce_position(
        position: Position,
        quantity: float,
        exit_price: float,
        timestamp: datetime,
    ) -> Tuple[Position, PositionUpdated]:
        """
        Reduce an existing position (partial close).

        Calculates realized PnL for the closed portion.
        Average entry price remains unchanged.

        Args:
            position: Existing position
            quantity: Quantity to reduce (absolute value, will be adjusted for direction)
            exit_price: Exit price for the reduction
            timestamp: Update timestamp

        Returns:
            Tuple of (new Position, PositionUpdated event)

        Raises:
            ValueError: If validation fails
        """
        PositionService._validate_reduce(position, quantity, exit_price)

        is_long = position.quantity > 0
        reduction_quantity = abs(quantity)

        if reduction_quantity > abs(position.quantity):
            raise ValueError(
                f"Cannot reduce position by {reduction_quantity}: "
                f"only {abs(position.quantity)} available"
            )

        realized_pnl = PositionService.calculate_realized_pnl(
            position, exit_price, reduction_quantity
        )

        new_quantity = position.quantity - (
            reduction_quantity if is_long else -reduction_quantity
        )
        new_realized_pnl = position.realized_pnl + realized_pnl

        status = (
            PositionLifecycle.PARTIALLY_CLOSED
            if abs(new_quantity) > 0
            else PositionLifecycle.CLOSED
        )

        new_position = replace(
            position,
            quantity=new_quantity,
            realized_pnl=new_realized_pnl,
            status=status,
            updated_at=timestamp,
        )

        event = PositionUpdated(
            position_id=position.symbol,
            timestamp=timestamp,
            quantity=new_quantity,
            average_entry_price=position.average_entry_price,
            realized_pnl=realized_pnl,
        )

        return new_position, event

    @staticmethod
    def close_position(
        position: Position,
        exit_price: float,
        timestamp: datetime,
    ) -> Tuple[Position, PositionClosed]:
        """
        Close an entire position.

        Calculates final realized PnL.

        Args:
            position: Existing position
            exit_price: Final exit price
            timestamp: Close timestamp

        Returns:
            Tuple of (closed Position, PositionClosed event)

        Raises:
            ValueError: If validation fails
        """
        PositionService._validate_close(position, exit_price)

        closing_quantity = abs(position.quantity)
        realized_pnl = PositionService.calculate_realized_pnl(
            position, exit_price, closing_quantity
        )

        total_realized_pnl = position.realized_pnl + realized_pnl

        closed_position = replace(
            position,
            quantity=0.0,
            realized_pnl=total_realized_pnl,
            average_exit_price=exit_price,
            unrealized_pnl=0.0,
            status=PositionLifecycle.CLOSED,
            updated_at=timestamp,
        )

        event = PositionClosed(
            position_id=position.symbol,
            timestamp=timestamp,
            quantity=0.0,
            average_entry_price=position.average_entry_price,
            realized_pnl=total_realized_pnl,
        )

        return closed_position, event

    @staticmethod
    def calculate_unrealized_pnl(
        position: Position,
        mark_price: float,
    ) -> float:
        """
        Calculate unrealized PnL for a position.

        LONG: (mark_price - entry_price) * quantity
        SHORT: (entry_price - mark_price) * abs(quantity)

        Args:
            position: Current position
            mark_price: Current mark price

        Returns:
            Unrealized PnL value
        """
        if mark_price <= 0:
            raise ValueError(f"mark_price must be positive: {mark_price}")

        if position.quantity == 0:
            return 0.0

        is_long = position.quantity > 0

        if is_long:
            unrealized_pnl = (mark_price - position.average_entry_price) * position.quantity
        else:
            unrealized_pnl = (position.average_entry_price - mark_price) * abs(position.quantity)

        return unrealized_pnl

    @staticmethod
    def calculate_realized_pnl(
        position: Position,
        exit_price: float,
        quantity: float,
    ) -> float:
        """
        Calculate realized PnL for closing a portion of a position.

        LONG: (exit_price - entry_price) * quantity
        SHORT: (entry_price - exit_price) * quantity

        Args:
            position: Current position
            exit_price: Exit price
            quantity: Quantity being closed (absolute value)

        Returns:
            Realized PnL value
        """
        if exit_price <= 0:
            raise ValueError(f"exit_price must be positive: {exit_price}")

        if quantity <= 0:
            raise ValueError(f"quantity must be positive: {quantity}")

        is_long = position.quantity > 0

        if is_long:
            realized_pnl = (exit_price - position.average_entry_price) * quantity
        else:
            realized_pnl = (position.average_entry_price - exit_price) * quantity

        return realized_pnl

    @staticmethod
    def _validate_open(
        position_type: PositionType,
        quantity: float,
        entry_price: float,
        margin_context: Optional[PositionMarginContext],
    ) -> None:
        """Validate position opening parameters."""
        if quantity == 0:
            raise ValueError("quantity cannot be zero")

        if entry_price <= 0:
            raise ValueError(f"entry_price must be positive: {entry_price}")

        if position_type in (PositionType.MARGIN, PositionType.FUTURES):
            if margin_context is None:
                raise ValueError(
                    f"margin_context required for {position_type} positions"
                )

        if position_type == PositionType.SPOT:
            if margin_context is not None:
                raise ValueError("margin_context must be None for SPOT positions")
            if quantity < 0:
                raise ValueError("SPOT positions cannot be SHORT (quantity must be positive)")

    @staticmethod
    def _validate_increase(
        position: Position,
        quantity: float,
        execution_price: float,
    ) -> None:
        """Validate position increase parameters."""
        if quantity == 0:
            raise ValueError("quantity cannot be zero")

        if execution_price <= 0:
            raise ValueError(f"execution_price must be positive: {execution_price}")

        if position.status == PositionLifecycle.CLOSED:
            raise ValueError("Cannot increase a CLOSED position")

        is_position_long = position.quantity > 0
        is_increase_long = quantity > 0

        if is_position_long != is_increase_long:
            raise ValueError(
                f"Increase quantity direction must match position direction: "
                f"position={position.quantity}, increase={quantity}"
            )

    @staticmethod
    def _validate_reduce(
        position: Position,
        quantity: float,
        exit_price: float,
    ) -> None:
        """Validate position reduction parameters."""
        if quantity <= 0:
            raise ValueError(f"quantity must be positive: {quantity}")

        if exit_price <= 0:
            raise ValueError(f"exit_price must be positive: {exit_price}")

        if position.status == PositionLifecycle.CLOSED:
            raise ValueError("Cannot reduce a CLOSED position")

        if quantity > abs(position.quantity):
            raise ValueError(
                f"Cannot reduce position by {quantity}: "
                f"only {abs(position.quantity)} available"
            )

    @staticmethod
    def _validate_close(
        position: Position,
        exit_price: float,
    ) -> None:
        """Validate position close parameters."""
        if exit_price <= 0:
            raise ValueError(f"exit_price must be positive: {exit_price}")

        if position.status == PositionLifecycle.CLOSED:
            raise ValueError("Position is already CLOSED")
