"""
Simulation Portfolio Runner

Coordinates the simulation step lifecycle:
1. Market event arrives
2. Simulation clock advances
3. Strategy produces signal
4. Order created
5. Execution simulated
6. Fill generated
7. Portfolio updated
8. Snapshot created
"""

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from ml_service.portfolio.models import Portfolio, AccountType
from ml_service.portfolio.service import PortfolioService
from ml_service.portfolio.snapshot import PortfolioSnapshot, PortfolioSnapshotService
from ml_service.simulation.execution.execution_models import ExecutionFill
from ml_service.simulation.integration.execution_adapter import ExecutionAdapter
from ml_service.simulation.integration.portfolio_adapter import PortfolioAdapter
from ml_service.simulation.interfaces import IExecutionContext
from ml_service.simulation.models import MarketSnapshot, Order


@dataclass(frozen=True)
class SimulationPortfolioState:
    """
    Immutable simulation state snapshot.

    Contains:
    - simulation_id
    - current_time
    - portfolio
    - latest_snapshot
    - processed_events
    """
    simulation_id: str
    current_time: datetime
    portfolio: Portfolio
    latest_snapshot: Optional[PortfolioSnapshot]
    processed_events: List[object] = field(default_factory=list)

    def with_portfolio(self, portfolio: Portfolio) -> "SimulationPortfolioState":
        """Return new state with updated portfolio."""
        return replace(self, portfolio=portfolio)

    def with_snapshot(self, snapshot: PortfolioSnapshot) -> "SimulationPortfolioState":
        """Return new state with updated snapshot."""
        return replace(self, latest_snapshot=snapshot)

    def with_time(self, current_time: datetime) -> "SimulationPortfolioState":
        """Return new state with updated time."""
        return replace(self, current_time=current_time)

    def with_events(self, events: List[object]) -> "SimulationPortfolioState":
        """Return new state with additional events."""
        all_events = list(self.processed_events) + events
        return replace(self, processed_events=all_events)


class SimulationPortfolioRunner:
    """
    Coordinates simulation runtime with portfolio and execution layers.

    Flow:
    1. Market snapshot arrives
    2. Update portfolio mark prices
    3. Strategy generates signal/order
    4. Execute order via execution adapter
    5. Apply fill via portfolio adapter
    6. Create snapshot
    7. Return updated state

    Maintains:
    - Deterministic replay
    - Immutable state transitions
    - No database writes
    - No exchange dependency
    - Chronological event processing
    """

    def __init__(
        self,
        portfolio_adapter: PortfolioAdapter,
        execution_adapter: ExecutionAdapter,
        portfolio_service: PortfolioService,
        snapshot_service: PortfolioSnapshotService,
    ):
        self.portfolio_adapter = portfolio_adapter
        self.execution_adapter = execution_adapter
        self.portfolio_service = portfolio_service
        self.snapshot_service = snapshot_service

    def initialize_state(
        self,
        simulation_id: str,
        initial_capital: float,
        start_time: datetime,
        account_type: AccountType = AccountType.FUTURES,
    ) -> SimulationPortfolioState:
        """
        Initialize simulation state with empty portfolio.

        Args:
            simulation_id: Unique simulation identifier
            initial_capital: Starting cash balance
            start_time: Simulation start timestamp
            account_type: Account type (SPOT, MARGIN, FUTURES)

        Returns:
            Initial SimulationPortfolioState
        """
        portfolio_id = f"sim-portfolio-{simulation_id}"

        portfolio = self.portfolio_service.initialize_portfolio(
            portfolio_id=portfolio_id,
            initial_cash=initial_capital,
            account_type=account_type,
            timestamp=start_time,
        )

        snapshot, _ = self.snapshot_service.create_snapshot(portfolio, start_time)

        return SimulationPortfolioState(
            simulation_id=simulation_id,
            current_time=start_time,
            portfolio=portfolio,
            latest_snapshot=snapshot,
            processed_events=[],
        )

    def run_step(
        self,
        state: SimulationPortfolioState,
        market_snapshot: MarketSnapshot,
        orders: Optional[List[Order]] = None,
        context: Optional[IExecutionContext] = None,
    ) -> SimulationPortfolioState:
        """
        Execute a single simulation step.

        Flow:
        1. Update portfolio with new market prices
        2. Process any pending orders
        3. Execute orders and generate fills
        4. Apply fills to portfolio
        5. Create snapshot
        6. Return updated state

        Args:
            state: Current simulation state
            market_snapshot: Current market data
            orders: Optional list of orders to execute
            context: Execution context for order matching

        Returns:
            Updated SimulationPortfolioState
        """
        current_portfolio = state.portfolio
        step_events = []

        mark_prices = {market_snapshot.symbol: market_snapshot.mid_price}

        updated_portfolio, price_events = self.portfolio_service.update_market_prices(
            current_portfolio,
            mark_prices,
            market_snapshot.timestamp,
        )
        step_events.extend(price_events)

        if orders and context:
            for order in orders:
                fill = self.execution_adapter.execute_order(
                    order, market_snapshot, context
                )

                if fill:
                    result = self.portfolio_adapter.apply_fill(
                        updated_portfolio, fill
                    )
                    updated_portfolio = result.portfolio
                    step_events.extend(result.events)

        snapshot, snapshot_event = self.snapshot_service.create_snapshot(
            updated_portfolio, market_snapshot.timestamp
        )
        step_events.append(snapshot_event)

        new_state = state.with_portfolio(updated_portfolio)
        new_state = new_state.with_snapshot(snapshot)
        new_state = new_state.with_time(market_snapshot.timestamp)
        new_state = new_state.with_events(step_events)

        return new_state

    def run_market_update_only(
        self,
        state: SimulationPortfolioState,
        market_snapshot: MarketSnapshot,
    ) -> SimulationPortfolioState:
        """
        Update portfolio with market prices only (no order execution).

        Args:
            state: Current simulation state
            market_snapshot: Current market data

        Returns:
            Updated SimulationPortfolioState
        """
        mark_prices = {market_snapshot.symbol: market_snapshot.mid_price}

        updated_portfolio, events = self.portfolio_service.update_market_prices(
            state.portfolio,
            mark_prices,
            market_snapshot.timestamp,
        )

        snapshot, snapshot_event = self.snapshot_service.create_snapshot(
            updated_portfolio, market_snapshot.timestamp
        )
        events.append(snapshot_event)

        new_state = state.with_portfolio(updated_portfolio)
        new_state = new_state.with_snapshot(snapshot)
        new_state = new_state.with_time(market_snapshot.timestamp)
        new_state = new_state.with_events(events)

        return new_state
