"""
Tests for simulation domain models

Validates immutability, type constraints, and domain invariants.
"""

import pytest
from datetime import datetime
from dataclasses import FrozenInstanceError

from ml_service.simulation.models import (
    OrderSide,
    OrderType,
    OrderStatus,
    SimulationStatus,
    MarketSnapshot,
    ExecutionAssumption,
    SimulationConfig,
    Order,
    Fill,
    Position,
    Portfolio,
    Trade,
    EquityCurve,
    PerformanceMetrics,
    SimulationReport,
    SimulationRun,
)


class TestEnums:
    """Test enum definitions"""

    def test_order_side_values(self):
        assert OrderSide.BUY.value == "BUY"
        assert OrderSide.SELL.value == "SELL"

    def test_order_type_values(self):
        assert OrderType.MARKET.value == "MARKET"
        assert OrderType.LIMIT.value == "LIMIT"
        assert OrderType.STOP.value == "STOP"

    def test_order_status_values(self):
        assert OrderStatus.PENDING.value == "PENDING"
        assert OrderStatus.FILLED.value == "FILLED"
        assert OrderStatus.CANCELLED.value == "CANCELLED"

    def test_simulation_status_values(self):
        assert SimulationStatus.CREATED.value == "CREATED"
        assert SimulationStatus.RUNNING.value == "RUNNING"
        assert SimulationStatus.COMPLETED.value == "COMPLETED"


class TestMarketSnapshot:
    """Test MarketSnapshot value object"""

    def test_create_snapshot(self):
        snapshot = MarketSnapshot(
            timestamp=datetime(2024, 1, 1, 12, 0),
            symbol="BTCUSDT",
            mid_price=50000.0,
            bid=49990.0,
            ask=50010.0,
        )

        assert snapshot.symbol == "BTCUSDT"
        assert snapshot.mid_price == 50000.0
        assert snapshot.bid == 49990.0

    def test_snapshot_immutability(self):
        snapshot = MarketSnapshot(
            timestamp=datetime(2024, 1, 1),
            symbol="BTCUSDT",
            mid_price=50000.0,
        )

        with pytest.raises(FrozenInstanceError):
            snapshot.mid_price = 51000.0


class TestExecutionAssumption:
    """Test ExecutionAssumption value object"""

    def test_create_assumption(self):
        assumption = ExecutionAssumption(
            commission=0.1,
            maker_fee=0.0002,
            taker_fee=0.0005,
            slippage=0.0001,
            latency=100,
            spread_model="FIXED",
            funding_fee=0.0,
            borrow_fee=0.0,
        )

        assert assumption.maker_fee == 0.0002
        assert assumption.latency == 100

    def test_assumption_immutability(self):
        assumption = ExecutionAssumption(
            commission=0.1,
            maker_fee=0.0002,
            taker_fee=0.0005,
            slippage=0.0001,
            latency=100,
            spread_model="FIXED",
            funding_fee=0.0,
            borrow_fee=0.0,
        )

        with pytest.raises(FrozenInstanceError):
            assumption.commission = 0.2


class TestSimulationConfig:
    """Test SimulationConfig aggregate"""

    def test_create_config(self):
        assumption = ExecutionAssumption(
            commission=0.1,
            maker_fee=0.0002,
            taker_fee=0.0005,
            slippage=0.0001,
            latency=100,
            spread_model="FIXED",
            funding_fee=0.0,
            borrow_fee=0.0,
        )

        config = SimulationConfig(
            symbol_universe=["BTCUSDT", "ETHUSDT"],
            timeframe="1h",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 12, 31),
            initial_capital=100000.0,
            execution_assumption=assumption,
            model_version_id="model_v1",
            dataset_snapshot_id="ds_001",
            config_hash="abc123",
        )

        assert config.initial_capital == 100000.0
        assert len(config.symbol_universe) == 2


class TestOrder:
    """Test Order entity"""

    def test_create_order(self):
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

        assert order.order_id == "ord_001"
        assert order.side == OrderSide.BUY
        assert order.quantity == 1.0

    def test_order_immutability(self):
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

        with pytest.raises(FrozenInstanceError):
            order.status = OrderStatus.FILLED


class TestFill:
    """Test Fill entity"""

    def test_create_fill(self):
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

        assert fill.fill_id == "fill_001"
        assert fill.quantity == 1.0
        assert fill.price == 50000.0


class TestPosition:
    """Test Position entity"""

    def test_create_position(self):
        position = Position(
            symbol="BTCUSDT",
            quantity=1.0,
            average_entry_price=50000.0,
            unrealized_pnl=100.0,
            realized_pnl=0.0,
            leverage=1.0,
            required_margin=0.0,
            last_updated_at=datetime(2024, 1, 1),
        )

        assert position.symbol == "BTCUSDT"
        assert position.quantity == 1.0


class TestPortfolio:
    """Test Portfolio aggregate"""

    def test_create_portfolio(self):
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

        assert portfolio.cash == 100000.0
        assert portfolio.equity == 100000.0
        assert len(portfolio.positions) == 0


class TestTrade:
    """Test Trade entity"""

    def test_create_trade(self):
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

        assert trade.realized_pnl == 1000.0
        assert trade.holding_time_seconds == 3600.0


class TestEquityCurve:
    """Test EquityCurve entity"""

    def test_create_equity_curve(self):
        curve = EquityCurve(
            simulation_run_id="sim_001",
            timestamps=[datetime(2024, 1, 1), datetime(2024, 1, 2)],
            equity_values=[100000.0, 101000.0],
        )

        assert len(curve.timestamps) == 2
        assert curve.equity_values[1] == 101000.0

    def test_equity_curve_validates_lengths(self):
        with pytest.raises(ValueError, match="same length"):
            EquityCurve(
                simulation_run_id="sim_001",
                timestamps=[datetime(2024, 1, 1)],
                equity_values=[100000.0, 101000.0],
            )


class TestPerformanceMetrics:
    """Test PerformanceMetrics aggregate"""

    def test_create_metrics(self):
        metrics = PerformanceMetrics(
            sharpe=1.5,
            sortino=1.8,
            calmar=2.0,
            omega=1.2,
            sterling=1.5,
            mar=1.3,
            profit_factor=2.5,
            expectancy=100.0,
            kelly=0.25,
            recovery_factor=3.0,
            ulcer_index=5.0,
            tail_ratio=1.5,
            skew=0.5,
            kurtosis=3.0,
            cagr=0.25,
            alpha=0.05,
            beta=0.8,
            information_ratio=1.2,
            tracking_error=0.05,
            var=0.02,
            cvar=0.03,
            trade_count=100,
            win_rate=0.6,
            average_trade=50.0,
            median_trade=40.0,
            max_drawdown=0.15,
            exposure_time=0.8,
            average_holding_time=3600.0,
            brier_score=0.1,
            ece=0.05,
            profit_capture_ratio=0.75,
        )

        assert metrics.sharpe == 1.5
        assert metrics.trade_count == 100
        assert metrics.win_rate == 0.6


class TestSimulationRun:
    """Test SimulationRun aggregate root"""

    def test_create_simulation_run(self):
        assumption = ExecutionAssumption(
            commission=0.1,
            maker_fee=0.0002,
            taker_fee=0.0005,
            slippage=0.0001,
            latency=100,
            spread_model="FIXED",
            funding_fee=0.0,
            borrow_fee=0.0,
        )

        config = SimulationConfig(
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

        run = SimulationRun(
            run_id="sim_001",
            config=config,
            status=SimulationStatus.CREATED,
            created_at=datetime(2024, 1, 1),
        )

        assert run.run_id == "sim_001"
        assert run.status == SimulationStatus.CREATED
        assert run.started_at is None
