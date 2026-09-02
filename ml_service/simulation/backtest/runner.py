"""
Backtest Runner

Execution-coupled backtest orchestration.
Research consumes outcomes via snapshots, not by constructing execution infrastructure.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Iterator
from uuid import uuid4

from ml_service.portfolio.models import Portfolio, AccountType
from ml_service.portfolio.service import PortfolioService
from ml_service.portfolio.snapshot import PortfolioSnapshot, PortfolioSnapshotService
from ml_service.portfolio.ledger import LedgerService
from ml_service.portfolio.position import PositionService
from ml_service.portfolio.equity import EquityService
from ml_service.portfolio.margin import MarginService
from ml_service.simulation.execution.simulator import ExecutionSimulator
from ml_service.simulation.execution.matching_engine import MatchingEngine
from ml_service.simulation.execution.slippage import FixedSlippageModel
from ml_service.simulation.execution.commission import BinanceSpotCommission
from ml_service.simulation.execution.latency import ZeroLatencyModel
from ml_service.simulation.execution.liquidity import InfiniteLiquidityModel
from ml_service.simulation.integration.execution_adapter import ExecutionAdapter
from ml_service.simulation.integration.portfolio_adapter import PortfolioAdapter
from ml_service.simulation.integration.simulation_portfolio_runner import (
    SimulationPortfolioRunner,
    SimulationPortfolioState,
)
from ml_service.simulation.models import MarketSnapshot


@dataclass(frozen=True)
class BacktestExecutionConfig:
    """Configuration for backtest execution."""
    initial_capital: float
    slippage_bps: float = 5.0
    commission_pct: float = 0.1
    account_type: AccountType = AccountType.FUTURES


@dataclass(frozen=True)
class BacktestExecutionResult:
    """Result from backtest execution."""
    simulation_id: str
    snapshots: List[PortfolioSnapshot]
    final_portfolio: Portfolio
    event_count: int


class BacktestRunner:
    """
    Executes backtests with full execution infrastructure.

    Owns:
    - Portfolio engine initialization
    - Execution simulator construction
    - Market replay coordination
    - Snapshot collection

    Research layer consumes BacktestExecutionResult, not execution internals.
    """

    def __init__(
        self,
        portfolio_service: PortfolioService,
        snapshot_service: PortfolioSnapshotService,
        simulation_runner: SimulationPortfolioRunner,
    ):
        self.portfolio_service = portfolio_service
        self.snapshot_service = snapshot_service
        self.simulation_runner = simulation_runner

    def execute(
        self,
        market_events: Iterator[MarketSnapshot],
        config: BacktestExecutionConfig,
    ) -> BacktestExecutionResult:
        """
        Execute backtest over market events.

        Args:
            market_events: Iterator of market snapshots
            config: Execution configuration

        Returns:
            BacktestExecutionResult with snapshots and final portfolio
        """
        simulation_id = f"sim-{uuid4().hex[:12]}"
        start_time = datetime.utcnow()

        state = self.simulation_runner.initialize_state(
            simulation_id=simulation_id,
            initial_capital=config.initial_capital,
            start_time=start_time,
            account_type=config.account_type,
        )

        snapshots = []
        if state.latest_snapshot:
            snapshots.append(state.latest_snapshot)

        event_count = 0
        for event in market_events:
            state = self.simulation_runner.run_market_update_only(state, event)
            if state.latest_snapshot:
                snapshots.append(state.latest_snapshot)
            event_count += 1

        return BacktestExecutionResult(
            simulation_id=simulation_id,
            snapshots=snapshots,
            final_portfolio=state.portfolio,
            event_count=event_count,
        )

    @staticmethod
    def create_default() -> "BacktestRunner":
        """
        Create runner with default execution infrastructure.

        Returns:
            BacktestRunner with standard configuration
        """
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

        matching_engine = MatchingEngine(
            slippage_model=FixedSlippageModel(fixed_bps=5.0),
            commission_model=BinanceSpotCommission(fee_pct=0.1),
            latency_model=ZeroLatencyModel(),
            liquidity_model=InfiniteLiquidityModel(),
        )
        execution_simulator = ExecutionSimulator(matching_engine=matching_engine)
        execution_adapter = ExecutionAdapter(execution_simulator=execution_simulator)
        portfolio_adapter = PortfolioAdapter(
            portfolio_service=portfolio_service,
            snapshot_service=snapshot_service,
        )

        simulation_runner = SimulationPortfolioRunner(
            portfolio_adapter=portfolio_adapter,
            execution_adapter=execution_adapter,
            portfolio_service=portfolio_service,
            snapshot_service=snapshot_service,
        )

        return BacktestRunner(
            portfolio_service=portfolio_service,
            snapshot_service=snapshot_service,
            simulation_runner=simulation_runner,
        )
