"""
Test suite for Position Engine

Validates:
- Position lifecycle operations (open, increase, reduce, close)
- PnL calculations (realized and unrealized)
- Long/short position handling
- Spot/futures/margin position types
- Average entry price calculations
- Immutability guarantees
- Validation rules
"""

import pytest
from datetime import datetime
from ml_service.portfolio.position import (
    PositionService,
    PositionOpened,
    PositionUpdated,
    PositionClosed,
)
from ml_service.portfolio.models import (
    Position,
    PositionType,
    PositionLifecycle,
    PositionMarginContext,
)


class TestOpenPosition:
    """Test position opening operations."""

    def test_open_long_spot_position(self):
        """Test opening a long spot position."""
        position, event = PositionService.open_position(
            symbol="BTC/USDT",
            position_type=PositionType.SPOT,
            quantity=1.0,
            entry_price=50000.0,
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
            margin_context=None,
        )

        assert position.symbol == "BTC/USDT"
        assert position.position_type == PositionType.SPOT
        assert position.status == PositionLifecycle.OPEN
        assert position.quantity == 1.0
        assert position.average_entry_price == 50000.0
        assert position.unrealized_pnl == 0.0
        assert position.realized_pnl == 0.0
        assert position.margin_context is None
        assert position.margin_required == 0.0

        assert isinstance(event, PositionOpened)
        assert event.position_id == "BTC/USDT"
        assert event.quantity == 1.0
        assert event.average_entry_price == 50000.0

    def test_open_futures_long_position(self):
        """Test opening a futures long position with leverage."""
        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0,
        )

        position, event = PositionService.open_position(
            symbol="BTC/USDT",
            position_type=PositionType.FUTURES,
            quantity=1.0,
            entry_price=10000.0,
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
            margin_context=margin_context,
        )

        assert position.position_type == PositionType.FUTURES
        assert position.quantity == 1.0
        assert position.average_entry_price == 10000.0
        assert position.margin_context == margin_context
        assert position.margin_required == 1000.0

    def test_open_short_position(self):
        """Test opening a short futures position."""
        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0,
        )

        position, event = PositionService.open_position(
            symbol="BTC/USDT",
            position_type=PositionType.FUTURES,
            quantity=-1.0,
            entry_price=10000.0,
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
            margin_context=margin_context,
        )

        assert position.quantity == -1.0
        assert position.average_entry_price == 10000.0

    def test_open_position_requires_margin_context_for_futures(self):
        """Test that futures positions require margin context."""
        with pytest.raises(ValueError, match="margin_context required"):
            PositionService.open_position(
                symbol="BTC/USDT",
                position_type=PositionType.FUTURES,
                quantity=1.0,
                entry_price=10000.0,
                timestamp=datetime(2026, 1, 1),
                margin_context=None,
            )

    def test_open_position_rejects_margin_context_for_spot(self):
        """Test that spot positions cannot have margin context."""
        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0,
        )

        with pytest.raises(ValueError, match="margin_context must be None for SPOT"):
            PositionService.open_position(
                symbol="BTC/USDT",
                position_type=PositionType.SPOT,
                quantity=1.0,
                entry_price=10000.0,
                timestamp=datetime(2026, 1, 1),
                margin_context=margin_context,
            )

    def test_open_position_rejects_zero_quantity(self):
        """Test that opening with zero quantity is rejected."""
        with pytest.raises(ValueError, match="quantity cannot be zero"):
            PositionService.open_position(
                symbol="BTC/USDT",
                position_type=PositionType.SPOT,
                quantity=0.0,
                entry_price=10000.0,
                timestamp=datetime(2026, 1, 1),
            )

    def test_open_position_rejects_negative_price(self):
        """Test that negative prices are rejected."""
        with pytest.raises(ValueError, match="entry_price must be positive"):
            PositionService.open_position(
                symbol="BTC/USDT",
                position_type=PositionType.SPOT,
                quantity=1.0,
                entry_price=-10000.0,
                timestamp=datetime(2026, 1, 1),
            )

    def test_open_spot_position_rejects_short(self):
        """Test that spot positions cannot be short."""
        with pytest.raises(ValueError, match="SPOT positions cannot be SHORT"):
            PositionService.open_position(
                symbol="BTC/USDT",
                position_type=PositionType.SPOT,
                quantity=-1.0,
                entry_price=10000.0,
                timestamp=datetime(2026, 1, 1),
            )


class TestIncreasePosition:
    """Test position increase operations and average entry calculation."""

    def test_increase_position_average_entry(self):
        """
        Test average entry price calculation when increasing position.

        Example from design doc:
        BTC LONG: 1 BTC @ 50000
        Add: 1 BTC @ 60000
        Average: 55000
        """
        position = Position(
            symbol="BTC/USDT",
            position_type=PositionType.SPOT,
            status=PositionLifecycle.OPEN,
            quantity=1.0,
            average_entry_price=50000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=0.0,
            margin_context=None,
            opened_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )

        new_position, event = PositionService.increase_position(
            position=position,
            quantity=1.0,
            execution_price=60000.0,
            timestamp=datetime(2026, 1, 2),
        )

        expected_avg = (1.0 * 50000.0 + 1.0 * 60000.0) / 2.0
        assert new_position.quantity == 2.0
        assert new_position.average_entry_price == expected_avg
        assert new_position.average_entry_price == 55000.0

        assert isinstance(event, PositionUpdated)
        assert event.quantity == 2.0
        assert event.average_entry_price == 55000.0

    def test_increase_short_position(self):
        """Test increasing a short position."""
        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0,
        )

        position = Position(
            symbol="BTC/USDT",
            position_type=PositionType.FUTURES,
            status=PositionLifecycle.OPEN,
            quantity=-1.0,
            average_entry_price=10000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=1000.0,
            margin_context=margin_context,
            opened_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )

        new_position, event = PositionService.increase_position(
            position=position,
            quantity=-1.0,
            execution_price=9000.0,
            timestamp=datetime(2026, 1, 2),
        )

        expected_avg = (1.0 * 10000.0 + 1.0 * 9000.0) / 2.0
        assert new_position.quantity == -2.0
        assert new_position.average_entry_price == expected_avg

    def test_increase_position_immutability(self):
        """Test that increase returns a new position and preserves the original."""
        position = Position(
            symbol="BTC/USDT",
            position_type=PositionType.SPOT,
            status=PositionLifecycle.OPEN,
            quantity=1.0,
            average_entry_price=50000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=0.0,
            margin_context=None,
            opened_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )

        original_quantity = position.quantity
        original_avg = position.average_entry_price

        new_position, _ = PositionService.increase_position(
            position=position,
            quantity=1.0,
            execution_price=60000.0,
            timestamp=datetime(2026, 1, 2),
        )

        assert position.quantity == original_quantity
        assert position.average_entry_price == original_avg
        assert new_position is not position
        assert new_position.quantity != position.quantity

    def test_increase_position_rejects_opposite_direction(self):
        """Test that increase rejects opposite direction quantity."""
        position = Position(
            symbol="BTC/USDT",
            position_type=PositionType.SPOT,
            status=PositionLifecycle.OPEN,
            quantity=1.0,
            average_entry_price=50000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=0.0,
            margin_context=None,
            opened_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )

        with pytest.raises(ValueError, match="direction must match"):
            PositionService.increase_position(
                position=position,
                quantity=-1.0,
                execution_price=60000.0,
                timestamp=datetime(2026, 1, 2),
            )


class TestReducePosition:
    """Test partial position close operations."""

    def test_partial_close_long(self):
        """
        Test partial close of long position.

        Example from design doc:
        LONG: 2 BTC @ 50000
        Close: 1 BTC @ 60000
        Realized PnL: 10000
        Remaining: 1 BTC @ 50000
        """
        position = Position(
            symbol="BTC/USDT",
            position_type=PositionType.SPOT,
            status=PositionLifecycle.OPEN,
            quantity=2.0,
            average_entry_price=50000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=0.0,
            margin_context=None,
            opened_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )

        new_position, event = PositionService.reduce_position(
            position=position,
            quantity=1.0,
            exit_price=60000.0,
            timestamp=datetime(2026, 1, 2),
        )

        assert new_position.quantity == 1.0
        assert new_position.average_entry_price == 50000.0
        assert new_position.realized_pnl == 10000.0
        assert new_position.status == PositionLifecycle.PARTIALLY_CLOSED

        assert isinstance(event, PositionUpdated)
        assert event.realized_pnl == 10000.0

    def test_partial_close_short(self):
        """
        Test partial close of short position.

        SHORT: -2 BTC @ 10000
        Close: 1 BTC @ 9000
        Realized PnL: (10000 - 9000) * 1 = 1000
        """
        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=2000.0,
        )

        position = Position(
            symbol="BTC/USDT",
            position_type=PositionType.FUTURES,
            status=PositionLifecycle.OPEN,
            quantity=-2.0,
            average_entry_price=10000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=2000.0,
            margin_context=margin_context,
            opened_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )

        new_position, event = PositionService.reduce_position(
            position=position,
            quantity=1.0,
            exit_price=9000.0,
            timestamp=datetime(2026, 1, 2),
        )

        assert new_position.quantity == -1.0
        assert new_position.average_entry_price == 10000.0
        assert new_position.realized_pnl == 1000.0

    def test_reduce_position_rejects_excessive_quantity(self):
        """Test that reducing more than available is rejected."""
        position = Position(
            symbol="BTC/USDT",
            position_type=PositionType.SPOT,
            status=PositionLifecycle.OPEN,
            quantity=1.0,
            average_entry_price=50000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=0.0,
            margin_context=None,
            opened_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )

        with pytest.raises(ValueError, match="Cannot reduce position by 2.0"):
            PositionService.reduce_position(
                position=position,
                quantity=2.0,
                exit_price=60000.0,
                timestamp=datetime(2026, 1, 2),
            )


class TestClosePosition:
    """Test full position close operations."""

    def test_full_close(self):
        """Test closing an entire position."""
        position = Position(
            symbol="BTC/USDT",
            position_type=PositionType.SPOT,
            status=PositionLifecycle.OPEN,
            quantity=1.0,
            average_entry_price=50000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=5000.0,
            margin_required=0.0,
            margin_context=None,
            opened_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )

        closed_position, event = PositionService.close_position(
            position=position,
            exit_price=60000.0,
            timestamp=datetime(2026, 1, 2),
        )

        assert closed_position.quantity == 0.0
        assert closed_position.status == PositionLifecycle.CLOSED
        assert closed_position.realized_pnl == 15000.0
        assert closed_position.unrealized_pnl == 0.0
        assert closed_position.average_exit_price == 60000.0

        assert isinstance(event, PositionClosed)
        assert event.realized_pnl == 15000.0

    def test_close_short_position(self):
        """Test closing a short position."""
        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0,
        )

        position = Position(
            symbol="BTC/USDT",
            position_type=PositionType.FUTURES,
            status=PositionLifecycle.OPEN,
            quantity=-1.0,
            average_entry_price=10000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=1000.0,
            margin_context=margin_context,
            opened_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )

        closed_position, event = PositionService.close_position(
            position=position,
            exit_price=9000.0,
            timestamp=datetime(2026, 1, 2),
        )

        assert closed_position.quantity == 0.0
        assert closed_position.status == PositionLifecycle.CLOSED
        assert closed_position.realized_pnl == 1000.0

    def test_close_position_rejects_already_closed(self):
        """Test that closing an already closed position is rejected."""
        position = Position(
            symbol="BTC/USDT",
            position_type=PositionType.SPOT,
            status=PositionLifecycle.CLOSED,
            quantity=0.0,
            average_entry_price=50000.0,
            average_exit_price=60000.0,
            unrealized_pnl=0.0,
            realized_pnl=10000.0,
            margin_required=0.0,
            margin_context=None,
            opened_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 2),
        )

        with pytest.raises(ValueError, match="already CLOSED"):
            PositionService.close_position(
                position=position,
                exit_price=60000.0,
                timestamp=datetime(2026, 1, 3),
            )


class TestRealizedPnL:
    """Test realized PnL calculations."""

    def test_realized_pnl_long_profit(self):
        """Test realized PnL for profitable long position."""
        position = Position(
            symbol="BTC/USDT",
            position_type=PositionType.SPOT,
            status=PositionLifecycle.OPEN,
            quantity=1.0,
            average_entry_price=50000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=0.0,
            margin_context=None,
            opened_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )

        pnl = PositionService.calculate_realized_pnl(
            position=position,
            exit_price=60000.0,
            quantity=1.0,
        )

        assert pnl == 10000.0

    def test_realized_pnl_long_loss(self):
        """Test realized PnL for losing long position."""
        position = Position(
            symbol="BTC/USDT",
            position_type=PositionType.SPOT,
            status=PositionLifecycle.OPEN,
            quantity=1.0,
            average_entry_price=50000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=0.0,
            margin_context=None,
            opened_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )

        pnl = PositionService.calculate_realized_pnl(
            position=position,
            exit_price=40000.0,
            quantity=1.0,
        )

        assert pnl == -10000.0

    def test_realized_pnl_short_profit(self):
        """Test realized PnL for profitable short position."""
        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0,
        )

        position = Position(
            symbol="BTC/USDT",
            position_type=PositionType.FUTURES,
            status=PositionLifecycle.OPEN,
            quantity=-1.0,
            average_entry_price=10000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=1000.0,
            margin_context=margin_context,
            opened_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )

        pnl = PositionService.calculate_realized_pnl(
            position=position,
            exit_price=9000.0,
            quantity=1.0,
        )

        assert pnl == 1000.0

    def test_realized_pnl_short_loss(self):
        """Test realized PnL for losing short position."""
        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0,
        )

        position = Position(
            symbol="BTC/USDT",
            position_type=PositionType.FUTURES,
            status=PositionLifecycle.OPEN,
            quantity=-1.0,
            average_entry_price=10000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=1000.0,
            margin_context=margin_context,
            opened_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )

        pnl = PositionService.calculate_realized_pnl(
            position=position,
            exit_price=11000.0,
            quantity=1.0,
        )

        assert pnl == -1000.0


class TestUnrealizedPnL:
    """Test unrealized PnL calculations."""

    def test_unrealized_pnl_long_profit(self):
        """Test unrealized PnL for long position in profit."""
        position = Position(
            symbol="BTC/USDT",
            position_type=PositionType.SPOT,
            status=PositionLifecycle.OPEN,
            quantity=1.0,
            average_entry_price=50000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=0.0,
            margin_context=None,
            opened_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )

        pnl = PositionService.calculate_unrealized_pnl(
            position=position,
            mark_price=60000.0,
        )

        assert pnl == 10000.0

    def test_unrealized_pnl_long_loss(self):
        """Test unrealized PnL for long position in loss."""
        position = Position(
            symbol="BTC/USDT",
            position_type=PositionType.SPOT,
            status=PositionLifecycle.OPEN,
            quantity=1.0,
            average_entry_price=50000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=0.0,
            margin_context=None,
            opened_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )

        pnl = PositionService.calculate_unrealized_pnl(
            position=position,
            mark_price=40000.0,
        )

        assert pnl == -10000.0

    def test_unrealized_pnl_short_profit(self):
        """Test unrealized PnL for short position in profit."""
        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0,
        )

        position = Position(
            symbol="BTC/USDT",
            position_type=PositionType.FUTURES,
            status=PositionLifecycle.OPEN,
            quantity=-1.0,
            average_entry_price=10000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=1000.0,
            margin_context=margin_context,
            opened_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )

        pnl = PositionService.calculate_unrealized_pnl(
            position=position,
            mark_price=9000.0,
        )

        assert pnl == 1000.0

    def test_unrealized_pnl_short_loss(self):
        """Test unrealized PnL for short position in loss."""
        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0,
        )

        position = Position(
            symbol="BTC/USDT",
            position_type=PositionType.FUTURES,
            status=PositionLifecycle.OPEN,
            quantity=-1.0,
            average_entry_price=10000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=1000.0,
            margin_context=margin_context,
            opened_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )

        pnl = PositionService.calculate_unrealized_pnl(
            position=position,
            mark_price=11000.0,
        )

        assert pnl == -1000.0

    def test_unrealized_pnl_zero_quantity(self):
        """Test unrealized PnL for closed position (zero quantity)."""
        position = Position(
            symbol="BTC/USDT",
            position_type=PositionType.SPOT,
            status=PositionLifecycle.CLOSED,
            quantity=0.0,
            average_entry_price=50000.0,
            average_exit_price=60000.0,
            unrealized_pnl=0.0,
            realized_pnl=10000.0,
            margin_required=0.0,
            margin_context=None,
            opened_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 2),
        )

        pnl = PositionService.calculate_unrealized_pnl(
            position=position,
            mark_price=70000.0,
        )

        assert pnl == 0.0
