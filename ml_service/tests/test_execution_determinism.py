"""
Tests for Execution Simulator Determinism

Verifies that identical simulations produce identical results.
All IDs, timestamps, and metrics must be exactly reproducible.
"""

import pytest
from datetime import datetime
from typing import Dict, Optional

from ml_service.simulation.execution.simulator import ExecutionSimulator
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


class DeterministicExecutionContext(IExecutionContext):
    """Deterministic execution context for testing"""

    def __init__(self, snapshots: Dict[str, MarketSnapshot], current_time: datetime):
        self.snapshots = snapshots
        self.current_time = current_time

    def get_current_time(self) -> datetime:
        return self.current_time

    def get_market_snapshot(self, symbol: str) -> Optional[MarketSnapshot]:
        return self.snapshots.get(symbol)

    def get_all_prices(self) -> Dict[str, float]:
        return {symbol: snap.mid_price for symbol, snap in self.snapshots.items()}


def create_deterministic_simulator():
    """Create deterministic execution simulator"""
    matching_engine = MatchingEngine(
        slippage_model=FixedSlippageModel(fixed_bps=5.0),
        commission_model=BinanceSpotCommission(fee_pct=0.1),
        latency_model=ZeroLatencyModel(),
        liquidity_model=InfiniteLiquidityModel(),
    )
    return ExecutionSimulator(matching_engine=matching_engine)


def create_deterministic_order(order_id="order-123"):
    """Create deterministic test order"""
    return Order(
        order_id=order_id,
        simulation_run_id="run-123",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1.0,
        price=None,
        status=OrderStatus.PENDING,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
    )


def create_deterministic_snapshot():
    """Create deterministic market snapshot"""
    return MarketSnapshot(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        symbol="BTCUSDT",
        mid_price=50000.0,
        bid=49995.0,
        ask=50005.0,
        spread=10.0,
        volume=1000.0,
    )


def test_deterministic_execution_identical_results():
    """Test that identical executions produce identical results"""
    simulator = create_deterministic_simulator()
    order = create_deterministic_order()
    snapshot = create_deterministic_snapshot()
    context = DeterministicExecutionContext(
        {"BTCUSDT": snapshot}, datetime(2024, 1, 1, 12, 0, 0)
    )

    result1 = simulator.simulate_execution(order, context)
    result2 = simulator.simulate_execution(order, context)

    assert result1.get_filled_quantity() == result2.get_filled_quantity()
    assert result1.get_average_price() == result2.get_average_price()
    assert result1.get_total_fees() == result2.get_total_fees()
    assert result1.get_slippage() == result2.get_slippage()
    assert result1.is_fully_filled() == result2.is_fully_filled()


def test_deterministic_fill_ids():
    """Test that fill IDs are deterministic"""
    simulator = create_deterministic_simulator()
    order = create_deterministic_order()
    snapshot = create_deterministic_snapshot()
    context = DeterministicExecutionContext(
        {"BTCUSDT": snapshot}, datetime(2024, 1, 1, 12, 0, 0)
    )

    result1 = simulator.simulate_execution(order, context)
    result2 = simulator.simulate_execution(order, context)

    fills1 = result1._fills
    fills2 = result2._fills

    assert len(fills1) == len(fills2)
    for fill1, fill2 in zip(fills1, fills2):
        assert fill1.fill_id == fill2.fill_id, "Fill IDs must be deterministic"
        assert fill1.order_id == fill2.order_id
        assert fill1.symbol == fill2.symbol
        assert fill1.side == fill2.side
        assert fill1.quantity == fill2.quantity
        assert fill1.price == fill2.price
        assert fill1.commission == fill2.commission
        assert fill1.slippage == fill2.slippage
        assert fill1.executed_at == fill2.executed_at


def test_deterministic_execution_report_timestamps():
    """Test that execution report timestamps are deterministic"""
    simulator = create_deterministic_simulator()
    order = create_deterministic_order()
    snapshot = create_deterministic_snapshot()
    context = DeterministicExecutionContext(
        {"BTCUSDT": snapshot}, datetime(2024, 1, 1, 12, 0, 0)
    )

    result1 = simulator.simulate_execution(order, context)
    result2 = simulator.simulate_execution(order, context)

    report1 = result1._report
    report2 = result2._report

    assert report1.timestamp == report2.timestamp, "Report timestamps must be deterministic"
    assert report1.order_id == report2.order_id
    assert report1.status == report2.status
    assert report1.remaining_quantity == report2.remaining_quantity
    assert report1.rejection_reason == report2.rejection_reason


def test_deterministic_execution_across_multiple_orders():
    """Test determinism across multiple order executions"""
    simulator = create_deterministic_simulator()
    snapshot = create_deterministic_snapshot()
    context = DeterministicExecutionContext(
        {"BTCUSDT": snapshot}, datetime(2024, 1, 1, 12, 0, 0)
    )

    orders = [create_deterministic_order(f"order-{i}") for i in range(5)]

    results1 = [simulator.simulate_execution(order, context) for order in orders]
    results2 = [simulator.simulate_execution(order, context) for order in orders]

    for r1, r2 in zip(results1, results2):
        assert r1.get_filled_quantity() == r2.get_filled_quantity()
        assert r1.get_average_price() == r2.get_average_price()
        assert r1.get_total_fees() == r2.get_total_fees()
        assert r1.get_slippage() == r2.get_slippage()

        fills1 = r1._fills
        fills2 = r2._fills
        for f1, f2 in zip(fills1, fills2):
            assert f1.fill_id == f2.fill_id, "All fill IDs must be deterministic"


def test_no_datetime_now_in_execution():
    """Test that execution does not depend on host system time"""
    simulator = create_deterministic_simulator()
    order = create_deterministic_order()
    snapshot = create_deterministic_snapshot()

    context1 = DeterministicExecutionContext(
        {"BTCUSDT": snapshot}, datetime(2024, 1, 1, 12, 0, 0)
    )
    context2 = DeterministicExecutionContext(
        {"BTCUSDT": snapshot}, datetime(2024, 1, 1, 12, 0, 0)
    )

    result1 = simulator.simulate_execution(order, context1)
    result2 = simulator.simulate_execution(order, context2)

    assert result1._report.timestamp == result2._report.timestamp
    assert result1._fills[0].executed_at == result2._fills[0].executed_at


def test_deterministic_estimate_functions():
    """Test that estimation functions are deterministic"""
    simulator = create_deterministic_simulator()
    order = create_deterministic_order()
    snapshot = create_deterministic_snapshot()
    context = DeterministicExecutionContext(
        {"BTCUSDT": snapshot}, datetime(2024, 1, 1, 12, 0, 0)
    )

    price1 = simulator.estimate_fill_price(order, context)
    price2 = simulator.estimate_fill_price(order, context)
    assert price1 == price2, "Estimated fill prices must be deterministic"

    slippage1 = simulator.estimate_slippage(order, context)
    slippage2 = simulator.estimate_slippage(order, context)
    assert slippage1 == slippage2, "Estimated slippage must be deterministic"


def test_deterministic_rejection():
    """Test that rejection scenarios are deterministic"""
    simulator = create_deterministic_simulator()
    order = create_deterministic_order()
    context = DeterministicExecutionContext({}, datetime(2024, 1, 1, 12, 0, 0))

    result1 = simulator.simulate_execution(order, context)
    result2 = simulator.simulate_execution(order, context)

    assert result1.get_filled_quantity() == result2.get_filled_quantity() == 0.0
    assert result1.is_fully_filled() == result2.is_fully_filled() == False
    assert result1._report.status == result2._report.status
    assert result1._report.rejection_reason == result2._report.rejection_reason
    assert result1._report.timestamp == result2._report.timestamp
