"""
Tests for simulation services

Validates pure functional service logic.
"""

import pytest
from datetime import datetime
from dataclasses import replace

from ml_service.simulation.models import (
    SimulationRun,
    SimulationConfig,
    SimulationStatus,
    Order,
    OrderSide,
    OrderType,
    OrderStatus,
    Fill,
    Portfolio,
    Position,
    EquityCurve,
    ExecutionAssumption,
)
from ml_service.simulation.service import (
    ValidationService,
    LifecycleService,
    PortfolioService,
    EquityCurveService,
    PerformanceService,
)


@pytest.fixture
def sample_config():
    assumption = ExecutionAssumption(
        commission=0.1, maker_fee=0.0002, taker_fee=0.0005,
        slippage=0.0001, latency=100, spread_model="FIXED",
        funding_fee=0.0, borrow_fee=0.0,
    )
    return SimulationConfig(
        symbol_universe=["BTCUSDT"],
        timeframe="1h",
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 12, 31),
        initial_capital=100000.0,
        execution_assumption=assumption,
        model_version_id="model_v1",
        dataset_snapshot_id="ds_001",
        config_hash="abc123",
    )


class TestValidationService:
    """Test ValidationService"""

    def test_validate_valid_config(self, sample_config):
        valid, error = ValidationService.validate_config(sample_config)
        assert valid is True
        assert error is None

    def test_validate_negative_capital(self, sample_config):
        bad_config = replace(sample_config, initial_capital=-1000)
        valid, error = ValidationService.validate_config(bad_config)
        assert valid is False
        assert "positive" in error

    def test_validate_invalid_time_range(self, sample_config):
        bad_config = replace(
            sample_config,
            start_time=datetime(2024, 12, 31),
            end_time=datetime(2024, 1, 1)
        )
        valid, error = ValidationService.validate_config(bad_config)
        assert valid is False
        assert "before" in error

    def test_validate_empty_symbols(self, sample_config):
        bad_config = replace(sample_config, symbol_universe=[])
        valid, error = ValidationService.validate_config(bad_config)
        assert valid is False
        assert "empty" in error

    def test_validate_order(self):
        order = Order(
            order_id="ord_001",
            simulation_run_id="sim_001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
            price=None,
            status=OrderStatus.PENDING,
            created_at=datetime(2024, 1, 1),
        )
        portfolio = Portfolio(
            portfolio_id="port_001",
            cash=100000.0,
            equity=100000.0,
            used_margin=0.0,
            free_margin=0.0,
            reserved_margin=0.0,
            buying_power=100000.0,
            leverage=1.0,
            exposure=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            positions={},
        )

        valid, error = ValidationService.validate_order(order, portfolio)
        assert valid is True
        assert error is None

    def test_validate_fill(self):
        fill = Fill(
            fill_id="fill_001",
            order_id="ord_001",
            simulation_run_id="sim_001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=1.0,
            price=50000.0,
            fee=10.0,
            slippage=5.0,
            executed_at=datetime(2024, 1, 1),
        )

        valid, error = ValidationService.validate_fill(fill)
        assert valid is True
        assert error is None


class TestLifecycleService:
    """Test LifecycleService"""

    def test_create_simulation(self, sample_config):
        run = LifecycleService.create_simulation(
            run_id="sim_001",
            config=sample_config,
            created_at=datetime(2024, 1, 1),
        )

        assert run.run_id == "sim_001"
        assert run.status == SimulationStatus.CREATED
        assert run.started_at is None

    def test_start_simulation(self, sample_config):
        run = SimulationRun(
            run_id="sim_001",
            config=sample_config,
            status=SimulationStatus.CREATED,
            created_at=datetime(2024, 1, 1),
        )

        started = LifecycleService.start_simulation(
            run=run,
            started_at=datetime(2024, 1, 1, 10, 0),
        )

        assert started.status == SimulationStatus.RUNNING
        assert started.started_at == datetime(2024, 1, 1, 10, 0)

    def test_start_invalid_state_fails(self, sample_config):
        run = SimulationRun(
            run_id="sim_001",
            config=sample_config,
            status=SimulationStatus.COMPLETED,
            created_at=datetime(2024, 1, 1),
        )

        with pytest.raises(ValueError, match="Cannot start"):
            LifecycleService.start_simulation(run, datetime(2024, 1, 1))

    def test_complete_simulation(self, sample_config):
        run = SimulationRun(
            run_id="sim_001",
            config=sample_config,
            status=SimulationStatus.RUNNING,
            created_at=datetime(2024, 1, 1),
            started_at=datetime(2024, 1, 1, 10, 0),
        )

        completed = LifecycleService.complete_simulation(
            run=run,
            completed_at=datetime(2024, 1, 1, 20, 0),
        )

        assert completed.status == SimulationStatus.COMPLETED
        assert completed.completed_at == datetime(2024, 1, 1, 20, 0)

    def test_fail_simulation(self, sample_config):
        run = SimulationRun(
            run_id="sim_001",
            config=sample_config,
            status=SimulationStatus.RUNNING,
            created_at=datetime(2024, 1, 1),
            started_at=datetime(2024, 1, 1, 10, 0),
        )

        failed = LifecycleService.fail_simulation(
            run=run,
            error_message="Test error",
            failed_at=datetime(2024, 1, 1, 15, 0),
        )

        assert failed.status == SimulationStatus.FAILED
        assert failed.error_message == "Test error"
        assert failed.completed_at == datetime(2024, 1, 1, 15, 0)


class TestPortfolioService:
    """Test PortfolioService"""

    def test_create_initial_portfolio(self):
        portfolio = PortfolioService.create_initial_portfolio(
            portfolio_id="port_001",
            initial_capital=100000.0,
            leverage=1.0,
        )

        assert portfolio.cash == 100000.0
        assert portfolio.equity == 100000.0
        assert portfolio.buying_power == 100000.0
        assert len(portfolio.positions) == 0

    def test_apply_fill_creates_position(self):
        portfolio = Portfolio(
            portfolio_id="port_001",
            cash=100000.0,
            equity=100000.0,
            used_margin=0.0,
            free_margin=0.0,
            reserved_margin=0.0,
            buying_power=100000.0,
            leverage=1.0,
            exposure=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            positions={},
        )

        fill = Fill(
            fill_id="fill_001",
            order_id="ord_001",
            simulation_run_id="sim_001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=1.0,
            price=50000.0,
            fee=10.0,
            slippage=5.0,
            executed_at=datetime(2024, 1, 1),
        )

        updated = PortfolioService.apply_fill(
            portfolio=portfolio,
            fill=fill,
            current_prices={"BTCUSDT": 50000.0},
        )

        assert "BTCUSDT" in updated.positions
        assert updated.positions["BTCUSDT"].quantity == 1.0
        assert updated.cash < portfolio.cash

    def test_update_portfolio_prices(self):
        position = Position(
            symbol="BTCUSDT",
            quantity=1.0,
            average_entry_price=50000.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            leverage=1.0,
            required_margin=0.0,
            last_updated_at=datetime(2024, 1, 1),
        )

        portfolio = Portfolio(
            portfolio_id="port_001",
            cash=50000.0,
            equity=100000.0,
            used_margin=0.0,
            free_margin=0.0,
            reserved_margin=0.0,
            buying_power=100000.0,
            leverage=1.0,
            exposure=50000.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            positions={"BTCUSDT": position},
        )

        updated = PortfolioService.update_portfolio_prices(
            portfolio=portfolio,
            current_prices={"BTCUSDT": 51000.0},
        )

        assert updated.positions["BTCUSDT"].unrealized_pnl == 1000.0
        assert updated.equity > portfolio.equity


class TestEquityCurveService:
    """Test EquityCurveService"""

    def test_create_curve(self):
        curve = EquityCurveService.create_curve("sim_001")

        assert curve.simulation_run_id == "sim_001"
        assert len(curve.timestamps) == 0
        assert len(curve.equity_values) == 0

    def test_append_point(self):
        curve = EquityCurve(
            simulation_run_id="sim_001",
            timestamps=[],
            equity_values=[],
        )

        updated = EquityCurveService.append_point(
            curve=curve,
            timestamp=datetime(2024, 1, 1),
            equity=100000.0,
        )

        assert len(updated.timestamps) == 1
        assert len(updated.equity_values) == 1
        assert updated.equity_values[0] == 100000.0


class TestPerformanceService:
    """Test PerformanceService"""

    def test_calculate_metrics_empty_trades(self):
        curve = EquityCurve(
            simulation_run_id="sim_001",
            timestamps=[datetime(2024, 1, 1)],
            equity_values=[100000.0],
        )

        metrics = PerformanceService.calculate_metrics(
            trades=[],
            equity_curve=curve,
            initial_capital=100000.0,
        )

        assert metrics.trade_count == 0
        assert metrics.win_rate == 0.0

    def test_calculate_max_drawdown(self):
        curve = EquityCurve(
            simulation_run_id="sim_001",
            timestamps=[
                datetime(2024, 1, 1),
                datetime(2024, 1, 2),
                datetime(2024, 1, 3),
                datetime(2024, 1, 4),
            ],
            equity_values=[100000.0, 110000.0, 95000.0, 105000.0],
        )

        max_dd = PerformanceService._calculate_max_drawdown(curve)
        assert max_dd > 0
        assert max_dd < 0.2

    def test_calculate_sharpe(self):
        returns = [0.01, 0.02, -0.01, 0.015, 0.005]
        sharpe = PerformanceService._calculate_sharpe(returns)
        assert isinstance(sharpe, float)
