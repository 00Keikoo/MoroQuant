"""
Tests for Equity Engine - Deterministic Portfolio Valuation

Validates the Universal Equity Formula:
    Equity = Ledger Cash Balance + Σ Asset Holdings Market Value + Σ Position Unrealized PnL

Financial invariants tested:
1. Ledger cash already includes realized PnL, fees, and funding
2. Asset holdings valued at mark price
3. Position unrealized PnL calculated correctly for long/short
4. No double-counting of fees or funding
"""

import pytest
from datetime import datetime
from decimal import Decimal

from ml_service.portfolio.equity import EquityService, EquityUpdated
from ml_service.portfolio.models import (
    AccountType,
    AssetHolding,
    CashAccount,
    EquitySnapshot,
    MarginAccount,
    MarginMode,
    Portfolio,
    PortfolioLifecycle,
    Position,
    PositionLifecycle,
    PositionMarginContext,
    PositionType,
    RiskMode,
)


class TestEquityCalculation:
    """Test equity calculation across different portfolio configurations."""

    def test_empty_portfolio_equity(self):
        """Test equity calculation for empty portfolio with only cash."""
        cash_account = CashAccount(
            ledger_cash_balance=10000.0,
            available_cash=10000.0,
            reserved_cash=0.0,
            locked_cash=0.0
        )

        equity = EquityService.calculate_equity(
            cash_account=cash_account,
            asset_holdings={},
            positions={},
            mark_prices={}
        )

        assert equity == 10000.0

    def test_spot_btc_valuation(self):
        """
        Test spot BTC holding valuation.

        Scenario from design doc Example 1:
        - Initial: 10,000 USDT cash
        - Buy 0.1 BTC at 50,000 USDT
        - Fee: 5 USDT
        - Expected: 4,995 cash + 5,000 holdings = 9,995 equity
        """
        cash_account = CashAccount(
            ledger_cash_balance=4995.0,  # 10,000 - 5,000 - 5
            available_cash=4995.0,
            reserved_cash=0.0,
            locked_cash=0.0
        )

        btc_holding = AssetHolding(
            symbol="BTC",
            quantity=0.1,
            mark_price=50000.0,
            market_value=5000.0
        )

        holdings = {"BTC": btc_holding}
        mark_prices = {"BTC": 50000.0}

        equity = EquityService.calculate_equity(
            cash_account=cash_account,
            asset_holdings=holdings,
            positions={},
            mark_prices=mark_prices
        )

        assert abs(equity - 9995.0) < 1e-8
        assert abs(equity - (4995.0 + 5000.0)) < 1e-8

    def test_futures_long_unrealized_profit(self):
        """
        Test long futures position with unrealized profit.

        Scenario:
        - Long 1 BTC at 10,000 USDT
        - Mark price: 11,000 USDT
        - Expected unrealized PnL: (11,000 - 10,000) × 1 = +1,000 USDT
        """
        cash_account = CashAccount(
            ledger_cash_balance=1000.0,
            available_cash=0.0,
            reserved_cash=0.0,
            locked_cash=1000.0
        )

        position = Position(
            symbol="BTCUSDT",
            position_type=PositionType.FUTURES,
            status=PositionLifecycle.OPEN,
            quantity=1.0,  # Long
            average_entry_price=10000.0,
            average_exit_price=0.0,
            unrealized_pnl=1000.0,
            realized_pnl=0.0,
            margin_required=1000.0,
            margin_context=PositionMarginContext(
                leverage=10.0,
                initial_margin_ratio=0.1,
                maintenance_margin_ratio=0.05,
                allocated_margin=1000.0
            ),
            opened_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1)
        )

        positions = {"BTCUSDT": position}
        mark_prices = {"BTCUSDT": 11000.0}

        unrealized_pnl = EquityService.calculate_unrealized_pnl(
            positions=positions,
            mark_prices=mark_prices
        )

        assert abs(unrealized_pnl - 1000.0) < 1e-8

        equity = EquityService.calculate_equity(
            cash_account=cash_account,
            asset_holdings={},
            positions=positions,
            mark_prices=mark_prices
        )

        assert abs(equity - 2000.0) < 1e-8  # 1,000 cash + 1,000 unrealized

    def test_futures_long_unrealized_loss(self):
        """
        Test long futures position with unrealized loss.

        Scenario:
        - Long 1 BTC at 10,000 USDT
        - Mark price: 9,000 USDT
        - Expected unrealized PnL: (9,000 - 10,000) × 1 = -1,000 USDT
        """
        cash_account = CashAccount(
            ledger_cash_balance=1000.0,
            available_cash=0.0,
            reserved_cash=0.0,
            locked_cash=1000.0
        )

        position = Position(
            symbol="BTCUSDT",
            position_type=PositionType.FUTURES,
            status=PositionLifecycle.OPEN,
            quantity=1.0,  # Long
            average_entry_price=10000.0,
            average_exit_price=0.0,
            unrealized_pnl=-1000.0,
            realized_pnl=0.0,
            margin_required=1000.0,
            margin_context=PositionMarginContext(
                leverage=10.0,
                initial_margin_ratio=0.1,
                maintenance_margin_ratio=0.05,
                allocated_margin=1000.0
            ),
            opened_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1)
        )

        positions = {"BTCUSDT": position}
        mark_prices = {"BTCUSDT": 9000.0}

        unrealized_pnl = EquityService.calculate_unrealized_pnl(
            positions=positions,
            mark_prices=mark_prices
        )

        assert abs(unrealized_pnl - (-1000.0)) < 1e-8

        equity = EquityService.calculate_equity(
            cash_account=cash_account,
            asset_holdings={},
            positions=positions,
            mark_prices=mark_prices
        )

        assert abs(equity - 0.0) < 1e-8  # 1,000 cash - 1,000 unrealized loss

    def test_futures_short_profit(self):
        """
        Test short futures position with unrealized profit.

        Scenario:
        - Short 1 BTC at 10,000 USDT (quantity = -1.0)
        - Mark price: 9,000 USDT
        - Expected unrealized PnL: (10,000 - 9,000) × 1 = +1,000 USDT
        """
        cash_account = CashAccount(
            ledger_cash_balance=1000.0,
            available_cash=0.0,
            reserved_cash=0.0,
            locked_cash=1000.0
        )

        position = Position(
            symbol="BTCUSDT",
            position_type=PositionType.FUTURES,
            status=PositionLifecycle.OPEN,
            quantity=-1.0,  # Short
            average_entry_price=10000.0,
            average_exit_price=0.0,
            unrealized_pnl=1000.0,
            realized_pnl=0.0,
            margin_required=1000.0,
            margin_context=PositionMarginContext(
                leverage=10.0,
                initial_margin_ratio=0.1,
                maintenance_margin_ratio=0.05,
                allocated_margin=1000.0
            ),
            opened_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1)
        )

        positions = {"BTCUSDT": position}
        mark_prices = {"BTCUSDT": 9000.0}

        unrealized_pnl = EquityService.calculate_unrealized_pnl(
            positions=positions,
            mark_prices=mark_prices
        )

        assert abs(unrealized_pnl - 1000.0) < 1e-8

        equity = EquityService.calculate_equity(
            cash_account=cash_account,
            asset_holdings={},
            positions=positions,
            mark_prices=mark_prices
        )

        assert abs(equity - 2000.0) < 1e-8  # 1,000 cash + 1,000 unrealized

    def test_futures_short_loss(self):
        """
        Test short futures position with unrealized loss.

        Scenario:
        - Short 1 BTC at 10,000 USDT (quantity = -1.0)
        - Mark price: 11,000 USDT
        - Expected unrealized PnL: (10,000 - 11,000) × 1 = -1,000 USDT
        """
        cash_account = CashAccount(
            ledger_cash_balance=1000.0,
            available_cash=0.0,
            reserved_cash=0.0,
            locked_cash=1000.0
        )

        position = Position(
            symbol="BTCUSDT",
            position_type=PositionType.FUTURES,
            status=PositionLifecycle.OPEN,
            quantity=-1.0,  # Short
            average_entry_price=10000.0,
            average_exit_price=0.0,
            unrealized_pnl=-1000.0,
            realized_pnl=0.0,
            margin_required=1000.0,
            margin_context=PositionMarginContext(
                leverage=10.0,
                initial_margin_ratio=0.1,
                maintenance_margin_ratio=0.05,
                allocated_margin=1000.0
            ),
            opened_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1)
        )

        positions = {"BTCUSDT": position}
        mark_prices = {"BTCUSDT": 11000.0}

        unrealized_pnl = EquityService.calculate_unrealized_pnl(
            positions=positions,
            mark_prices=mark_prices
        )

        assert abs(unrealized_pnl - (-1000.0)) < 1e-8

        equity = EquityService.calculate_equity(
            cash_account=cash_account,
            asset_holdings={},
            positions=positions,
            mark_prices=mark_prices
        )

        assert abs(equity - 0.0) < 1e-8  # 1,000 cash - 1,000 unrealized loss

    def test_mixed_spot_and_futures_portfolio(self):
        """
        Test portfolio with both spot holdings and futures positions.

        Scenario:
        - Cash: 5,000 USDT
        - Spot: 0.1 BTC at 50,000 = 5,000 USDT
        - Long futures: 0.5 BTC at 48,000, mark 50,000 = +1,000 unrealized
        - Expected equity: 5,000 + 5,000 + 1,000 = 11,000 USDT
        """
        cash_account = CashAccount(
            ledger_cash_balance=5000.0,
            available_cash=2500.0,
            reserved_cash=0.0,
            locked_cash=2500.0
        )

        btc_holding = AssetHolding(
            symbol="BTC",
            quantity=0.1,
            mark_price=50000.0,
            market_value=5000.0
        )

        position = Position(
            symbol="BTCUSDT",
            position_type=PositionType.FUTURES,
            status=PositionLifecycle.OPEN,
            quantity=0.5,  # Long
            average_entry_price=48000.0,
            average_exit_price=0.0,
            unrealized_pnl=1000.0,
            realized_pnl=0.0,
            margin_required=2500.0,
            margin_context=PositionMarginContext(
                leverage=10.0,
                initial_margin_ratio=0.1,
                maintenance_margin_ratio=0.05,
                allocated_margin=2500.0
            ),
            opened_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1)
        )

        holdings = {"BTC": btc_holding}
        positions = {"BTCUSDT": position}
        mark_prices = {"BTC": 50000.0, "BTCUSDT": 50000.0}

        equity = EquityService.calculate_equity(
            cash_account=cash_account,
            asset_holdings=holdings,
            positions=positions,
            mark_prices=mark_prices
        )

        assert abs(equity - 11000.0) < 1e-8
        assert abs(equity - (5000.0 + 5000.0 + 1000.0)) < 1e-8

    def test_fee_already_in_ledger_not_double_counted(self):
        """
        Test that fees are NOT double-counted.

        Financial Invariant: Ledger cash already includes fee charges.
        DO NOT subtract fees again from equity calculation.

        Scenario:
        - Initial cash: 10,000 USDT
        - Trade cost: 5,000 USDT
        - Fee: 5 USDT
        - Ledger cash: 10,000 - 5,000 - 5 = 4,995 USDT
        - Holdings: 5,000 USDT
        - Equity: 4,995 + 5,000 = 9,995 USDT (fee already deducted)
        """
        cash_account = CashAccount(
            ledger_cash_balance=4995.0,  # Fee already deducted
            available_cash=4995.0,
            reserved_cash=0.0,
            locked_cash=0.0
        )

        btc_holding = AssetHolding(
            symbol="BTC",
            quantity=0.1,
            mark_price=50000.0,
            market_value=5000.0
        )

        holdings = {"BTC": btc_holding}
        mark_prices = {"BTC": 50000.0}

        equity = EquityService.calculate_equity(
            cash_account=cash_account,
            asset_holdings=holdings,
            positions={},
            mark_prices=mark_prices
        )

        # Equity should be 9,995, NOT 9,990
        # Fee is already in ledger_cash_balance, don't subtract again
        assert abs(equity - 9995.0) < 1e-8

    def test_funding_already_in_ledger_not_double_counted(self):
        """
        Test that funding payments are NOT double-counted.

        Financial Invariant: Ledger cash already includes funding adjustments.
        DO NOT add/subtract funding again from equity calculation.

        Scenario:
        - Initial cash: 1,000 USDT
        - Funding payment: -1 USDT
        - Ledger cash: 1,000 - 1 = 999 USDT
        - Position: Long 1 BTC at 10,000, mark 10,000, unrealized = 0
        - Equity: 999 + 0 = 999 USDT (funding already deducted)
        """
        cash_account = CashAccount(
            ledger_cash_balance=999.0,  # Funding already deducted
            available_cash=0.0,
            reserved_cash=0.0,
            locked_cash=999.0
        )

        position = Position(
            symbol="BTCUSDT",
            position_type=PositionType.FUTURES,
            status=PositionLifecycle.OPEN,
            quantity=1.0,
            average_entry_price=10000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=999.0,
            margin_context=PositionMarginContext(
                leverage=10.0,
                initial_margin_ratio=0.1,
                maintenance_margin_ratio=0.05,
                allocated_margin=999.0
            ),
            opened_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1)
        )

        positions = {"BTCUSDT": position}
        mark_prices = {"BTCUSDT": 10000.0}

        equity = EquityService.calculate_equity(
            cash_account=cash_account,
            asset_holdings={},
            positions=positions,
            mark_prices=mark_prices
        )

        # Equity should be 999, NOT 1000
        # Funding is already in ledger_cash_balance
        assert abs(equity - 999.0) < 1e-8


class TestEquitySnapshot:
    """Test equity snapshot creation."""

    def test_equity_snapshot_creation(self):
        """Test creating an immutable equity snapshot."""
        cash_account = CashAccount(
            ledger_cash_balance=5000.0,
            available_cash=2500.0,
            reserved_cash=0.0,
            locked_cash=2500.0
        )

        btc_holding = AssetHolding(
            symbol="BTC",
            quantity=0.1,
            mark_price=50000.0,
            market_value=5000.0
        )

        position = Position(
            symbol="ETHUSDT",
            position_type=PositionType.MARGIN,
            status=PositionLifecycle.OPEN,
            quantity=10.0,
            average_entry_price=2000.0,
            average_exit_price=0.0,
            unrealized_pnl=1000.0,
            realized_pnl=0.0,
            margin_required=2000.0,
            margin_context=PositionMarginContext(
                leverage=10.0,
                initial_margin_ratio=0.1,
                maintenance_margin_ratio=0.05,
                allocated_margin=2000.0
            ),
            opened_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1)
        )

        margin_account = MarginAccount(
            risk_mode=RiskMode.LIQUIDATION_ENABLED,
            margin_mode=MarginMode.CROSS,
            initial_margin=2000.0,
            maintenance_margin=1000.0,
            margin_ratio=0.05,
            liquidation_buffer=1000.0,
            liquidation_price={}
        )

        portfolio = Portfolio(
            portfolio_id="test-portfolio",
            account_type=AccountType.MARGIN,
            lifecycle=PortfolioLifecycle.ACTIVE,
            ledger=[],
            cash_ledger=cash_account,
            margin_ledger=margin_account,
            positions={"ETHUSDT": position},
            holdings={"BTC": btc_holding},
            equity=11000.0,
            last_updated=datetime(2024, 1, 1)
        )

        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        mark_prices = {"BTC": 50000.0, "ETHUSDT": 2100.0}

        snapshot = EquityService.create_equity_snapshot(
            portfolio=portfolio,
            timestamp=timestamp,
            mark_prices=mark_prices
        )

        assert isinstance(snapshot, EquitySnapshot)
        assert snapshot.timestamp == timestamp
        assert snapshot.ledger_cash == 5000.0
        assert snapshot.holdings_value == 5000.0
        assert snapshot.unrealized_pnl == 1000.0
        assert snapshot.total_equity == 11000.0

    def test_equity_snapshot_immutability(self):
        """Test that EquitySnapshot is immutable."""
        snapshot = EquitySnapshot(
            timestamp=datetime(2024, 1, 1),
            ledger_cash=1000.0,
            holdings_value=500.0,
            unrealized_pnl=100.0,
            total_equity=1600.0
        )

        with pytest.raises(Exception):
            snapshot.total_equity = 2000.0


class TestEquityValidation:
    """Test validation and error handling."""

    def test_missing_mark_price_for_holding(self):
        """Test that missing mark price for holding raises error."""
        cash_account = CashAccount(
            ledger_cash_balance=1000.0,
            available_cash=1000.0,
            reserved_cash=0.0,
            locked_cash=0.0
        )

        btc_holding = AssetHolding(
            symbol="BTC",
            quantity=0.1,
            mark_price=50000.0,
            market_value=5000.0
        )

        holdings = {"BTC": btc_holding}
        mark_prices = {}  # Missing BTC price

        with pytest.raises(ValueError, match="Missing mark price for asset holding: BTC"):
            EquityService.calculate_equity(
                cash_account=cash_account,
                asset_holdings=holdings,
                positions={},
                mark_prices=mark_prices
            )

    def test_missing_mark_price_for_position(self):
        """Test that missing mark price for position raises error."""
        cash_account = CashAccount(
            ledger_cash_balance=1000.0,
            available_cash=0.0,
            reserved_cash=0.0,
            locked_cash=1000.0
        )

        position = Position(
            symbol="BTCUSDT",
            position_type=PositionType.FUTURES,
            status=PositionLifecycle.OPEN,
            quantity=1.0,
            average_entry_price=10000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=1000.0,
            margin_context=PositionMarginContext(
                leverage=10.0,
                initial_margin_ratio=0.1,
                maintenance_margin_ratio=0.05,
                allocated_margin=1000.0
            ),
            opened_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1)
        )

        positions = {"BTCUSDT": position}
        mark_prices = {}  # Missing BTCUSDT price

        with pytest.raises(ValueError, match="Missing mark price for position: BTCUSDT"):
            EquityService.calculate_equity(
                cash_account=cash_account,
                asset_holdings={},
                positions=positions,
                mark_prices=mark_prices
            )

    def test_invalid_mark_price_negative(self):
        """Test that negative mark price raises error."""
        positions = {
            "BTCUSDT": Position(
                symbol="BTCUSDT",
                position_type=PositionType.FUTURES,
                status=PositionLifecycle.OPEN,
                quantity=1.0,
                average_entry_price=10000.0,
                average_exit_price=0.0,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                margin_required=1000.0,
                margin_context=PositionMarginContext(
                    leverage=10.0,
                    initial_margin_ratio=0.1,
                    maintenance_margin_ratio=0.05,
                    allocated_margin=1000.0
                ),
                opened_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1)
            )
        }

        mark_prices = {"BTCUSDT": -10000.0}  # Invalid negative price

        with pytest.raises(ValueError, match="Invalid mark price"):
            EquityService.calculate_unrealized_pnl(
                positions=positions,
                mark_prices=mark_prices
            )

    def test_zero_quantity_position_raises_error(self):
        """Test that position with zero quantity raises error during creation."""
        # Position model validates this at creation time
        with pytest.raises(ValueError, match="quantity cannot be zero"):
            Position(
                symbol="BTCUSDT",
                position_type=PositionType.FUTURES,
                status=PositionLifecycle.OPEN,
                quantity=0.0,  # Invalid
                average_entry_price=10000.0,
                average_exit_price=0.0,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                margin_required=1000.0,
                margin_context=PositionMarginContext(
                    leverage=10.0,
                    initial_margin_ratio=0.1,
                    maintenance_margin_ratio=0.05,
                    allocated_margin=1000.0
                ),
                opened_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1)
            )


class TestEquityEvents:
    """Test equity event creation."""

    def test_create_equity_updated_event(self):
        """Test creating EquityUpdated event."""
        event = EquityService.create_equity_updated_event(
            portfolio_id="test-portfolio",
            timestamp=datetime(2024, 1, 1),
            previous_equity=10000.0,
            current_equity=11000.0
        )

        assert isinstance(event, EquityUpdated)
        assert event.portfolio_id == "test-portfolio"
        assert event.previous_equity == 10000.0
        assert event.current_equity == 11000.0
        assert event.change == 1000.0

    def test_equity_event_immutability(self):
        """Test that EquityUpdated event is immutable."""
        event = EquityUpdated(
            portfolio_id="test-portfolio",
            timestamp=datetime(2024, 1, 1),
            previous_equity=10000.0,
            current_equity=11000.0,
            change=1000.0
        )

        with pytest.raises(Exception):
            event.change = 2000.0
