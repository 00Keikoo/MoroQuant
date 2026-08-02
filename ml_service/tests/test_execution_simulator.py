"""
Tests for Execution Simulator
"""

import pytest
from datetime import datetime
from typing import Dict, Optional

from ml_service.simulation.execution.simulator import ExecutionSimulator, ExecutionResult
from ml_service.simulation.execution.execution_models import (
    ExecutionReport,
    ExecutionLifecycle,
)
from ml_service.simulation.execution.matching_engine import MatchingEngine
from ml_service.simulation.execution.slippage import FixedSlippageModel
from ml_service.simulation.execution.commission import BinanceSpotCommission
from ml_service.simulation.execution.latency import ZeroLatencyModel
from ml_service.simulation.execution.liquidity import InfiniteLiquidityModel
from ml_service.simulation.models import (
    Order,
    OrderSide,
    OrderType,
    OrderStatus,
    MarketSnapshot,
)
from ml_service.simulation.interfaces import IExecutionContext


class MockExecutionContext(IExecutionContext):
    """Mock execution context for testing"""

    def __init__(self, snapshots: Dict[str, MarketSnapshot]):
        self.snapshots = snapshots

    def get_current_time(self) -> datetime:
        return datetime(2024, 1, 1, 12, 0, 0)

    def get_market_snapshot(self, symbol: str) -> Optional[MarketSnapshot]:
        return self.snapshots.get(symbol)

    def get_all_prices(self) -> Dict[str, float]:
        return {symbol: snap.mid_price for symbol, snap in self.snapshots.items()}


def create_simulator():
    """Helper to create execution simulator"""
    matching_engine = MatchingEngine(
        slippage_model=FixedSlippageModel(fixed_bps=5.0),
        commission_model=BinanceSpotCommission(fee_pct=0.1),
        latency_model=ZeroLatencyModel(),
        liquidity_model=InfiniteLiquidityModel(),
    )
    return ExecutionSimulator(matching_engine=matching_engine)


def create_test_order(
    symbol="BTCUSDT",
    side=OrderSide.BUY,
    quantity=1.0,
    order_type=OrderType.MARKET,
):
    """Helper to create test order"""
    return Order(
        order_id="order-123",
        simulation_run_id="run-123",
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=None,
        status=OrderStatus.PENDING,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
    )


def create_test_snapshot(symbol="BTCUSDT", mid_price=50000.0):
    """Helper to create test snapshot"""
    return MarketSnapshot(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        symbol=symbol,
        mid_price=mid_price,
        bid=mid_price - 5.0,
        ask=mid_price + 5.0,
        spread=10.0,
        volume=1000.0,
    )


def test_execution_simulator_creation():
    """Test ExecutionSimulator creation"""
    simulator = create_simulator()
    assert simulator is not None
    assert simulator.matching_engine is not None


def test_simulate_execution_success():
    """Test successful order execution simulation"""
    simulator = create_simulator()
    order = create_test_order(side=OrderSide.BUY, quantity=1.0)
    snapshot = create_test_snapshot(mid_price=50000.0)
    context = MockExecutionContext({"BTCUSDT": snapshot})

    result = simulator.simulate_execution(order, context)

    assert result is not None
    assert result.get_filled_quantity() == 1.0
    assert result.is_fully_filled()
    assert result.get_average_price() > 0
    assert result.get_total_fees() > 0
    assert result.get_slippage() > 0


def test_simulate_execution_no_market_data():
    """Test execution simulation with no market data"""
    simulator = create_simulator()
    order = create_test_order(symbol="ETHUSDT")
    context = MockExecutionContext({})

    result = simulator.simulate_execution(order, context)

    assert result is not None
    assert result.get_filled_quantity() == 0.0
    assert not result.is_fully_filled()


def test_simulate_execution_buy_order():
    """Test simulating BUY order"""
    simulator = create_simulator()
    order = create_test_order(side=OrderSide.BUY, quantity=2.0)
    snapshot = create_test_snapshot(mid_price=50000.0)
    context = MockExecutionContext({"BTCUSDT": snapshot})

    result = simulator.simulate_execution(order, context)

    assert result.get_filled_quantity() == 2.0
    assert result.get_average_price() > snapshot.ask


def test_simulate_execution_sell_order():
    """Test simulating SELL order"""
    simulator = create_simulator()
    order = create_test_order(side=OrderSide.SELL, quantity=2.0)
    snapshot = create_test_snapshot(mid_price=50000.0)
    context = MockExecutionContext({"BTCUSDT": snapshot})

    result = simulator.simulate_execution(order, context)

    assert result.get_filled_quantity() == 2.0
    assert result.get_average_price() < snapshot.bid


def test_estimate_fill_price():
    """Test estimating fill price"""
    simulator = create_simulator()
    order = create_test_order(side=OrderSide.BUY, quantity=1.0)
    snapshot = create_test_snapshot(mid_price=50000.0)
    context = MockExecutionContext({"BTCUSDT": snapshot})

    estimated_price = simulator.estimate_fill_price(order, context)

    assert estimated_price > 0
    assert estimated_price > snapshot.ask


def test_estimate_fill_price_no_data():
    """Test estimating fill price with no market data"""
    simulator = create_simulator()
    order = create_test_order(symbol="ETHUSDT")
    context = MockExecutionContext({})

    estimated_price = simulator.estimate_fill_price(order, context)
    assert estimated_price == 0.0


def test_estimate_slippage():
    """Test estimating slippage"""
    simulator = create_simulator()
    order = create_test_order(side=OrderSide.BUY, quantity=1.0)
    snapshot = create_test_snapshot(mid_price=50000.0)
    context = MockExecutionContext({"BTCUSDT": snapshot})

    slippage = simulator.estimate_slippage(order, context)

    assert slippage > 0


def test_estimate_slippage_no_data():
    """Test estimating slippage with no market data"""
    simulator = create_simulator()
    order = create_test_order(symbol="ETHUSDT")
    context = MockExecutionContext({})

    slippage = simulator.estimate_slippage(order, context)
    assert slippage == 0.0


def test_execution_result_calculations():
    """Test ExecutionResult metric calculations"""
    from ml_service.simulation.execution.execution_models import ExecutionFill

    fill1 = ExecutionFill(
        fill_id="fill-1",
        order_id="order-123",
        symbol="BTCUSDT",
        side="BUY",
        quantity=1.0,
        price=50000.0,
        commission=50.0,
        slippage=2.5,
        executed_at=datetime(2024, 1, 1, 12, 0, 0),
    )

    fill2 = ExecutionFill(
        fill_id="fill-2",
        order_id="order-123",
        symbol="BTCUSDT",
        side="BUY",
        quantity=1.0,
        price=50010.0,
        commission=50.0,
        slippage=2.5,
        executed_at=datetime(2024, 1, 1, 12, 0, 1),
    )

    report = ExecutionReport(
        order_id="order-123",
        status=ExecutionLifecycle.FILLED,
        emitted_fills=[fill1, fill2],
        remaining_quantity=0.0,
        timestamp=datetime(2024, 1, 1, 12, 0, 1),
    )

    result = ExecutionResult(report, [fill1, fill2])

    assert result.get_filled_quantity() == 2.0
    assert result.get_average_price() == 50005.0
    assert result.get_total_fees() == 100.0
    assert result.get_slippage() == 5.0
    assert result.is_fully_filled()


def test_execution_result_empty_fills():
    """Test ExecutionResult with no fills"""
    report = ExecutionReport(
        order_id="order-123",
        status=ExecutionLifecycle.REJECTED,
        emitted_fills=[],
        remaining_quantity=1.0,
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        rejection_reason="Test rejection",
    )

    result = ExecutionResult(report, [])

    assert result.get_filled_quantity() == 0.0
    assert result.get_average_price() == 0.0
    assert result.get_total_fees() == 0.0
    assert result.get_slippage() == 0.0
    assert not result.is_fully_filled()
