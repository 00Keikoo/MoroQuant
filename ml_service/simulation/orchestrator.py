"""
Simulation Orchestrator

Coordinates SimulationRun lifecycle, repositories, and services.
Returns immutable outputs without side effects.
"""

from datetime import datetime, timezone
from typing import Optional, Tuple
import uuid

from ml_service.simulation.models import (
    SimulationRun,
    SimulationConfig,
    SimulationStatus,
    Order,
    Fill,
    Trade,
    Portfolio,
    EquityCurve,
    PerformanceMetrics,
    SimulationReport,
)
from ml_service.simulation.interfaces import (
    ISimulationRunRepository,
    IOrderRepository,
    IFillRepository,
    ITradeRepository,
    IPortfolioRepository,
    IEquityCurveRepository,
    ISimulationReportRepository,
)
from ml_service.simulation.service import (
    ValidationService,
    LifecycleService,
    PortfolioService,
    EquityCurveService,
    PerformanceService,
)


class SimulationOrchestrator:
    """Coordinates simulation execution lifecycle"""

    def __init__(
        self,
        run_repo: ISimulationRunRepository,
        order_repo: IOrderRepository,
        fill_repo: IFillRepository,
        trade_repo: ITradeRepository,
        portfolio_repo: IPortfolioRepository,
        equity_curve_repo: IEquityCurveRepository,
        report_repo: ISimulationReportRepository,
    ) -> None:
        self.run_repo = run_repo
        self.order_repo = order_repo
        self.fill_repo = fill_repo
        self.trade_repo = trade_repo
        self.portfolio_repo = portfolio_repo
        self.equity_curve_repo = equity_curve_repo
        self.report_repo = report_repo

    def create_simulation(
        self,
        config: SimulationConfig,
        run_id: Optional[str] = None
    ) -> SimulationRun:
        """Create and validate a new simulation run"""
        is_valid, error = ValidationService.validate_config(config)
        if not is_valid:
            raise ValueError(f"Invalid configuration: {error}")

        if run_id is None:
            run_id = self._generate_run_id()

        run = LifecycleService.create_simulation(
            run_id=run_id,
            config=config,
            created_at=datetime.now(timezone.utc),
        )

        return self.run_repo.create(run)

    def start_simulation(self, run_id: str) -> SimulationRun:
        """Start simulation execution"""
        run = self.run_repo.get(run_id)
        if run is None:
            raise ValueError(f"SimulationRun {run_id} not found")

        updated_run = LifecycleService.start_simulation(
            run=run,
            started_at=datetime.now(timezone.utc),
        )

        return self.run_repo.update(updated_run)

    def complete_simulation(self, run_id: str) -> SimulationRun:
        """Complete simulation execution"""
        run = self.run_repo.get(run_id)
        if run is None:
            raise ValueError(f"SimulationRun {run_id} not found")

        updated_run = LifecycleService.complete_simulation(
            run=run,
            completed_at=datetime.now(timezone.utc),
        )

        return self.run_repo.update(updated_run)

    def fail_simulation(self, run_id: str, error_message: str) -> SimulationRun:
        """Mark simulation as failed"""
        run = self.run_repo.get(run_id)
        if run is None:
            raise ValueError(f"SimulationRun {run_id} not found")

        updated_run = LifecycleService.fail_simulation(
            run=run,
            error_message=error_message,
            failed_at=datetime.now(timezone.utc),
        )

        return self.run_repo.update(updated_run)

    def cancel_simulation(self, run_id: str) -> SimulationRun:
        """Cancel simulation execution"""
        run = self.run_repo.get(run_id)
        if run is None:
            raise ValueError(f"SimulationRun {run_id} not found")

        updated_run = LifecycleService.cancel_simulation(
            run=run,
            cancelled_at=datetime.now(timezone.utc),
        )

        return self.run_repo.update(updated_run)

    def initialize_portfolio(
        self,
        run_id: str,
        initial_capital: float,
        leverage: float = 1.0
    ) -> Portfolio:
        """Initialize portfolio for simulation run"""
        portfolio_id = f"{run_id}_portfolio"
        portfolio = PortfolioService.create_initial_portfolio(
            portfolio_id=portfolio_id,
            initial_capital=initial_capital,
            leverage=leverage,
        )

        self.portfolio_repo.append_snapshot(run_id, portfolio)
        return portfolio

    def record_order(self, order: Order) -> Order:
        """Record order in repository"""
        return self.order_repo.create(order)

    def record_fill(
        self,
        fill: Fill,
        current_prices: dict[str, float]
    ) -> Portfolio:
        """Record fill and update portfolio state"""
        is_valid, error = ValidationService.validate_fill(fill)
        if not is_valid:
            raise ValueError(f"Invalid fill: {error}")

        self.fill_repo.create(fill)

        current_portfolio = self.portfolio_repo.get_latest(fill.simulation_run_id)
        if current_portfolio is None:
            raise ValueError(f"No portfolio found for run {fill.simulation_run_id}")

        updated_portfolio = PortfolioService.apply_fill(
            portfolio=current_portfolio,
            fill=fill,
            current_prices=current_prices,
        )

        self.portfolio_repo.append_snapshot(fill.simulation_run_id, updated_portfolio)
        return updated_portfolio

    def record_trade(self, trade: Trade) -> Trade:
        """Record completed trade"""
        return self.trade_repo.create(trade)

    def update_portfolio_prices(
        self,
        run_id: str,
        current_prices: dict[str, float]
    ) -> Portfolio:
        """Update portfolio with current market prices"""
        current_portfolio = self.portfolio_repo.get_latest(run_id)
        if current_portfolio is None:
            raise ValueError(f"No portfolio found for run {run_id}")

        updated_portfolio = PortfolioService.update_portfolio_prices(
            portfolio=current_portfolio,
            current_prices=current_prices,
        )

        self.portfolio_repo.append_snapshot(run_id, updated_portfolio)
        return updated_portfolio

    def record_equity_point(
        self,
        run_id: str,
        timestamp: datetime,
        equity: float
    ) -> EquityCurve:
        """Append equity snapshot to curve"""
        curve = self.equity_curve_repo.get(run_id)

        if curve is None:
            curve = EquityCurveService.create_curve(run_id)

        updated_curve = EquityCurveService.append_point(
            curve=curve,
            timestamp=timestamp,
            equity=equity,
        )

        return self.equity_curve_repo.save(updated_curve)

    def calculate_performance(self, run_id: str) -> PerformanceMetrics:
        """Calculate performance metrics for simulation run"""
        run = self.run_repo.get(run_id)
        if run is None:
            raise ValueError(f"SimulationRun {run_id} not found")

        trades = self.trade_repo.list_by_run(run_id)
        equity_curve = self.equity_curve_repo.get(run_id)

        if equity_curve is None:
            raise ValueError(f"No equity curve found for run {run_id}")

        return PerformanceService.calculate_metrics(
            trades=trades,
            equity_curve=equity_curve,
            initial_capital=run.config.initial_capital,
        )

    def generate_report(
        self,
        run_id: str,
        report_id: Optional[str] = None
    ) -> SimulationReport:
        """Generate simulation report with performance metrics"""
        metrics = self.calculate_performance(run_id)

        if report_id is None:
            report_id = self._generate_report_id()

        report = SimulationReport(
            report_id=report_id,
            simulation_run_id=run_id,
            metrics=metrics,
            manifest_checksum=self._generate_checksum(run_id),
            bundle_path=f"/reports/{run_id}",
            created_at=datetime.now(timezone.utc),
        )

        return self.report_repo.create(report)

    def get_simulation_summary(self, run_id: str) -> dict:
        """Get comprehensive simulation summary"""
        run = self.run_repo.get(run_id)
        if run is None:
            raise ValueError(f"SimulationRun {run_id} not found")

        orders = self.order_repo.list_by_run(run_id)
        fills = self.fill_repo.list_by_run(run_id)
        trades = self.trade_repo.list_by_run(run_id)
        portfolio = self.portfolio_repo.get_latest(run_id)
        equity_curve = self.equity_curve_repo.get(run_id)
        report = self.report_repo.get_by_run(run_id)

        return {
            "run": run,
            "order_count": len(orders),
            "fill_count": len(fills),
            "trade_count": len(trades),
            "final_portfolio": portfolio,
            "equity_curve_length": len(equity_curve.equity_values) if equity_curve else 0,
            "report": report,
        }

    @staticmethod
    def _generate_run_id() -> str:
        """Generate unique simulation run ID"""
        return f"sim_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def _generate_report_id() -> str:
        """Generate unique report ID"""
        return f"report_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def _generate_checksum(run_id: str) -> str:
        """Generate checksum for simulation run"""
        import hashlib
        return hashlib.sha256(run_id.encode()).hexdigest()[:16]
