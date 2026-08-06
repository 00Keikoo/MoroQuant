"""
Test Simulation Portfolio Integration Layer

Verifies:
1. Single market step
2. Buy order lifecycle
3. Sell order lifecycle
4. Futures long lifecycle
5. Snapshot generated after fill
6. Multiple market steps
7. Deterministic replay
8. Event ordering
9. Portfolio state immutability
10. Failed execution handling
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from ml_service.portfolio.models import (
    AccountType,
    PositionType,
    Portfolio,
)
from ml_service.portfolio.service import PortfolioService
from ml_service.portfolio.ledger import LedgerService
from ml_service.portfolio.position import PositionService
from ml_service.portfolio.equity import EquityService
from ml_service.portfolio.margin import MarginService
from ml_service.portfolio.snapshot import PortfolioSnapshotService
from ml_service.simulation.execution.simulator import ExecutionSimulator
from ml_service.simulation.execution.matching_engine import MatchingEngine
from ml_service.simulation.execution.slippage import FixedSlippageModel
from ml_service.simulation.execution.commission import BinanceSpotCommission
from ml_service.simulation.execution.latency import ZeroLatencyModel
from ml_service.simulation.execution.liquidity import InfiniteLiquidityModel
from ml_service.simulation.models import (
    MarketSnapshot,
    Order,
    OrderSide,
    OrderType,
    OrderStatus,
)
from ml_service.simulation.integration import (
    PortfolioAdapter,
    ExecutionAdapter,
    SimulationPortfolioRunner,
)


class MockExecutionContext:
    """Mock execution context for testing."""

    def __init__(self, market_snapshot: MarketSnapshot, current_time: datetime):
        self._snapshot = market_snapshot
        self._current_time = current_time

    def get_market_snapshot(self, symbol: str):
        if symbol == self._snapshot.symbol:
            return self._snapshot
        return None

    def get_current_time(self):
        return self._current_time


@pytest.fixture
def base_timestamp():
    """Base timestamp for tests."""
    return datetime(2024, 1, 1, 12, 0, 0)


@pytest.fixture
def portfolio_services():
    """Initialize portfolio service stack."""
    ledger_service = LedgerService()
    position_service = PositionService()
    equity_service = EquityService()
    margin_service = MarginService()

    portfolio_service = PortfolioService(
        ledger_service=ledger_service,
        position_service=position_service,
        equity_service=equity_service,
        margin_service=margin_service,
    )

    snapshot_service = PortfolioSnapshotService()

    return portfolio_service, snapshot_service


@pytest.fixture
def execution_simulator():
    """Initialize execution simulator."""
    slippage_model = FixedSlippageModel(fixed_bps=0.0)
    commission_model = BinanceSpotCommission(fee_pct=0.1)
    latency_model = ZeroLatencyModel()
    liquidity_model = InfiniteLiquidityModel()

    matching_engine = MatchingEngine(
        slippage_model=slippage_model,
        commission_model=commission_model,
        latency_model=latency_model,
        liquidity_model=liquidity_model,
    )

    return ExecutionSimulator(matching_engine=matching_engine)


@pytest.fixture
def integration_runner(portfolio_services, execution_simulator):
    """Initialize integration runner."""
    portfolio_service, snapshot_service = portfolio_services

    portfolio_adapter = PortfolioAdapter(
        portfolio_service=portfolio_service,
        snapshot_service=snapshot_service,
    )

    execution_adapter = ExecutionAdapter(
        execution_simulator=execution_simulator,
    )

    return SimulationPortfolioRunner(
        portfolio_adapter=portfolio_adapter,
        execution_adapter=execution_adapter,
        portfolio_service=portfolio_service,
        snapshot_service=snapshot_service,
    )


def test_single_market_step(integration_runner, base_timestamp):
    """Test 1: Single market step without orders."""
    simulation_id = str(uuid4())

    state = integration_runner.initialize_state(
        simulation_id=simulation_id,
        initial_capital=10000.0,
        start_time=base_timestamp,
        account_type=AccountType.FUTURES,
    )

    assert state.simulation_id == simulation_id
    assert state.portfolio.equity == 10000.0
    assert state.latest_snapshot is not None
    assert len(state.processed_events) == 0

    market_snapshot = MarketSnapshot(
        timestamp=base_timestamp + timedelta(minutes=1),
        symbol="BTCUSDT",
        mid_price=50000.0,
        bid=49995.0,
        ask=50005.0,
    )

    new_state = integration_runner.run_market_update_only(
        state=state,
        market_snapshot=market_snapshot,
    )

    assert new_state.current_time == market_snapshot.timestamp
    assert new_state.portfolio.equity == 10000.0
    assert len(new_state.processed_events) > 0


def test_buy_order_lifecycle(integration_runner, base_timestamp):
    """Test 2: Buy order lifecycle."""
    simulation_id = str(uuid4())

    state = integration_runner.initialize_state(
        simulation_id=simulation_id,
        initial_capital=10000.0,
        start_time=base_timestamp,
        account_type=AccountType.FUTURES,
    )

    market_snapshot = MarketSnapshot(
        timestamp=base_timestamp + timedelta(minutes=1),
        symbol="BTCUSDT",
        mid_price=50000.0,
        bid=49995.0,
        ask=50005.0,
    )

    order = Order(
        order_id=str(uuid4()),
        simulation_run_id=simulation_id,
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.1,
        price=None,
        status=OrderStatus.PENDING,
        created_at=market_snapshot.timestamp,
    )

    context = MockExecutionContext(market_snapshot, market_snapshot.timestamp)

    new_state = integration_runner.run_step(
        state=state,
        market_snapshot=market_snapshot,
        orders=[order],
        context=context,
    )

    assert len(new_state.portfolio.positions) == 1
    assert "BTCUSDT" in new_state.portfolio.positions
    position = new_state.portfolio.positions["BTCUSDT"]
    assert position.quantity > 0
    assert new_state.latest_snapshot is not None


def test_sell_order_lifecycle(integration_runner, base_timestamp):
    """Test 3: Sell order lifecycle (open long, then close)."""
    simulation_id = str(uuid4())

    state = integration_runner.initialize_state(
        simulation_id=simulation_id,
        initial_capital=10000.0,
        start_time=base_timestamp,
        account_type=AccountType.FUTURES,
    )

    market_snapshot_1 = MarketSnapshot(
        timestamp=base_timestamp + timedelta(minutes=1),
        symbol="BTCUSDT",
        mid_price=50000.0,
        bid=49995.0,
        ask=50005.0,
    )

    buy_order = Order(
        order_id=str(uuid4()),
        simulation_run_id=simulation_id,
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.1,
        price=None,
        status=OrderStatus.PENDING,
        created_at=market_snapshot_1.timestamp,
    )

    context_1 = MockExecutionContext(market_snapshot_1, market_snapshot_1.timestamp)

    state = integration_runner.run_step(
        state=state,
        market_snapshot=market_snapshot_1,
        orders=[buy_order],
        context=context_1,
    )

    assert len(state.portfolio.positions) == 1

    market_snapshot_2 = MarketSnapshot(
        timestamp=base_timestamp + timedelta(minutes=2),
        symbol="BTCUSDT",
        mid_price=51000.0,
        bid=50995.0,
        ask=51005.0,
    )

    sell_order = Order(
        order_id=str(uuid4()),
        simulation_run_id=simulation_id,
        symbol="BTCUSDT",
        side=OrderSide.SELL,
        order_type=OrderType.MARKET,
        quantity=0.1,
        price=None,
        status=OrderStatus.PENDING,
        created_at=market_snapshot_2.timestamp,
    )

    context_2 = MockExecutionContext(market_snapshot_2, market_snapshot_2.timestamp)

    final_state = integration_runner.run_step(
        state=state,
        market_snapshot=market_snapshot_2,
        orders=[sell_order],
        context=context_2,
    )

    assert len(final_state.portfolio.positions) == 0
    assert final_state.portfolio.equity > 10000.0


def test_futures_long_lifecycle(integration_runner, base_timestamp):
    """Test 4: Futures long lifecycle with price updates."""
    simulation_id = str(uuid4())

    state = integration_runner.initialize_state(
        simulation_id=simulation_id,
        initial_capital=10000.0,
        start_time=base_timestamp,
        account_type=AccountType.FUTURES,
    )

    market_snapshot_1 = MarketSnapshot(
        timestamp=base_timestamp + timedelta(minutes=1),
        symbol="BTCUSDT",
        mid_price=50000.0,
        bid=49995.0,
        ask=50005.0,
    )

    order = Order(
        order_id=str(uuid4()),
        simulation_run_id=simulation_id,
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.1,
        price=None,
        status=OrderStatus.PENDING,
        created_at=market_snapshot_1.timestamp,
    )

    context = MockExecutionContext(market_snapshot_1, market_snapshot_1.timestamp)

    state = integration_runner.run_step(
        state=state,
        market_snapshot=market_snapshot_1,
        orders=[order],
        context=context,
    )

    initial_equity = state.portfolio.equity

    market_snapshot_2 = MarketSnapshot(
        timestamp=base_timestamp + timedelta(minutes=2),
        symbol="BTCUSDT",
        mid_price=52000.0,
        bid=51995.0,
        ask=52005.0,
    )

    state = integration_runner.run_market_update_only(
        state=state,
        market_snapshot=market_snapshot_2,
    )

    assert state.portfolio.equity > initial_equity
    position = state.portfolio.positions["BTCUSDT"]
    assert position.unrealized_pnl > 0


def test_snapshot_generated_after_fill(integration_runner, base_timestamp):
    """Test 5: Snapshot generated after fill."""
    simulation_id = str(uuid4())

    state = integration_runner.initialize_state(
        simulation_id=simulation_id,
        initial_capital=10000.0,
        start_time=base_timestamp,
        account_type=AccountType.FUTURES,
    )

    initial_snapshot_id = state.latest_snapshot.snapshot_id

    market_snapshot = MarketSnapshot(
        timestamp=base_timestamp + timedelta(minutes=1),
        symbol="BTCUSDT",
        mid_price=50000.0,
        bid=49995.0,
        ask=50005.0,
    )

    order = Order(
        order_id=str(uuid4()),
        simulation_run_id=simulation_id,
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.1,
        price=None,
        status=OrderStatus.PENDING,
        created_at=market_snapshot.timestamp,
    )

    context = MockExecutionContext(market_snapshot, market_snapshot.timestamp)

    new_state = integration_runner.run_step(
        state=state,
        market_snapshot=market_snapshot,
        orders=[order],
        context=context,
    )

    assert new_state.latest_snapshot.snapshot_id != initial_snapshot_id
    assert new_state.latest_snapshot.timestamp == market_snapshot.timestamp


def test_multiple_market_steps(integration_runner, base_timestamp):
    """Test 6: Multiple market steps with varying prices."""
    simulation_id = str(uuid4())

    state = integration_runner.initialize_state(
        simulation_id=simulation_id,
        initial_capital=10000.0,
        start_time=base_timestamp,
        account_type=AccountType.FUTURES,
    )

    prices = [50000.0, 50500.0, 51000.0, 50800.0, 51200.0]

    for i, price in enumerate(prices):
        market_snapshot = MarketSnapshot(
            timestamp=base_timestamp + timedelta(minutes=i + 1),
            symbol="BTCUSDT",
            mid_price=price,
            bid=price - 5.0,
            ask=price + 5.0,
        )

        state = integration_runner.run_market_update_only(
            state=state,
            market_snapshot=market_snapshot,
        )

    assert state.current_time == base_timestamp + timedelta(minutes=len(prices))
    assert len(state.processed_events) > 0


def test_deterministic_replay(integration_runner, base_timestamp):
    """Test 7: Deterministic replay produces identical results."""
    simulation_id = str(uuid4())

    def run_simulation():
        state = integration_runner.initialize_state(
            simulation_id=simulation_id,
            initial_capital=10000.0,
            start_time=base_timestamp,
            account_type=AccountType.FUTURES,
        )

        market_snapshot = MarketSnapshot(
            timestamp=base_timestamp + timedelta(minutes=1),
            symbol="BTCUSDT",
            mid_price=50000.0,
            bid=49995.0,
            ask=50005.0,
        )

        order = Order(
            order_id="order-123",
            simulation_run_id=simulation_id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
            price=None,
            status=OrderStatus.PENDING,
            created_at=market_snapshot.timestamp,
        )

        context = MockExecutionContext(market_snapshot, market_snapshot.timestamp)

        return integration_runner.run_step(
            state=state,
            market_snapshot=market_snapshot,
            orders=[order],
            context=context,
        )

    result_1 = run_simulation()
    result_2 = run_simulation()

    assert result_1.portfolio.equity == result_2.portfolio.equity
    assert result_1.portfolio.cash_ledger.ledger_cash_balance == result_2.portfolio.cash_ledger.ledger_cash_balance
    assert len(result_1.portfolio.positions) == len(result_2.portfolio.positions)


def test_event_ordering(integration_runner, base_timestamp):
    """Test 8: Event ordering is chronological."""
    simulation_id = str(uuid4())

    state = integration_runner.initialize_state(
        simulation_id=simulation_id,
        initial_capital=10000.0,
        start_time=base_timestamp,
        account_type=AccountType.FUTURES,
    )

    market_snapshot = MarketSnapshot(
        timestamp=base_timestamp + timedelta(minutes=1),
        symbol="BTCUSDT",
        mid_price=50000.0,
        bid=49995.0,
        ask=50005.0,
    )

    order = Order(
        order_id=str(uuid4()),
        simulation_run_id=simulation_id,
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.1,
        price=None,
        status=OrderStatus.PENDING,
        created_at=market_snapshot.timestamp,
    )

    context = MockExecutionContext(market_snapshot, market_snapshot.timestamp)

    new_state = integration_runner.run_step(
        state=state,
        market_snapshot=market_snapshot,
        orders=[order],
        context=context,
    )

    assert len(new_state.processed_events) > 0

    for i in range(len(new_state.processed_events) - 1):
        event_a = new_state.processed_events[i]
        event_b = new_state.processed_events[i + 1]

        if hasattr(event_a, 'timestamp') and hasattr(event_b, 'timestamp'):
            assert event_a.timestamp <= event_b.timestamp


def test_portfolio_state_immutability(integration_runner, base_timestamp):
    """Test 9: Portfolio state immutability."""
    simulation_id = str(uuid4())

    state = integration_runner.initialize_state(
        simulation_id=simulation_id,
        initial_capital=10000.0,
        start_time=base_timestamp,
        account_type=AccountType.FUTURES,
    )

    original_equity = state.portfolio.equity
    original_portfolio_id = id(state.portfolio)

    market_snapshot = MarketSnapshot(
        timestamp=base_timestamp + timedelta(minutes=1),
        symbol="BTCUSDT",
        mid_price=50000.0,
        bid=49995.0,
        ask=50005.0,
    )

    new_state = integration_runner.run_market_update_only(
        state=state,
        market_snapshot=market_snapshot,
    )

    assert state.portfolio.equity == original_equity
    assert id(state.portfolio) == original_portfolio_id
    assert id(new_state.portfolio) != original_portfolio_id


def test_failed_execution_handling(integration_runner, base_timestamp):
    """Test 10: Failed execution handling."""
    simulation_id = str(uuid4())

    state = integration_runner.initialize_state(
        simulation_id=simulation_id,
        initial_capital=10000.0,
        start_time=base_timestamp,
        account_type=AccountType.FUTURES,
    )

    market_snapshot = MarketSnapshot(
        timestamp=base_timestamp + timedelta(minutes=1),
        symbol="BTCUSDT",
        mid_price=50000.0,
        bid=49995.0,
        ask=50005.0,
    )

    order = Order(
        order_id=str(uuid4()),
        simulation_run_id=simulation_id,
        symbol="ETHUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1.0,
        price=None,
        status=OrderStatus.PENDING,
        created_at=market_snapshot.timestamp,
    )

    context = MockExecutionContext(market_snapshot, market_snapshot.timestamp)

    new_state = integration_runner.run_step(
        state=state,
        market_snapshot=market_snapshot,
        orders=[order],
        context=context,
    )

    assert len(new_state.portfolio.positions) == 0
    assert new_state.portfolio.equity == 10000.0
