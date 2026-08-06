"""
Tests for Portfolio Service - Aggregate Orchestrator

Tests the complete portfolio lifecycle through the orchestration layer.
"""

import pytest
from datetime import datetime
from ml_service.portfolio.service import (
    PortfolioService,
    FillEvent,
    PortfolioUpdated,
    LiquidationDetected,
)
from ml_service.portfolio.ledger import LedgerService
from ml_service.portfolio.position import PositionService
from ml_service.portfolio.equity import EquityService
from ml_service.portfolio.margin import MarginService
from ml_service.portfolio.models import (
    AccountType,
    PositionType,
    PositionMarginContext,
    PortfolioLifecycle,
)


@pytest.fixture
def portfolio_service():
    ledger = LedgerService()
    position = PositionService()
    equity = EquityService()
    margin = MarginService()
    return PortfolioService(ledger, position, equity, margin)


@pytest.fixture
def timestamp():
    return datetime(2024, 1, 1, 12, 0, 0)


class TestPortfolioInitialization:
    def test_initialize_empty_portfolio(self, portfolio_service, timestamp):
        portfolio = portfolio_service.initialize_portfolio(
            portfolio_id="test_portfolio",
            initial_cash=10000.0,
            account_type=AccountType.SPOT,
            timestamp=timestamp
        )

        assert portfolio.portfolio_id == "test_portfolio"
        assert portfolio.account_type == AccountType.SPOT
        assert portfolio.lifecycle == PortfolioLifecycle.ACTIVE
        assert portfolio.cash_ledger.ledger_cash_balance == 10000.0
        assert portfolio.cash_ledger.available_cash == 10000.0
        assert portfolio.cash_ledger.reserved_cash == 0.0
        assert portfolio.cash_ledger.locked_cash == 0.0
        assert portfolio.equity == 10000.0
        assert len(portfolio.positions) == 0
        assert len(portfolio.holdings) == 0
        assert len(portfolio.ledger) == 0

    def test_initialize_futures_portfolio(self, portfolio_service, timestamp):
        portfolio = portfolio_service.initialize_portfolio(
            portfolio_id="futures_portfolio",
            initial_cash=5000.0,
            account_type=AccountType.FUTURES,
            timestamp=timestamp
        )

        assert portfolio.account_type == AccountType.FUTURES
        assert portfolio.equity == 5000.0
        assert portfolio.margin_ledger.margin_ratio == 0.0

    def test_initialize_with_zero_cash(self, portfolio_service, timestamp):
        portfolio = portfolio_service.initialize_portfolio(
            portfolio_id="empty_portfolio",
            initial_cash=0.0,
            timestamp=timestamp
        )

        assert portfolio.lifecycle == PortfolioLifecycle.EMPTY
        assert portfolio.equity == 0.0

    def test_initialize_with_negative_cash_raises_error(self, portfolio_service, timestamp):
        with pytest.raises(ValueError, match="initial_cash cannot be negative"):
            portfolio_service.initialize_portfolio(
                portfolio_id="invalid",
                initial_cash=-1000.0,
                timestamp=timestamp
            )


class TestSpotTrading:
    def test_apply_spot_buy_fill(self, portfolio_service, timestamp):
        portfolio = portfolio_service.initialize_portfolio(
            portfolio_id="spot_portfolio",
            initial_cash=10000.0,
            account_type=AccountType.SPOT,
            timestamp=timestamp
        )

        fill = FillEvent(
            symbol="BTC",
            position_type=PositionType.SPOT,
            quantity=0.1,
            execution_price=50000.0,
            fee_amount=5.0,
            timestamp=timestamp
        )

        new_portfolio, events = portfolio_service.apply_fill(portfolio, fill)

        assert new_portfolio.cash_ledger.ledger_cash_balance == 10000.0 - 5000.0 - 5.0
        assert "BTC" in new_portfolio.holdings
        assert new_portfolio.holdings["BTC"].quantity == 0.1
        assert new_portfolio.holdings["BTC"].mark_price == 50000.0
        assert new_portfolio.holdings["BTC"].market_value == 5000.0
        assert len(new_portfolio.ledger) == 2

    def test_apply_spot_sell_fill(self, portfolio_service, timestamp):
        portfolio = portfolio_service.initialize_portfolio(
            portfolio_id="spot_portfolio",
            initial_cash=10000.0,
            account_type=AccountType.SPOT,
            timestamp=timestamp
        )

        buy_fill = FillEvent(
            symbol="BTC",
            position_type=PositionType.SPOT,
            quantity=0.1,
            execution_price=50000.0,
            fee_amount=5.0,
            timestamp=timestamp
        )

        portfolio, _ = portfolio_service.apply_fill(portfolio, buy_fill)

        sell_fill = FillEvent(
            symbol="BTC",
            position_type=PositionType.SPOT,
            quantity=-0.05,
            execution_price=52000.0,
            fee_amount=2.6,
            timestamp=timestamp
        )

        new_portfolio, events = portfolio_service.apply_fill(portfolio, sell_fill)

        assert new_portfolio.holdings["BTC"].quantity == 0.05
        assert new_portfolio.cash_ledger.ledger_cash_balance > portfolio.cash_ledger.ledger_cash_balance

    def test_apply_spot_sell_without_holding_raises_error(self, portfolio_service, timestamp):
        portfolio = portfolio_service.initialize_portfolio(
            portfolio_id="spot_portfolio",
            initial_cash=10000.0,
            timestamp=timestamp
        )

        sell_fill = FillEvent(
            symbol="BTC",
            position_type=PositionType.SPOT,
            quantity=-0.1,
            execution_price=50000.0,
            fee_amount=5.0,
            timestamp=timestamp
        )

        with pytest.raises(ValueError, match="no holding exists"):
            portfolio_service.apply_fill(portfolio, sell_fill)


class TestFuturesTrading:
    def test_apply_futures_long_fill(self, portfolio_service, timestamp):
        portfolio = portfolio_service.initialize_portfolio(
            portfolio_id="futures_portfolio",
            initial_cash=10000.0,
            account_type=AccountType.FUTURES,
            timestamp=timestamp
        )

        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0
        )

        fill = FillEvent(
            symbol="BTCUSDT",
            position_type=PositionType.FUTURES,
            quantity=1.0,
            execution_price=50000.0,
            fee_amount=5.0,
            timestamp=timestamp,
            margin_context=margin_context
        )

        new_portfolio, events = portfolio_service.apply_fill(portfolio, fill)

        assert "BTCUSDT" in new_portfolio.positions
        position = new_portfolio.positions["BTCUSDT"]
        assert position.quantity == 1.0
        assert position.average_entry_price == 50000.0
        assert position.position_type == PositionType.FUTURES
        assert position.margin_context.leverage == 10.0
        assert new_portfolio.cash_ledger.ledger_cash_balance == 10000.0 - 5.0
        assert len(events) == 1

    def test_apply_futures_short_fill(self, portfolio_service, timestamp):
        portfolio = portfolio_service.initialize_portfolio(
            portfolio_id="futures_portfolio",
            initial_cash=10000.0,
            account_type=AccountType.FUTURES,
            timestamp=timestamp
        )

        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0
        )

        fill = FillEvent(
            symbol="BTCUSDT",
            position_type=PositionType.FUTURES,
            quantity=-1.0,
            execution_price=50000.0,
            fee_amount=5.0,
            timestamp=timestamp,
            margin_context=margin_context
        )

        new_portfolio, events = portfolio_service.apply_fill(portfolio, fill)

        assert "BTCUSDT" in new_portfolio.positions
        position = new_portfolio.positions["BTCUSDT"]
        assert position.quantity == -1.0
        assert position.average_entry_price == 50000.0

    def test_apply_futures_increase_position(self, portfolio_service, timestamp):
        portfolio = portfolio_service.initialize_portfolio(
            portfolio_id="futures_portfolio",
            initial_cash=10000.0,
            account_type=AccountType.FUTURES,
            timestamp=timestamp
        )

        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0
        )

        fill1 = FillEvent(
            symbol="BTCUSDT",
            position_type=PositionType.FUTURES,
            quantity=1.0,
            execution_price=50000.0,
            fee_amount=5.0,
            timestamp=timestamp,
            margin_context=margin_context
        )

        portfolio, _ = portfolio_service.apply_fill(portfolio, fill1)

        fill2 = FillEvent(
            symbol="BTCUSDT",
            position_type=PositionType.FUTURES,
            quantity=0.5,
            execution_price=51000.0,
            fee_amount=2.55,
            timestamp=timestamp,
            margin_context=margin_context
        )

        new_portfolio, events = portfolio_service.apply_fill(portfolio, fill2)

        position = new_portfolio.positions["BTCUSDT"]
        assert position.quantity == 1.5
        expected_avg = (1.0 * 50000.0 + 0.5 * 51000.0) / 1.5
        assert abs(position.average_entry_price - expected_avg) < 1e-6

    def test_apply_futures_reduce_position(self, portfolio_service, timestamp):
        portfolio = portfolio_service.initialize_portfolio(
            portfolio_id="futures_portfolio",
            initial_cash=10000.0,
            account_type=AccountType.FUTURES,
            timestamp=timestamp
        )

        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0
        )

        fill1 = FillEvent(
            symbol="BTCUSDT",
            position_type=PositionType.FUTURES,
            quantity=1.0,
            execution_price=50000.0,
            fee_amount=5.0,
            timestamp=timestamp,
            margin_context=margin_context
        )

        portfolio, _ = portfolio_service.apply_fill(portfolio, fill1)

        fill2 = FillEvent(
            symbol="BTCUSDT",
            position_type=PositionType.FUTURES,
            quantity=-0.5,
            execution_price=52000.0,
            fee_amount=2.6,
            timestamp=timestamp
        )

        new_portfolio, events = portfolio_service.apply_fill(portfolio, fill2)

        position = new_portfolio.positions["BTCUSDT"]
        assert position.quantity == 0.5
        realized_pnl = (52000.0 - 50000.0) * 0.5
        assert abs(new_portfolio.cash_ledger.ledger_cash_balance - (10000.0 - 5.0 - 2.6 + realized_pnl)) < 1e-6


class TestMarketPriceUpdates:
    def test_update_market_prices_spot(self, portfolio_service, timestamp):
        portfolio = portfolio_service.initialize_portfolio(
            portfolio_id="spot_portfolio",
            initial_cash=10000.0,
            account_type=AccountType.SPOT,
            timestamp=timestamp
        )

        fill = FillEvent(
            symbol="BTC",
            position_type=PositionType.SPOT,
            quantity=0.1,
            execution_price=50000.0,
            fee_amount=5.0,
            timestamp=timestamp
        )

        portfolio, _ = portfolio_service.apply_fill(portfolio, fill)

        mark_prices = {"BTC": 55000.0}
        new_portfolio, events = portfolio_service.update_market_prices(
            portfolio, mark_prices, timestamp
        )

        assert new_portfolio.holdings["BTC"].mark_price == 55000.0
        assert new_portfolio.holdings["BTC"].market_value == 0.1 * 55000.0
        assert len(events) == 1
        assert isinstance(events[0], PortfolioUpdated)

    def test_update_market_prices_futures(self, portfolio_service, timestamp):
        portfolio = portfolio_service.initialize_portfolio(
            portfolio_id="futures_portfolio",
            initial_cash=10000.0,
            account_type=AccountType.FUTURES,
            timestamp=timestamp
        )

        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0
        )

        fill = FillEvent(
            symbol="BTCUSDT",
            position_type=PositionType.FUTURES,
            quantity=1.0,
            execution_price=50000.0,
            fee_amount=5.0,
            timestamp=timestamp,
            margin_context=margin_context
        )

        portfolio, _ = portfolio_service.apply_fill(portfolio, fill)

        mark_prices = {"BTCUSDT": 52000.0}
        new_portfolio, events = portfolio_service.update_market_prices(
            portfolio, mark_prices, timestamp
        )

        position = new_portfolio.positions["BTCUSDT"]
        expected_pnl = (52000.0 - 50000.0) * 1.0
        assert abs(position.unrealized_pnl - expected_pnl) < 1e-6
        assert new_portfolio.equity > portfolio.equity


class TestEquityCalculation:
    def test_equity_recalculation_spot(self, portfolio_service, timestamp):
        portfolio = portfolio_service.initialize_portfolio(
            portfolio_id="spot_portfolio",
            initial_cash=10000.0,
            account_type=AccountType.SPOT,
            timestamp=timestamp
        )

        fill = FillEvent(
            symbol="BTC",
            position_type=PositionType.SPOT,
            quantity=0.1,
            execution_price=50000.0,
            fee_amount=5.0,
            timestamp=timestamp
        )

        portfolio, _ = portfolio_service.apply_fill(portfolio, fill)

        mark_prices = {"BTC": 50000.0}
        state = portfolio_service.calculate_portfolio_state(
            portfolio, mark_prices, timestamp
        )

        expected_equity = (10000.0 - 5000.0 - 5.0) + (0.1 * 50000.0)
        assert abs(state.equity_snapshot.total_equity - expected_equity) < 1e-6
        assert abs(state.equity_snapshot.ledger_cash - (10000.0 - 5000.0 - 5.0)) < 1e-6
        assert abs(state.equity_snapshot.holdings_value - 5000.0) < 1e-6
        assert state.equity_snapshot.unrealized_pnl == 0.0

    def test_equity_recalculation_futures(self, portfolio_service, timestamp):
        portfolio = portfolio_service.initialize_portfolio(
            portfolio_id="futures_portfolio",
            initial_cash=10000.0,
            account_type=AccountType.FUTURES,
            timestamp=timestamp
        )

        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0
        )

        fill = FillEvent(
            symbol="BTCUSDT",
            position_type=PositionType.FUTURES,
            quantity=1.0,
            execution_price=50000.0,
            fee_amount=5.0,
            timestamp=timestamp,
            margin_context=margin_context
        )

        portfolio, _ = portfolio_service.apply_fill(portfolio, fill)

        mark_prices = {"BTCUSDT": 51000.0}
        state = portfolio_service.calculate_portfolio_state(
            portfolio, mark_prices, timestamp
        )

        expected_unrealized_pnl = (51000.0 - 50000.0) * 1.0
        expected_equity = (10000.0 - 5.0) + expected_unrealized_pnl
        assert abs(state.equity_snapshot.total_equity - expected_equity) < 1e-6
        assert abs(state.equity_snapshot.unrealized_pnl - expected_unrealized_pnl) < 1e-6


class TestMarginEvaluation:
    def test_margin_evaluation(self, portfolio_service, timestamp):
        portfolio = portfolio_service.initialize_portfolio(
            portfolio_id="futures_portfolio",
            initial_cash=1000.0,
            account_type=AccountType.FUTURES,
            timestamp=timestamp
        )

        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0
        )

        fill = FillEvent(
            symbol="BTCUSDT",
            position_type=PositionType.FUTURES,
            quantity=1.0,
            execution_price=10000.0,
            fee_amount=1.0,
            timestamp=timestamp,
            margin_context=margin_context
        )

        portfolio, _ = portfolio_service.apply_fill(portfolio, fill)

        mark_prices = {"BTCUSDT": 10000.0}
        new_portfolio, events = portfolio_service.update_market_prices(
            portfolio, mark_prices, timestamp
        )

        expected_mm = 10000.0 * 1.0 * 0.05
        assert abs(new_portfolio.margin_ledger.maintenance_margin - expected_mm) < 1e-6
        assert new_portfolio.margin_ledger.margin_ratio > 0


class TestLiquidationDetection:
    def test_liquidation_detection_long(self, portfolio_service, timestamp):
        portfolio = portfolio_service.initialize_portfolio(
            portfolio_id="futures_portfolio",
            initial_cash=1000.0,
            account_type=AccountType.FUTURES,
            timestamp=timestamp
        )

        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0
        )

        fill = FillEvent(
            symbol="BTCUSDT",
            position_type=PositionType.FUTURES,
            quantity=1.0,
            execution_price=10000.0,
            fee_amount=1.0,
            timestamp=timestamp,
            margin_context=margin_context
        )

        portfolio, _ = portfolio_service.apply_fill(portfolio, fill)

        liquidation_price = 10000.0 * (1.0 - 0.1) / (1.0 - 0.05)
        mark_prices = {"BTCUSDT": liquidation_price}
        new_portfolio, events = portfolio_service.update_market_prices(
            portfolio, mark_prices, timestamp
        )

        liquidation_events = [e for e in events if isinstance(e, LiquidationDetected)]
        assert len(liquidation_events) > 0
        assert new_portfolio.lifecycle == PortfolioLifecycle.LIQUIDATED

    def test_liquidation_detection_short(self, portfolio_service, timestamp):
        portfolio = portfolio_service.initialize_portfolio(
            portfolio_id="futures_portfolio",
            initial_cash=1000.0,
            account_type=AccountType.FUTURES,
            timestamp=timestamp
        )

        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0
        )

        fill = FillEvent(
            symbol="BTCUSDT",
            position_type=PositionType.FUTURES,
            quantity=-1.0,
            execution_price=10000.0,
            fee_amount=1.0,
            timestamp=timestamp,
            margin_context=margin_context
        )

        portfolio, _ = portfolio_service.apply_fill(portfolio, fill)

        liquidation_price = 10000.0 * (1.0 + 0.1) / (1.0 + 0.05)
        mark_prices = {"BTCUSDT": liquidation_price}
        new_portfolio, events = portfolio_service.update_market_prices(
            portfolio, mark_prices, timestamp
        )

        liquidation_events = [e for e in events if isinstance(e, LiquidationDetected)]
        assert len(liquidation_events) > 0


class TestPositionCloseLifecycle:
    def test_close_position(self, portfolio_service, timestamp):
        portfolio = portfolio_service.initialize_portfolio(
            portfolio_id="futures_portfolio",
            initial_cash=10000.0,
            account_type=AccountType.FUTURES,
            timestamp=timestamp
        )

        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0
        )

        fill = FillEvent(
            symbol="BTCUSDT",
            position_type=PositionType.FUTURES,
            quantity=1.0,
            execution_price=50000.0,
            fee_amount=5.0,
            timestamp=timestamp,
            margin_context=margin_context
        )

        portfolio, _ = portfolio_service.apply_fill(portfolio, fill)

        new_portfolio, events = portfolio_service.close_position(
            portfolio, "BTCUSDT", 52000.0, timestamp
        )

        assert "BTCUSDT" not in new_portfolio.positions
        expected_pnl = (52000.0 - 50000.0) * 1.0
        assert abs(new_portfolio.cash_ledger.ledger_cash_balance - (10000.0 - 5.0 + expected_pnl)) < 1e-6


class TestMultiplePositions:
    def test_multiple_positions_portfolio(self, portfolio_service, timestamp):
        portfolio = portfolio_service.initialize_portfolio(
            portfolio_id="multi_portfolio",
            initial_cash=20000.0,
            account_type=AccountType.FUTURES,
            timestamp=timestamp
        )

        margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.1,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0
        )

        fills = [
            FillEvent("BTCUSDT", PositionType.FUTURES, 1.0, 50000.0, 5.0, timestamp, margin_context),
            FillEvent("ETHUSDT", PositionType.FUTURES, 10.0, 3000.0, 3.0, timestamp, margin_context),
            FillEvent("SOLUSDT", PositionType.FUTURES, -100.0, 100.0, 1.0, timestamp, margin_context),
        ]

        for fill in fills:
            portfolio, _ = portfolio_service.apply_fill(portfolio, fill)

        assert len(portfolio.positions) == 3
        assert "BTCUSDT" in portfolio.positions
        assert "ETHUSDT" in portfolio.positions
        assert "SOLUSDT" in portfolio.positions

        mark_prices = {
            "BTCUSDT": 51000.0,
            "ETHUSDT": 3100.0,
            "SOLUSDT": 95.0
        }
        new_portfolio, events = portfolio_service.update_market_prices(
            portfolio, mark_prices, timestamp
        )

        btc_pnl = (51000.0 - 50000.0) * 1.0
        eth_pnl = (3100.0 - 3000.0) * 10.0
        sol_pnl = (100.0 - 95.0) * 100.0

        total_unrealized_pnl = btc_pnl + eth_pnl + sol_pnl
        expected_equity = (20000.0 - 5.0 - 3.0 - 1.0) + total_unrealized_pnl
        assert abs(new_portfolio.equity - expected_equity) < 1e-6


class TestImmutability:
    def test_immutability(self, portfolio_service, timestamp):
        portfolio = portfolio_service.initialize_portfolio(
            portfolio_id="immutable_test",
            initial_cash=10000.0,
            timestamp=timestamp
        )

        original_cash = portfolio.cash_ledger.ledger_cash_balance
        original_equity = portfolio.equity

        fill = FillEvent(
            symbol="BTC",
            position_type=PositionType.SPOT,
            quantity=0.1,
            execution_price=50000.0,
            fee_amount=5.0,
            timestamp=timestamp
        )

        new_portfolio, _ = portfolio_service.apply_fill(portfolio, fill)

        assert portfolio.cash_ledger.ledger_cash_balance == original_cash
        assert portfolio.equity == original_equity
        assert len(portfolio.holdings) == 0
        assert len(new_portfolio.holdings) == 1


class TestDeterministicReplay:
    def test_deterministic_replay(self, portfolio_service, timestamp):
        fills = [
            FillEvent("BTC", PositionType.SPOT, 0.1, 50000.0, 5.0, timestamp),
            FillEvent("BTC", PositionType.SPOT, 0.05, 51000.0, 2.55, timestamp),
            FillEvent("BTC", PositionType.SPOT, -0.03, 52000.0, 1.56, timestamp),
        ]

        portfolio1 = portfolio_service.initialize_portfolio(
            "replay1", 10000.0, timestamp=timestamp
        )
        for fill in fills:
            portfolio1, _ = portfolio_service.apply_fill(portfolio1, fill)

        portfolio2 = portfolio_service.initialize_portfolio(
            "replay2", 10000.0, timestamp=timestamp
        )
        for fill in fills:
            portfolio2, _ = portfolio_service.apply_fill(portfolio2, fill)

        assert portfolio1.cash_ledger.ledger_cash_balance == portfolio2.cash_ledger.ledger_cash_balance
        assert portfolio1.holdings["BTC"].quantity == portfolio2.holdings["BTC"].quantity
        assert len(portfolio1.ledger) == len(portfolio2.ledger)
