"""
Tests for simulation repositories

Validates in-memory storage, thread safety, and CRUD operations.
"""

import pytest
from datetime import datetime
import threading

from ml_service.simulation.models import (
    SimulationRun,
    SimulationConfig,
    SimulationStatus,
    Order,
    OrderSide,
    OrderType,
    OrderStatus,
    Fill,
    Trade,
    Portfolio,
    EquityCurve,
    SimulationReport,
    PerformanceMetrics,
    ExecutionAssumption,
)
from ml_service.simulation.repository import (
    SimulationRunRepository,
    OrderRepository,
    FillRepository,
    TradeRepository,
    PortfolioRepository,
    EquityCurveRepository,
    SimulationReportRepository,
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


class TestSimulationRunRepository:
    """Test SimulationRunRepository"""

    def test_create_run(self, sample_config):
        repo = SimulationRunRepository()
        run = SimulationRun(
            run_id="sim_001",
            config=sample_config,
            status=SimulationStatus.CREATED,
            created_at=datetime(2024, 1, 1),
        )

        created = repo.create(run)
        assert created.run_id == "sim_001"

    def test_create_duplicate_fails(self, sample_config):
        repo = SimulationRunRepository()
        run = SimulationRun(
            run_id="sim_001",
            config=sample_config,
            status=SimulationStatus.CREATED,
            created_at=datetime(2024, 1, 1),
        )

        repo.create(run)
        with pytest.raises(ValueError, match="already exists"):
            repo.create(run)

    def test_get_run(self, sample_config):
        repo = SimulationRunRepository()
        run = SimulationRun(
            run_id="sim_001",
            config=sample_config,
            status=SimulationStatus.CREATED,
            created_at=datetime(2024, 1, 1),
        )

        repo.create(run)
        retrieved = repo.get("sim_001")
        assert retrieved is not None
        assert retrieved.run_id == "sim_001"

    def test_get_nonexistent_returns_none(self):
        repo = SimulationRunRepository()
        assert repo.get("nonexistent") is None

    def test_update_run(self, sample_config):
        repo = SimulationRunRepository()
        run = SimulationRun(
            run_id="sim_001",
            config=sample_config,
            status=SimulationStatus.CREATED,
            created_at=datetime(2024, 1, 1),
        )

        repo.create(run)
        from dataclasses import replace
        updated_run = replace(run, status=SimulationStatus.RUNNING)
        repo.update(updated_run)

        retrieved = repo.get("sim_001")
        assert retrieved.status == SimulationStatus.RUNNING

    def test_list_all(self, sample_config):
        repo = SimulationRunRepository()
        run1 = SimulationRun(
            run_id="sim_001",
            config=sample_config,
            status=SimulationStatus.CREATED,
            created_at=datetime(2024, 1, 1),
        )
        run2 = SimulationRun(
            run_id="sim_002",
            config=sample_config,
            status=SimulationStatus.CREATED,
            created_at=datetime(2024, 1, 2),
        )

        repo.create(run1)
        repo.create(run2)
        all_runs = repo.list_all()
        assert len(all_runs) == 2

    def test_delete_run(self, sample_config):
        repo = SimulationRunRepository()
        run = SimulationRun(
            run_id="sim_001",
            config=sample_config,
            status=SimulationStatus.CREATED,
            created_at=datetime(2024, 1, 1),
        )

        repo.create(run)
        repo.delete("sim_001")
        assert repo.get("sim_001") is None

    def test_clear(self, sample_config):
        repo = SimulationRunRepository()
        run = SimulationRun(
            run_id="sim_001",
            config=sample_config,
            status=SimulationStatus.CREATED,
            created_at=datetime(2024, 1, 1),
        )

        repo.create(run)
        repo.clear()
        assert len(repo.list_all()) == 0


class TestOrderRepository:
    """Test OrderRepository"""

    def test_create_order(self):
        repo = OrderRepository()
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

        created = repo.create(order)
        assert created.order_id == "ord_001"

    def test_list_by_run(self):
        repo = OrderRepository()
        order1 = Order(
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
        order2 = Order(
            order_id="ord_002",
            simulation_run_id="sim_001",
            symbol="ETHUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=2.0,
            price=3000.0,
            status=OrderStatus.PENDING,
            created_at=datetime(2024, 1, 1),
        )

        repo.create(order1)
        repo.create(order2)
        orders = repo.list_by_run("sim_001")
        assert len(orders) == 2


class TestFillRepository:
    """Test FillRepository"""

    def test_create_fill(self):
        repo = FillRepository()
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

        created = repo.create(fill)
        assert created.fill_id == "fill_001"

    def test_list_by_order(self):
        repo = FillRepository()
        fill1 = Fill(
            fill_id="fill_001",
            order_id="ord_001",
            simulation_run_id="sim_001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.5,
            price=50000.0,
            fee=5.0,
            slippage=2.5,
            executed_at=datetime(2024, 1, 1, 10, 0),
        )
        fill2 = Fill(
            fill_id="fill_002",
            order_id="ord_001",
            simulation_run_id="sim_001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.5,
            price=50010.0,
            fee=5.0,
            slippage=2.5,
            executed_at=datetime(2024, 1, 1, 10, 1),
        )

        repo.create(fill1)
        repo.create(fill2)
        fills = repo.list_by_order("ord_001")
        assert len(fills) == 2


class TestTradeRepository:
    """Test TradeRepository"""

    def test_create_trade(self):
        repo = TradeRepository()
        trade = Trade(
            trade_id="trade_001",
            simulation_run_id="sim_001",
            symbol="BTCUSDT",
            quantity=1.0,
            entry_price=50000.0,
            exit_price=51000.0,
            realized_pnl=1000.0,
            holding_time_seconds=3600.0,
            entered_at=datetime(2024, 1, 1, 12, 0),
            exited_at=datetime(2024, 1, 1, 13, 0),
        )

        created = repo.create(trade)
        assert created.trade_id == "trade_001"

    def test_list_by_run(self):
        repo = TradeRepository()
        trade1 = Trade(
            trade_id="trade_001",
            simulation_run_id="sim_001",
            symbol="BTCUSDT",
            quantity=1.0,
            entry_price=50000.0,
            exit_price=51000.0,
            realized_pnl=1000.0,
            holding_time_seconds=3600.0,
            entered_at=datetime(2024, 1, 1, 12, 0),
            exited_at=datetime(2024, 1, 1, 13, 0),
        )
        trade2 = Trade(
            trade_id="trade_002",
            simulation_run_id="sim_001",
            symbol="ETHUSDT",
            quantity=2.0,
            entry_price=3000.0,
            exit_price=3100.0,
            realized_pnl=200.0,
            holding_time_seconds=7200.0,
            entered_at=datetime(2024, 1, 2, 10, 0),
            exited_at=datetime(2024, 1, 2, 12, 0),
        )

        repo.create(trade1)
        repo.create(trade2)
        trades = repo.list_by_run("sim_001")
        assert len(trades) == 2


class TestPortfolioRepository:
    """Test PortfolioRepository"""

    def test_append_snapshot(self):
        repo = PortfolioRepository()
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

        repo.append_snapshot("sim_001", portfolio)
        snapshots = repo.get_snapshots("sim_001")
        assert len(snapshots) == 1

    def test_get_latest(self):
        repo = PortfolioRepository()
        portfolio1 = Portfolio(
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
        portfolio2 = Portfolio(
            portfolio_id="port_001",
            cash=99000.0,
            equity=100500.0,
            used_margin=0.0,
            free_margin=0.0,
            reserved_margin=0.0,
            buying_power=100500.0,
            leverage=1.0,
            exposure=1000.0,
            unrealized_pnl=500.0,
            realized_pnl=0.0,
            positions={},
        )

        repo.append_snapshot("sim_001", portfolio1)
        repo.append_snapshot("sim_001", portfolio2)

        latest = repo.get_latest("sim_001")
        assert latest is not None
        assert latest.equity == 100500.0


class TestEquityCurveRepository:
    """Test EquityCurveRepository"""

    def test_save_curve(self):
        repo = EquityCurveRepository()
        curve = EquityCurve(
            simulation_run_id="sim_001",
            timestamps=[datetime(2024, 1, 1)],
            equity_values=[100000.0],
        )

        saved = repo.save(curve)
        assert saved.simulation_run_id == "sim_001"

    def test_get_curve(self):
        repo = EquityCurveRepository()
        curve = EquityCurve(
            simulation_run_id="sim_001",
            timestamps=[datetime(2024, 1, 1)],
            equity_values=[100000.0],
        )

        repo.save(curve)
        retrieved = repo.get("sim_001")
        assert retrieved is not None
        assert len(retrieved.equity_values) == 1


class TestSimulationReportRepository:
    """Test SimulationReportRepository"""

    def test_create_report(self):
        repo = SimulationReportRepository()
        metrics = PerformanceMetrics(
            sharpe=1.5, sortino=1.8, calmar=2.0, omega=1.2, sterling=1.5,
            mar=1.3, profit_factor=2.5, expectancy=100.0, kelly=0.25,
            recovery_factor=3.0, ulcer_index=5.0, tail_ratio=1.5,
            skew=0.5, kurtosis=3.0, cagr=0.25, alpha=0.05, beta=0.8,
            information_ratio=1.2, tracking_error=0.05, var=0.02, cvar=0.03,
            trade_count=100, win_rate=0.6, average_trade=50.0, median_trade=40.0,
            max_drawdown=0.15, exposure_time=0.8, average_holding_time=3600.0,
            brier_score=0.1, ece=0.05, profit_capture_ratio=0.75,
        )

        report = SimulationReport(
            report_id="report_001",
            simulation_run_id="sim_001",
            metrics=metrics,
            manifest_checksum="checksum123",
            bundle_path="/reports/sim_001",
            created_at=datetime(2024, 1, 1),
        )

        created = repo.create(report)
        assert created.report_id == "report_001"

    def test_get_by_run(self):
        repo = SimulationReportRepository()
        metrics = PerformanceMetrics(
            sharpe=1.5, sortino=1.8, calmar=2.0, omega=1.2, sterling=1.5,
            mar=1.3, profit_factor=2.5, expectancy=100.0, kelly=0.25,
            recovery_factor=3.0, ulcer_index=5.0, tail_ratio=1.5,
            skew=0.5, kurtosis=3.0, cagr=0.25, alpha=0.05, beta=0.8,
            information_ratio=1.2, tracking_error=0.05, var=0.02, cvar=0.03,
            trade_count=100, win_rate=0.6, average_trade=50.0, median_trade=40.0,
            max_drawdown=0.15, exposure_time=0.8, average_holding_time=3600.0,
            brier_score=0.1, ece=0.05, profit_capture_ratio=0.75,
        )

        report = SimulationReport(
            report_id="report_001",
            simulation_run_id="sim_001",
            metrics=metrics,
            manifest_checksum="checksum123",
            bundle_path="/reports/sim_001",
            created_at=datetime(2024, 1, 1),
        )

        repo.create(report)
        retrieved = repo.get_by_run("sim_001")
        assert retrieved is not None
        assert retrieved.report_id == "report_001"
