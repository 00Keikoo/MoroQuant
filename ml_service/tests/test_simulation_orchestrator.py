"""
Tests for simulation orchestrator

Validates orchestration of simulation lifecycle and coordination.
"""

import pytest
from datetime import datetime

from ml_service.simulation.models import (
    SimulationConfig,
    SimulationStatus,
    Order,
    OrderSide,
    OrderType,
    OrderStatus,
    Fill,
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
from ml_service.simulation.orchestrator import SimulationOrchestrator


@pytest.fixture
def orchestrator():
    return SimulationOrchestrator(
        run_repo=SimulationRunRepository(),
        order_repo=OrderRepository(),
        fill_repo=FillRepository(),
        trade_repo=TradeRepository(),
        portfolio_repo=PortfolioRepository(),
        equity_curve_repo=EquityCurveRepository(),
        report_repo=SimulationReportRepository(),
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


class TestSimulationOrchestrator:
    """Test SimulationOrchestrator"""

    def test_create_simulation(self, orchestrator, sample_config):
        run = orchestrator.create_simulation(config=sample_config, run_id="sim_001")

        assert run.run_id == "sim_001"
        assert run.status == SimulationStatus.CREATED

        retrieved = orchestrator.run_repo.get("sim_001")
        assert retrieved is not None

    def test_create_simulation_auto_id(self, orchestrator, sample_config):
        run = orchestrator.create_simulation(config=sample_config)

        assert run.run_id.startswith("sim_")
        assert run.status == SimulationStatus.CREATED

    def test_create_simulation_invalid_config(self, orchestrator, sample_config):
        from dataclasses import replace
        bad_config = replace(sample_config, initial_capital=-1000)

        with pytest.raises(ValueError, match="Invalid configuration"):
            orchestrator.create_simulation(config=bad_config)

    def test_start_simulation(self, orchestrator, sample_config):
        run = orchestrator.create_simulation(config=sample_config, run_id="sim_001")
        started = orchestrator.start_simulation("sim_001")

        assert started.status == SimulationStatus.RUNNING
        assert started.started_at is not None

    def test_complete_simulation(self, orchestrator, sample_config):
        run = orchestrator.create_simulation(config=sample_config, run_id="sim_001")
        orchestrator.start_simulation("sim_001")
        completed = orchestrator.complete_simulation("sim_001")

        assert completed.status == SimulationStatus.COMPLETED
        assert completed.completed_at is not None

    def test_fail_simulation(self, orchestrator, sample_config):
        run = orchestrator.create_simulation(config=sample_config, run_id="sim_001")
        orchestrator.start_simulation("sim_001")
        failed = orchestrator.fail_simulation("sim_001", "Test error")

        assert failed.status == SimulationStatus.FAILED
        assert failed.error_message == "Test error"

    def test_cancel_simulation(self, orchestrator, sample_config):
        run = orchestrator.create_simulation(config=sample_config, run_id="sim_001")
        orchestrator.start_simulation("sim_001")
        cancelled = orchestrator.cancel_simulation("sim_001")

        assert cancelled.status == SimulationStatus.CANCELLED

    def test_initialize_portfolio(self, orchestrator, sample_config):
        run = orchestrator.create_simulation(config=sample_config, run_id="sim_001")
        portfolio = orchestrator.initialize_portfolio("sim_001", 100000.0)

        assert portfolio.cash == 100000.0
        assert portfolio.equity == 100000.0

        retrieved = orchestrator.portfolio_repo.get_latest("sim_001")
        assert retrieved is not None

    def test_record_order(self, orchestrator, sample_config):
        run = orchestrator.create_simulation(config=sample_config, run_id="sim_001")
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

        recorded = orchestrator.record_order(order)
        assert recorded.order_id == "ord_001"

        retrieved = orchestrator.order_repo.get("ord_001")
        assert retrieved is not None

    def test_record_fill(self, orchestrator, sample_config):
        run = orchestrator.create_simulation(config=sample_config, run_id="sim_001")
        orchestrator.initialize_portfolio("sim_001", 100000.0)

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

        portfolio = orchestrator.record_fill(
            fill=fill,
            current_prices={"BTCUSDT": 50000.0},
        )

        assert "BTCUSDT" in portfolio.positions
        assert portfolio.cash < 100000.0

    def test_update_portfolio_prices(self, orchestrator, sample_config):
        run = orchestrator.create_simulation(config=sample_config, run_id="sim_001")
        orchestrator.initialize_portfolio("sim_001", 100000.0)

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

        orchestrator.record_fill(fill, {"BTCUSDT": 50000.0})
        updated = orchestrator.update_portfolio_prices(
            "sim_001",
            {"BTCUSDT": 51000.0},
        )

        assert updated.unrealized_pnl > 0

    def test_record_equity_point(self, orchestrator, sample_config):
        run = orchestrator.create_simulation(config=sample_config, run_id="sim_001")
        curve = orchestrator.record_equity_point(
            "sim_001",
            datetime(2024, 1, 1),
            100000.0,
        )

        assert len(curve.equity_values) == 1
        assert curve.equity_values[0] == 100000.0

    def test_record_multiple_equity_points(self, orchestrator, sample_config):
        run = orchestrator.create_simulation(config=sample_config, run_id="sim_001")

        orchestrator.record_equity_point("sim_001", datetime(2024, 1, 1), 100000.0)
        orchestrator.record_equity_point("sim_001", datetime(2024, 1, 2), 101000.0)
        curve = orchestrator.record_equity_point("sim_001", datetime(2024, 1, 3), 102000.0)

        assert len(curve.equity_values) == 3
        assert curve.equity_values[-1] == 102000.0

    def test_generate_report(self, orchestrator, sample_config):
        run = orchestrator.create_simulation(config=sample_config, run_id="sim_001")
        orchestrator.record_equity_point("sim_001", datetime(2024, 1, 1), 100000.0)

        report = orchestrator.generate_report("sim_001")

        assert report.simulation_run_id == "sim_001"
        assert report.metrics is not None
        assert report.metrics.trade_count == 0

    def test_get_simulation_summary(self, orchestrator, sample_config):
        run = orchestrator.create_simulation(config=sample_config, run_id="sim_001")
        orchestrator.initialize_portfolio("sim_001", 100000.0)
        orchestrator.record_equity_point("sim_001", datetime(2024, 1, 1), 100000.0)

        summary = orchestrator.get_simulation_summary("sim_001")

        assert summary["run"].run_id == "sim_001"
        assert summary["order_count"] == 0
        assert summary["fill_count"] == 0
        assert summary["trade_count"] == 0
        assert summary["final_portfolio"] is not None
        assert summary["equity_curve_length"] == 1

    def test_full_simulation_workflow(self, orchestrator, sample_config):
        run = orchestrator.create_simulation(config=sample_config, run_id="sim_001")
        orchestrator.start_simulation("sim_001")
        orchestrator.initialize_portfolio("sim_001", 100000.0)

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
        orchestrator.record_order(order)

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
        orchestrator.record_fill(fill, {"BTCUSDT": 50000.0})

        orchestrator.record_equity_point("sim_001", datetime(2024, 1, 1), 100000.0)
        orchestrator.complete_simulation("sim_001")

        report = orchestrator.generate_report("sim_001")

        summary = orchestrator.get_simulation_summary("sim_001")
        assert summary["run"].status == SimulationStatus.COMPLETED
        assert summary["order_count"] == 1
        assert summary["fill_count"] == 1
        assert summary["report"] is not None
