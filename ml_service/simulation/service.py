"""
Simulation Service Layer

Pure functional services for simulation domain logic.
All functions are deterministic with zero side effects.
"""

from datetime import datetime
from typing import List, Optional, Tuple
from dataclasses import replace

from ml_service.simulation.models import (
    SimulationRun,
    SimulationConfig,
    SimulationStatus,
    Order,
    OrderStatus,
    Fill,
    Trade,
    Portfolio,
    Position,
    EquityCurve,
    PerformanceMetrics,
    SimulationReport,
)


class ValidationService:
    """Pure validation functions"""

    @staticmethod
    def validate_config(config: SimulationConfig) -> Tuple[bool, Optional[str]]:
        """Validate simulation configuration"""
        if config.initial_capital <= 0:
            return False, "initial_capital must be positive"

        if config.start_time >= config.end_time:
            return False, "start_time must be before end_time"

        if not config.symbol_universe:
            return False, "symbol_universe cannot be empty"

        if not config.config_hash:
            return False, "config_hash is required"

        return True, None

    @staticmethod
    def validate_order(order: Order, portfolio: Portfolio) -> Tuple[bool, Optional[str]]:
        """Validate order against portfolio state"""
        if order.quantity <= 0:
            return False, "quantity must be positive"

        if order.price is not None and order.price <= 0:
            return False, "price must be positive when specified"

        return True, None

    @staticmethod
    def validate_fill(fill: Fill) -> Tuple[bool, Optional[str]]:
        """Validate fill data"""
        if fill.quantity <= 0:
            return False, "quantity must be positive"

        if fill.price <= 0:
            return False, "price must be positive"

        if fill.fee < 0:
            return False, "fee cannot be negative"

        return True, None


class LifecycleService:
    """Pure functions for managing simulation lifecycle"""

    @staticmethod
    def create_simulation(
        run_id: str,
        config: SimulationConfig,
        created_at: datetime
    ) -> SimulationRun:
        """Create a new simulation run"""
        return SimulationRun(
            run_id=run_id,
            config=config,
            status=SimulationStatus.CREATED,
            created_at=created_at,
        )

    @staticmethod
    def start_simulation(run: SimulationRun, started_at: datetime) -> SimulationRun:
        """Transition simulation to RUNNING state"""
        if run.status != SimulationStatus.CREATED:
            raise ValueError(f"Cannot start simulation in {run.status} state")

        return replace(run, status=SimulationStatus.RUNNING, started_at=started_at)

    @staticmethod
    def complete_simulation(
        run: SimulationRun,
        completed_at: datetime
    ) -> SimulationRun:
        """Transition simulation to COMPLETED state"""
        if run.status != SimulationStatus.RUNNING:
            raise ValueError(f"Cannot complete simulation in {run.status} state")

        return replace(run, status=SimulationStatus.COMPLETED, completed_at=completed_at)

    @staticmethod
    def fail_simulation(
        run: SimulationRun,
        error_message: str,
        failed_at: datetime
    ) -> SimulationRun:
        """Transition simulation to FAILED state"""
        if run.status not in [SimulationStatus.CREATED, SimulationStatus.RUNNING]:
            raise ValueError(f"Cannot fail simulation in {run.status} state")

        return replace(
            run,
            status=SimulationStatus.FAILED,
            error_message=error_message,
            completed_at=failed_at
        )

    @staticmethod
    def cancel_simulation(
        run: SimulationRun,
        cancelled_at: datetime
    ) -> SimulationRun:
        """Transition simulation to CANCELLED state"""
        if run.status != SimulationStatus.RUNNING:
            raise ValueError(f"Cannot cancel simulation in {run.status} state")

        return replace(
            run,
            status=SimulationStatus.CANCELLED,
            completed_at=cancelled_at
        )


class PortfolioService:
    """Pure functions for portfolio calculations"""

    @staticmethod
    def create_initial_portfolio(
        portfolio_id: str,
        initial_capital: float,
        leverage: float = 1.0
    ) -> Portfolio:
        """Create initial portfolio state"""
        return Portfolio(
            portfolio_id=portfolio_id,
            cash=initial_capital,
            equity=initial_capital,
            used_margin=0.0,
            free_margin=initial_capital if leverage > 1 else 0.0,
            reserved_margin=0.0,
            buying_power=initial_capital * leverage,
            leverage=leverage,
            exposure=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            positions={},
        )

    @staticmethod
    def apply_fill(
        portfolio: Portfolio,
        fill: Fill,
        current_prices: dict[str, float]
    ) -> Portfolio:
        """Apply fill to portfolio and return new state"""
        symbol = fill.symbol
        current_position = portfolio.positions.get(symbol)

        if current_position is None:
            new_position = PortfolioService._create_position_from_fill(
                fill, current_prices[symbol]
            )
        else:
            new_position = PortfolioService._update_position_from_fill(
                current_position, fill, current_prices[symbol]
            )

        new_positions = dict(portfolio.positions)
        if new_position.quantity == 0:
            new_positions.pop(symbol, None)
        else:
            new_positions[symbol] = new_position

        new_cash = portfolio.cash - (fill.quantity * fill.price + fill.fee)
        total_exposure = sum(abs(pos.quantity * current_prices.get(pos.symbol, 0))
                           for pos in new_positions.values())
        total_unrealized = sum(pos.unrealized_pnl for pos in new_positions.values())

        new_equity = new_cash + total_exposure + total_unrealized

        return replace(
            portfolio,
            cash=new_cash,
            equity=new_equity,
            exposure=total_exposure,
            unrealized_pnl=total_unrealized,
            positions=new_positions,
        )

    @staticmethod
    def _create_position_from_fill(fill: Fill, current_price: float) -> Position:
        """Create new position from fill"""
        quantity = fill.quantity if fill.side.value == "BUY" else -fill.quantity

        return Position(
            symbol=fill.symbol,
            quantity=quantity,
            average_entry_price=fill.price,
            unrealized_pnl=quantity * (current_price - fill.price),
            realized_pnl=0.0,
            leverage=1.0,
            required_margin=0.0,
            last_updated_at=fill.executed_at,
        )

    @staticmethod
    def _update_position_from_fill(
        position: Position,
        fill: Fill,
        current_price: float
    ) -> Position:
        """Update existing position with new fill"""
        fill_qty = fill.quantity if fill.side.value == "BUY" else -fill.quantity
        new_quantity = position.quantity + fill_qty

        if new_quantity == 0:
            return replace(
                position,
                quantity=0,
                average_entry_price=0,
                unrealized_pnl=0,
                last_updated_at=fill.executed_at,
            )

        if (position.quantity > 0 and fill_qty > 0) or (position.quantity < 0 and fill_qty < 0):
            total_cost = (position.quantity * position.average_entry_price +
                         fill_qty * fill.price)
            new_avg_price = total_cost / new_quantity
        else:
            new_avg_price = position.average_entry_price

        new_unrealized = new_quantity * (current_price - new_avg_price)

        return replace(
            position,
            quantity=new_quantity,
            average_entry_price=new_avg_price,
            unrealized_pnl=new_unrealized,
            last_updated_at=fill.executed_at,
        )

    @staticmethod
    def update_portfolio_prices(
        portfolio: Portfolio,
        current_prices: dict[str, float]
    ) -> Portfolio:
        """Update portfolio with current market prices"""
        updated_positions = {}
        total_unrealized = 0.0
        total_exposure = 0.0

        for symbol, position in portfolio.positions.items():
            if symbol not in current_prices:
                continue

            current_price = current_prices[symbol]
            unrealized_pnl = position.quantity * (current_price - position.average_entry_price)

            updated_positions[symbol] = replace(
                position,
                unrealized_pnl=unrealized_pnl,
            )

            total_unrealized += unrealized_pnl
            total_exposure += abs(position.quantity * current_price)

        new_equity = portfolio.cash + total_exposure + total_unrealized

        return replace(
            portfolio,
            equity=new_equity,
            exposure=total_exposure,
            unrealized_pnl=total_unrealized,
            positions=updated_positions,
        )


class EquityCurveService:
    """Pure functions for equity curve management"""

    @staticmethod
    def create_curve(run_id: str) -> EquityCurve:
        """Create empty equity curve"""
        return EquityCurve(
            simulation_run_id=run_id,
            timestamps=[],
            equity_values=[],
        )

    @staticmethod
    def append_point(
        curve: EquityCurve,
        timestamp: datetime,
        equity: float
    ) -> EquityCurve:
        """Append equity snapshot to curve"""
        return EquityCurve(
            simulation_run_id=curve.simulation_run_id,
            timestamps=curve.timestamps + [timestamp],
            equity_values=curve.equity_values + [equity],
        )


class PerformanceService:
    """Pure functions for performance metric calculation"""

    @staticmethod
    def calculate_metrics(
        trades: List[Trade],
        equity_curve: EquityCurve,
        initial_capital: float
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        if not trades:
            return PerformanceService._create_empty_metrics()

        returns = PerformanceService._calculate_returns(equity_curve, initial_capital)
        trade_pnls = [trade.realized_pnl for trade in trades]

        winning_trades = [pnl for pnl in trade_pnls if pnl > 0]
        losing_trades = [pnl for pnl in trade_pnls if pnl < 0]

        win_rate = len(winning_trades) / len(trades) if trades else 0.0
        avg_trade = sum(trade_pnls) / len(trades) if trades else 0.0
        median_trade = sorted(trade_pnls)[len(trade_pnls) // 2] if trades else 0.0

        max_dd = PerformanceService._calculate_max_drawdown(equity_curve)
        sharpe = PerformanceService._calculate_sharpe(returns)

        total_holding_time = sum(t.holding_time_seconds for t in trades)
        avg_holding_time = total_holding_time / len(trades) if trades else 0.0

        total_gains = sum(winning_trades) if winning_trades else 0.0
        total_losses = abs(sum(losing_trades)) if losing_trades else 0.0
        profit_factor = total_gains / total_losses if total_losses > 0 else 0.0

        return PerformanceMetrics(
            sharpe=sharpe,
            sortino=0.0,
            calmar=0.0,
            omega=0.0,
            sterling=0.0,
            mar=0.0,
            profit_factor=profit_factor,
            expectancy=avg_trade,
            kelly=0.0,
            recovery_factor=0.0,
            ulcer_index=0.0,
            tail_ratio=0.0,
            skew=0.0,
            kurtosis=0.0,
            cagr=0.0,
            alpha=0.0,
            beta=0.0,
            information_ratio=0.0,
            tracking_error=0.0,
            var=0.0,
            cvar=0.0,
            trade_count=len(trades),
            win_rate=win_rate,
            average_trade=avg_trade,
            median_trade=median_trade,
            max_drawdown=max_dd,
            exposure_time=0.0,
            average_holding_time=avg_holding_time,
            brier_score=None,
            ece=None,
            profit_capture_ratio=0.0,
        )

    @staticmethod
    def _create_empty_metrics() -> PerformanceMetrics:
        """Create zero-filled metrics"""
        return PerformanceMetrics(
            sharpe=0.0, sortino=0.0, calmar=0.0, omega=0.0, sterling=0.0,
            mar=0.0, profit_factor=0.0, expectancy=0.0, kelly=0.0,
            recovery_factor=0.0, ulcer_index=0.0, tail_ratio=0.0,
            skew=0.0, kurtosis=0.0, cagr=0.0, alpha=0.0, beta=0.0,
            information_ratio=0.0, tracking_error=0.0, var=0.0, cvar=0.0,
            trade_count=0, win_rate=0.0, average_trade=0.0, median_trade=0.0,
            max_drawdown=0.0, exposure_time=0.0, average_holding_time=0.0,
            brier_score=None, ece=None, profit_capture_ratio=0.0,
        )

    @staticmethod
    def _calculate_returns(curve: EquityCurve, initial: float) -> List[float]:
        """Calculate period returns"""
        if len(curve.equity_values) < 2:
            return []

        returns = []
        for i in range(1, len(curve.equity_values)):
            prev = curve.equity_values[i - 1]
            curr = curve.equity_values[i]
            returns.append((curr - prev) / prev if prev > 0 else 0.0)

        return returns

    @staticmethod
    def _calculate_max_drawdown(curve: EquityCurve) -> float:
        """Calculate maximum drawdown"""
        if not curve.equity_values:
            return 0.0

        peak = curve.equity_values[0]
        max_dd = 0.0

        for value in curve.equity_values[1:]:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0.0
            max_dd = max(max_dd, dd)

        return max_dd

    @staticmethod
    def _calculate_sharpe(returns: List[float], risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe ratio"""
        if not returns or len(returns) < 2:
            return 0.0

        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = variance ** 0.5

        if std_dev == 0:
            return 0.0

        return (avg_return - risk_free_rate) / std_dev
