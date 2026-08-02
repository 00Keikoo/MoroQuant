"""
Tests for Slippage Models
"""

import pytest
from datetime import datetime

from ml_service.simulation.execution.slippage import (
    ISlippageModel,
    FixedSlippageModel,
)
from ml_service.simulation.execution.execution_models import (
    ExecutionRequest,
    ExecutionOrder,
    ExecutionLifecycle,
    OrderType,
    ExecutionPolicy,
    FillPolicy,
)
from ml_service.simulation.models import MarketSnapshot


def create_test_order():
    """Helper to create test order"""
    req = ExecutionRequest(
        symbol="BTCUSDT",
        side="BUY",
        order_type=OrderType.MARKET,
        quantity=1.0,
        price=None,
        execution_policy=ExecutionPolicy.GTC,
        fill_policy=FillPolicy.FULL_FILL,
    )

    return ExecutionOrder(
        order_id="order-123",
        request=req,
        status=ExecutionLifecycle.VALIDATED,
        cumulative_filled_qty=0.0,
        average_filled_price=0.0,
        active_price=None,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 1, 12, 0, 1),
    )


def create_test_snapshot(mid_price=50000.0):
    """Helper to create test snapshot"""
    return MarketSnapshot(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        symbol="BTCUSDT",
        mid_price=mid_price,
        bid=49995.0,
        ask=50005.0,
        spread=10.0,
        volume=1000.0,
    )


def test_fixed_slippage_model_creation():
    """Test FixedSlippageModel creation"""
    model = FixedSlippageModel(fixed_bps=5.0)
    assert model.fixed_bps == 5.0


def test_fixed_slippage_model_negative_bps():
    """Test FixedSlippageModel rejects negative bps"""
    with pytest.raises(ValueError, match="fixed_bps must be non-negative"):
        FixedSlippageModel(fixed_bps=-1.0)


def test_fixed_slippage_calculation():
    """Test fixed slippage calculation"""
    model = FixedSlippageModel(fixed_bps=5.0)
    order = create_test_order()
    snapshot = create_test_snapshot(mid_price=50000.0)

    slippage = model.calculate_slippage(order, snapshot)

    expected = 50000.0 * (5.0 / 10000.0)
    assert slippage == expected
    assert slippage == 25.0


def test_fixed_slippage_zero_bps():
    """Test fixed slippage with zero bps"""
    model = FixedSlippageModel(fixed_bps=0.0)
    order = create_test_order()
    snapshot = create_test_snapshot(mid_price=50000.0)

    slippage = model.calculate_slippage(order, snapshot)
    assert slippage == 0.0


def test_fixed_slippage_different_prices():
    """Test fixed slippage scales with price"""
    model = FixedSlippageModel(fixed_bps=10.0)
    order = create_test_order()

    snapshot_low = create_test_snapshot(mid_price=10000.0)
    slippage_low = model.calculate_slippage(order, snapshot_low)

    snapshot_high = create_test_snapshot(mid_price=100000.0)
    slippage_high = model.calculate_slippage(order, snapshot_high)

    assert slippage_high > slippage_low
    assert slippage_low == 10.0
    assert slippage_high == 100.0


def test_islippage_model_is_abstract():
    """Test ISlippageModel cannot be instantiated"""
    with pytest.raises(TypeError):
        ISlippageModel()
