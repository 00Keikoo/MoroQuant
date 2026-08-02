"""
Tests for Matching Engine
"""

import pytest
from datetime import datetime

from ml_service.simulation.execution.matching_engine import MatchingEngine
from ml_service.simulation.execution.execution_models import (
    ExecutionRequest,
    ExecutionOrder,
    ExecutionLifecycle,
    OrderType,
    ExecutionPolicy,
    FillPolicy,
)
from ml_service.simulation.execution.slippage import FixedSlippageModel
from ml_service.simulation.execution.commission import BinanceSpotCommission
from ml_service.simulation.execution.latency import ZeroLatencyModel
from ml_service.simulation.execution.liquidity import InfiniteLiquidityModel
from ml_service.simulation.models import MarketSnapshot


def create_matching_engine():
    """Helper to create matching engine with default models"""
    return MatchingEngine(
        slippage_model=FixedSlippageModel(fixed_bps=5.0),
        commission_model=BinanceSpotCommission(fee_pct=0.1),
        latency_model=ZeroLatencyModel(),
        liquidity_model=InfiniteLiquidityModel(),
    )


def create_test_order(
    side="BUY",
    quantity=1.0,
    order_type=OrderType.MARKET,
    fill_policy=FillPolicy.FULL_FILL,
):
    """Helper to create test order"""
    req = ExecutionRequest(
        symbol="BTCUSDT",
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=None,
        execution_policy=ExecutionPolicy.GTC,
        fill_policy=fill_policy,
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


def create_test_snapshot(mid_price=50000.0, bid=None, ask=None):
    """Helper to create test snapshot"""
    return MarketSnapshot(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        symbol="BTCUSDT",
        mid_price=mid_price,
        bid=bid if bid is not None else mid_price - 5.0,
        ask=ask if ask is not None else mid_price + 5.0,
        spread=10.0,
        volume=1000.0,
    )


def test_matching_engine_creation():
    """Test MatchingEngine creation"""
    engine = create_matching_engine()
    assert engine is not None
    assert engine.slippage_model is not None
    assert engine.commission_model is not None
    assert engine.latency_model is not None
    assert engine.liquidity_model is not None


def test_validate_order_success():
    """Test order validation passes for valid order"""
    engine = create_matching_engine()
    order = create_test_order()

    rejection_reason = engine.validate_order(order)
    assert rejection_reason is None


def test_validate_order_negative_quantity():
    """Test order validation rejects negative quantity"""
    engine = create_matching_engine()
    order = create_test_order(quantity=-1.0)

    rejection_reason = engine.validate_order(order)
    assert rejection_reason == "Quantity must be positive"


def test_validate_order_zero_quantity():
    """Test order validation rejects zero quantity"""
    engine = create_matching_engine()
    order = create_test_order(quantity=0.0)

    rejection_reason = engine.validate_order(order)
    assert rejection_reason == "Quantity must be positive"


def test_validate_order_invalid_side():
    """Test order validation rejects invalid side"""
    engine = create_matching_engine()
    order = create_test_order(side="INVALID")

    rejection_reason = engine.validate_order(order)
    assert rejection_reason == "Side must be BUY or SELL"


def test_validate_order_unsupported_order_type():
    """Test order validation rejects unsupported order types"""
    engine = create_matching_engine()
    order = create_test_order(order_type=OrderType.LIMIT)

    rejection_reason = engine.validate_order(order)
    assert "not supported" in rejection_reason


def test_execute_market_order_buy():
    """Test executing BUY MARKET order"""
    engine = create_matching_engine()
    order = create_test_order(side="BUY", quantity=1.0)
    snapshot = create_test_snapshot(mid_price=50000.0, ask=50005.0)

    report = engine.execute_order(order, snapshot)

    assert report.status == ExecutionLifecycle.FILLED
    assert len(report.emitted_fills) == 1
    assert report.remaining_quantity == 0.0
    assert report.rejection_reason is None

    fill = report.emitted_fills[0]
    assert fill.symbol == "BTCUSDT"
    assert fill.side == "BUY"
    assert fill.quantity == 1.0
    assert fill.price > snapshot.ask


def test_execute_market_order_sell():
    """Test executing SELL MARKET order"""
    engine = create_matching_engine()
    order = create_test_order(side="SELL", quantity=1.0)
    snapshot = create_test_snapshot(mid_price=50000.0, bid=49995.0)

    report = engine.execute_order(order, snapshot)

    assert report.status == ExecutionLifecycle.FILLED
    assert len(report.emitted_fills) == 1
    assert report.remaining_quantity == 0.0

    fill = report.emitted_fills[0]
    assert fill.symbol == "BTCUSDT"
    assert fill.side == "SELL"
    assert fill.quantity == 1.0
    assert fill.price < snapshot.bid


def test_execute_order_calculates_commission():
    """Test order execution calculates commission"""
    engine = create_matching_engine()
    order = create_test_order(side="BUY", quantity=1.0)
    snapshot = create_test_snapshot(mid_price=50000.0)

    report = engine.execute_order(order, snapshot)

    fill = report.emitted_fills[0]
    assert fill.commission > 0


def test_execute_order_applies_slippage():
    """Test order execution applies slippage"""
    engine = create_matching_engine()
    order = create_test_order(side="BUY", quantity=1.0)
    snapshot = create_test_snapshot(mid_price=50000.0, ask=50005.0)

    report = engine.execute_order(order, snapshot)

    fill = report.emitted_fills[0]
    assert fill.slippage > 0
    assert fill.price == snapshot.ask + fill.slippage


def test_execute_order_rejection():
    """Test order execution with invalid order is rejected"""
    engine = create_matching_engine()
    order = create_test_order(quantity=-1.0)
    snapshot = create_test_snapshot(mid_price=50000.0)

    report = engine.execute_order(order, snapshot)

    assert report.status == ExecutionLifecycle.REJECTED
    assert len(report.emitted_fills) == 0
    assert report.rejection_reason is not None


def test_execute_order_uses_mid_price_fallback():
    """Test execution uses mid_price when bid/ask not available"""
    engine = create_matching_engine()
    order = create_test_order(side="BUY", quantity=1.0)
    snapshot = MarketSnapshot(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        symbol="BTCUSDT",
        mid_price=50000.0,
        bid=None,
        ask=None,
        spread=None,
        volume=1000.0,
    )

    report = engine.execute_order(order, snapshot)

    assert report.status == ExecutionLifecycle.FILLED
    fill = report.emitted_fills[0]
    assert fill.price > snapshot.mid_price


def test_execute_order_multiple_quantity():
    """Test executing order with larger quantity"""
    engine = create_matching_engine()
    order = create_test_order(side="BUY", quantity=10.0)
    snapshot = create_test_snapshot(mid_price=50000.0)

    report = engine.execute_order(order, snapshot)

    assert report.status == ExecutionLifecycle.FILLED
    fill = report.emitted_fills[0]
    assert fill.quantity == 10.0
