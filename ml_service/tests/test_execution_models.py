"""
Tests for Execution Domain Models
"""

import pytest
from datetime import datetime

from ml_service.simulation.execution.execution_models import (
    ExecutionRequest,
    ExecutionOrder,
    ExecutionFill,
    ExecutionReport,
    OrderType,
    ExecutionPolicy,
    FillPolicy,
    ExecutionLifecycle,
)


def test_execution_request_creation():
    """Test ExecutionRequest creation with all fields"""
    req = ExecutionRequest(
        symbol="BTCUSDT",
        side="BUY",
        order_type=OrderType.MARKET,
        quantity=1.0,
        price=50000.0,
        execution_policy=ExecutionPolicy.GTC,
        fill_policy=FillPolicy.FULL_FILL,
        requested_at=datetime(2024, 1, 1, 12, 0, 0),
    )

    assert req.symbol == "BTCUSDT"
    assert req.side == "BUY"
    assert req.order_type == OrderType.MARKET
    assert req.quantity == 1.0
    assert req.price == 50000.0
    assert req.execution_policy == ExecutionPolicy.GTC
    assert req.fill_policy == FillPolicy.FULL_FILL


def test_execution_request_immutability():
    """Test ExecutionRequest is frozen"""
    req = ExecutionRequest(
        symbol="BTCUSDT",
        side="BUY",
        order_type=OrderType.MARKET,
        quantity=1.0,
        price=None,
        execution_policy=ExecutionPolicy.GTC,
        fill_policy=FillPolicy.FULL_FILL,
        requested_at=datetime(2024, 1, 1, 12, 0, 0),
    )

    with pytest.raises(Exception):
        req.symbol = "ETHUSDT"


def test_execution_order_creation():
    """Test ExecutionOrder creation"""
    req = ExecutionRequest(
        symbol="BTCUSDT",
        side="BUY",
        order_type=OrderType.MARKET,
        quantity=1.0,
        price=None,
        execution_policy=ExecutionPolicy.GTC,
        fill_policy=FillPolicy.FULL_FILL,
        requested_at=datetime(2024, 1, 1, 12, 0, 0),
    )

    order = ExecutionOrder(
        order_id="order-123",
        request=req,
        status=ExecutionLifecycle.VALIDATED,
        cumulative_filled_qty=0.0,
        average_filled_price=0.0,
        active_price=None,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 1, 12, 0, 1),
    )

    assert order.order_id == "order-123"
    assert order.request == req
    assert order.status == ExecutionLifecycle.VALIDATED
    assert order.cumulative_filled_qty == 0.0
    assert order.average_filled_price == 0.0


def test_execution_fill_creation():
    """Test ExecutionFill creation"""
    fill = ExecutionFill(
        fill_id="fill-123",
        order_id="order-123",
        symbol="BTCUSDT",
        side="BUY",
        quantity=1.0,
        price=50000.0,
        commission=5.0,
        slippage=2.5,
        executed_at=datetime(2024, 1, 1, 12, 0, 0),
    )

    assert fill.fill_id == "fill-123"
    assert fill.order_id == "order-123"
    assert fill.symbol == "BTCUSDT"
    assert fill.side == "BUY"
    assert fill.quantity == 1.0
    assert fill.price == 50000.0
    assert fill.commission == 5.0
    assert fill.slippage == 2.5


def test_execution_report_creation():
    """Test ExecutionReport creation"""
    fill = ExecutionFill(
        fill_id="fill-123",
        order_id="order-123",
        symbol="BTCUSDT",
        side="BUY",
        quantity=1.0,
        price=50000.0,
        commission=5.0,
        slippage=2.5,
        executed_at=datetime(2024, 1, 1, 12, 0, 0),
    )

    report = ExecutionReport(
        order_id="order-123",
        status=ExecutionLifecycle.FILLED,
        emitted_fills=[fill],
        remaining_quantity=0.0,
        rejection_reason=None,
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
    )

    assert report.order_id == "order-123"
    assert report.status == ExecutionLifecycle.FILLED
    assert len(report.emitted_fills) == 1
    assert report.emitted_fills[0] == fill
    assert report.remaining_quantity == 0.0
    assert report.rejection_reason is None


def test_execution_report_with_rejection():
    """Test ExecutionReport with rejection"""
    report = ExecutionReport(
        order_id="order-123",
        status=ExecutionLifecycle.REJECTED,
        emitted_fills=[],
        remaining_quantity=1.0,
        rejection_reason="Insufficient liquidity",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
    )

    assert report.status == ExecutionLifecycle.REJECTED
    assert len(report.emitted_fills) == 0
    assert report.remaining_quantity == 1.0
    assert report.rejection_reason == "Insufficient liquidity"


def test_order_type_enum():
    """Test OrderType enum values"""
    assert OrderType.MARKET.value == "MARKET"
    assert OrderType.LIMIT.value == "LIMIT"
    assert OrderType.STOP.value == "STOP"
    assert OrderType.STOP_LIMIT.value == "STOP_LIMIT"
    assert OrderType.TRAILING_STOP.value == "TRAILING_STOP"


def test_execution_policy_enum():
    """Test ExecutionPolicy enum values"""
    assert ExecutionPolicy.FOK.value == "FOK"
    assert ExecutionPolicy.IOC.value == "IOC"
    assert ExecutionPolicy.GTC.value == "GTC"
    assert ExecutionPolicy.DAY.value == "DAY"


def test_fill_policy_enum():
    """Test FillPolicy enum values"""
    assert FillPolicy.FULL_FILL.value == "FULL_FILL"
    assert FillPolicy.PARTIAL_FILL.value == "PARTIAL_FILL"
    assert FillPolicy.REJECT.value == "REJECT"


def test_execution_lifecycle_enum():
    """Test ExecutionLifecycle enum values"""
    assert ExecutionLifecycle.REQUESTED.value == "REQUESTED"
    assert ExecutionLifecycle.VALIDATED.value == "VALIDATED"
    assert ExecutionLifecycle.QUEUED.value == "QUEUED"
    assert ExecutionLifecycle.MATCHING.value == "MATCHING"
    assert ExecutionLifecycle.PARTIALLY_FILLED.value == "PARTIALLY_FILLED"
    assert ExecutionLifecycle.FILLED.value == "FILLED"
    assert ExecutionLifecycle.SETTLED.value == "SETTLED"
    assert ExecutionLifecycle.REJECTED.value == "REJECTED"
    assert ExecutionLifecycle.CANCELLED.value == "CANCELLED"
