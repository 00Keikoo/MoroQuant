"""
Tests for Immutable Portfolio Domain Models

Validates:
- Immutability
- Equality
- Serialization
- Invalid states
- Spot portfolio scenarios
- Futures portfolio scenarios
- Isolated margin contexts
"""

import pytest
from datetime import datetime
from dataclasses import replace

from ml_service.portfolio.models import (
    AccountType, PositionType, RiskMode, MarginMode,
    PortfolioLifecycle, PositionLifecycle, TransactionType,
    LedgerEntry, CashAccount, PositionMarginContext, MarginAccount,
    AssetHolding, Position, EquitySnapshot, ExposureSnapshot, Portfolio
)


class TestEnums:
    def test_account_type_enum(self):
        assert AccountType.SPOT.value == "SPOT"
        assert AccountType.MARGIN.value == "MARGIN"
        assert AccountType.FUTURES.value == "FUTURES"

    def test_position_type_enum(self):
        assert PositionType.SPOT.value == "SPOT"
        assert PositionType.MARGIN.value == "MARGIN"
        assert PositionType.FUTURES.value == "FUTURES"

    def test_risk_mode_enum(self):
        assert RiskMode.NONE.value == "NONE"
        assert RiskMode.MARGIN.value == "MARGIN"
        assert RiskMode.LIQUIDATION_ENABLED.value == "LIQUIDATION_ENABLED"


class TestLedgerEntry:
    def test_valid_ledger_entry(self):
        entry = LedgerEntry(
            entry_id="entry_1",
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
            transaction_type=TransactionType.DEPOSIT,
            asset="USDT",
            amount=10000.0,
            description="Initial deposit"
        )
        assert entry.entry_id == "entry_1"
        assert entry.amount == 10000.0

    def test_immutability(self):
        entry = LedgerEntry(
            entry_id="entry_1",
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
            transaction_type=TransactionType.DEPOSIT,
            asset="USDT",
            amount=10000.0,
            description="Initial deposit"
        )
        with pytest.raises(AttributeError):
            entry.amount = 5000.0

    def test_invalid_transaction_type(self):
        with pytest.raises(ValueError, match="Invalid transaction_type"):
            LedgerEntry(
                entry_id="entry_1",
                timestamp=datetime(2026, 1, 1, 12, 0, 0),
                transaction_type="INVALID",
                asset="USDT",
                amount=10000.0,
                description="Test"
            )

    def test_empty_entry_id(self):
        with pytest.raises(ValueError, match="entry_id cannot be empty"):
            LedgerEntry(
                entry_id="",
                timestamp=datetime(2026, 1, 1, 12, 0, 0),
                transaction_type=TransactionType.DEPOSIT,
                asset="USDT",
                amount=10000.0,
                description="Test"
            )

    def test_empty_asset(self):
        with pytest.raises(ValueError, match="asset cannot be empty"):
            LedgerEntry(
                entry_id="entry_1",
                timestamp=datetime(2026, 1, 1, 12, 0, 0),
                transaction_type=TransactionType.DEPOSIT,
                asset="",
                amount=10000.0,
                description="Test"
            )


class TestCashAccount:
    def test_valid_cash_account(self):
        cash = CashAccount(
            ledger_cash_balance=10000.0,
            available_cash=8000.0,
            reserved_cash=1000.0,
            locked_cash=1000.0
        )
        assert cash.ledger_cash_balance == 10000.0
        assert cash.available_cash == 8000.0

    def test_negative_reserved_cash(self):
        with pytest.raises(ValueError, match="reserved_cash cannot be negative"):
            CashAccount(
                ledger_cash_balance=10000.0,
                available_cash=11000.0,
                reserved_cash=-1000.0,
                locked_cash=0.0
            )

    def test_negative_locked_cash(self):
        with pytest.raises(ValueError, match="locked_cash cannot be negative"):
            CashAccount(
                ledger_cash_balance=10000.0,
                available_cash=11000.0,
                reserved_cash=0.0,
                locked_cash=-1000.0
            )

    def test_negative_available_cash(self):
        with pytest.raises(ValueError, match="available_cash cannot be negative"):
            CashAccount(
                ledger_cash_balance=9000.0,
                available_cash=-1000.0,
                reserved_cash=5000.0,
                locked_cash=5000.0
            )

    def test_cash_invariant_violation(self):
        with pytest.raises(ValueError, match="Cash account invariant violated"):
            CashAccount(
                ledger_cash_balance=10000.0,
                available_cash=5000.0,
                reserved_cash=1000.0,
                locked_cash=1000.0
            )


class TestPositionMarginContext:
    def test_valid_margin_context(self):
        ctx = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.10,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0
        )
        assert ctx.leverage == 10.0
        assert ctx.initial_margin_ratio == 0.10

    def test_negative_leverage(self):
        with pytest.raises(ValueError, match="leverage must be positive"):
            PositionMarginContext(
                leverage=-10.0,
                initial_margin_ratio=0.10,
                maintenance_margin_ratio=0.05,
                allocated_margin=1000.0
            )

    def test_invalid_initial_margin_ratio(self):
        with pytest.raises(ValueError, match="initial_margin_ratio must be in"):
            PositionMarginContext(
                leverage=10.0,
                initial_margin_ratio=1.5,
                maintenance_margin_ratio=0.05,
                allocated_margin=1000.0
            )

    def test_mmr_greater_than_imr(self):
        with pytest.raises(ValueError, match="maintenance_margin_ratio.*must be less than"):
            PositionMarginContext(
                leverage=10.0,
                initial_margin_ratio=0.10,
                maintenance_margin_ratio=0.15,
                allocated_margin=1000.0
            )

    def test_negative_allocated_margin(self):
        with pytest.raises(ValueError, match="allocated_margin cannot be negative"):
            PositionMarginContext(
                leverage=10.0,
                initial_margin_ratio=0.10,
                maintenance_margin_ratio=0.05,
                allocated_margin=-100.0
            )

    def test_imr_leverage_mismatch(self):
        with pytest.raises(ValueError, match="initial_margin_ratio.*must equal 1/leverage"):
            PositionMarginContext(
                leverage=10.0,
                initial_margin_ratio=0.20,
                maintenance_margin_ratio=0.05,
                allocated_margin=1000.0
            )


class TestMarginAccount:
    def test_valid_margin_account(self):
        margin = MarginAccount(
            risk_mode=RiskMode.LIQUIDATION_ENABLED,
            margin_mode=MarginMode.CROSS,
            initial_margin=1000.0,
            maintenance_margin=500.0,
            margin_ratio=0.05,
            liquidation_buffer=9500.0,
            liquidation_price={"BTCUSDT": 9473.68}
        )
        assert margin.risk_mode == RiskMode.LIQUIDATION_ENABLED
        assert margin.margin_mode == MarginMode.CROSS

    def test_negative_initial_margin(self):
        with pytest.raises(ValueError, match="initial_margin cannot be negative"):
            MarginAccount(
                risk_mode=RiskMode.LIQUIDATION_ENABLED,
                margin_mode=MarginMode.CROSS,
                initial_margin=-1000.0,
                maintenance_margin=500.0,
                margin_ratio=0.05,
                liquidation_buffer=9500.0
            )


class TestAssetHolding:
    def test_valid_asset_holding(self):
        holding = AssetHolding(
            symbol="BTC",
            quantity=0.1,
            mark_price=50000.0,
            market_value=5000.0
        )
        assert holding.symbol == "BTC"
        assert holding.quantity == 0.1

    def test_negative_quantity(self):
        with pytest.raises(ValueError, match="quantity cannot be negative"):
            AssetHolding(
                symbol="BTC",
                quantity=-0.1,
                mark_price=50000.0,
                market_value=-5000.0
            )

    def test_negative_mark_price(self):
        with pytest.raises(ValueError, match="mark_price cannot be negative"):
            AssetHolding(
                symbol="BTC",
                quantity=0.1,
                mark_price=-50000.0,
                market_value=-5000.0
            )

    def test_market_value_mismatch(self):
        with pytest.raises(ValueError, match="market_value.*!=.*quantity.*mark_price"):
            AssetHolding(
                symbol="BTC",
                quantity=0.1,
                mark_price=50000.0,
                market_value=6000.0
            )

    def test_empty_symbol(self):
        with pytest.raises(ValueError, match="symbol cannot be empty"):
            AssetHolding(
                symbol="",
                quantity=0.1,
                mark_price=50000.0,
                market_value=5000.0
            )


class TestPosition:
    def test_valid_futures_position(self):
        margin_ctx = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.10,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0
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
            margin_context=margin_ctx,
            opened_at=datetime(2026, 1, 1, 12, 0, 0),
            updated_at=datetime(2026, 1, 1, 12, 0, 0)
        )
        assert position.symbol == "BTCUSDT"
        assert position.quantity == 1.0

    def test_valid_spot_position(self):
        position = Position(
            symbol="BTC",
            position_type=PositionType.SPOT,
            status=PositionLifecycle.OPEN,
            quantity=0.1,
            average_entry_price=50000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=0.0,
            margin_context=None,
            opened_at=datetime(2026, 1, 1, 12, 0, 0),
            updated_at=datetime(2026, 1, 1, 12, 0, 0)
        )
        assert position.position_type == PositionType.SPOT
        assert position.margin_context is None

    def test_zero_quantity_open_position(self):
        with pytest.raises(ValueError, match="quantity cannot be zero"):
            Position(
                symbol="BTCUSDT",
                position_type=PositionType.SPOT,
                status=PositionLifecycle.OPEN,
                quantity=0.0,
                average_entry_price=50000.0,
                average_exit_price=0.0,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                margin_required=0.0,
                margin_context=None,
                opened_at=datetime(2026, 1, 1, 12, 0, 0),
                updated_at=datetime(2026, 1, 1, 12, 0, 0)
            )

    def test_futures_position_without_margin_context(self):
        with pytest.raises(ValueError, match="margin_context required for"):
            Position(
                symbol="BTCUSDT",
                position_type=PositionType.FUTURES,
                status=PositionLifecycle.OPEN,
                quantity=1.0,
                average_entry_price=10000.0,
                average_exit_price=0.0,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                margin_required=1000.0,
                margin_context=None,
                opened_at=datetime(2026, 1, 1, 12, 0, 0),
                updated_at=datetime(2026, 1, 1, 12, 0, 0)
            )

    def test_spot_position_with_margin_context(self):
        margin_ctx = PositionMarginContext(
            leverage=1.0,
            initial_margin_ratio=1.0,
            maintenance_margin_ratio=0.5,
            allocated_margin=0.0
        )
        with pytest.raises(ValueError, match="margin_context must be None for SPOT"):
            Position(
                symbol="BTC",
                position_type=PositionType.SPOT,
                status=PositionLifecycle.OPEN,
                quantity=0.1,
                average_entry_price=50000.0,
                average_exit_price=0.0,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                margin_required=0.0,
                margin_context=margin_ctx,
                opened_at=datetime(2026, 1, 1, 12, 0, 0),
                updated_at=datetime(2026, 1, 1, 12, 0, 0)
            )


class TestEquitySnapshot:
    def test_valid_equity_snapshot(self):
        snapshot = EquitySnapshot(
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
            ledger_cash=10000.0,
            holdings_value=5000.0,
            unrealized_pnl=-500.0,
            total_equity=14500.0
        )
        assert snapshot.total_equity == 14500.0

    def test_equity_calculation_mismatch(self):
        with pytest.raises(ValueError, match="total_equity.*!="):
            EquitySnapshot(
                timestamp=datetime(2026, 1, 1, 12, 0, 0),
                ledger_cash=10000.0,
                holdings_value=5000.0,
                unrealized_pnl=-500.0,
                total_equity=20000.0
            )


class TestExposureSnapshot:
    def test_valid_exposure_snapshot(self):
        snapshot = ExposureSnapshot(
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
            asset_allocation={"BTC": 0.5, "ETH": 0.3, "USDT": 0.2},
            gross_exposure=15000.0,
            net_exposure=5000.0,
            leverage=1.5,
            buying_power=5000.0
        )
        assert snapshot.leverage == 1.5

    def test_negative_gross_exposure(self):
        with pytest.raises(ValueError, match="gross_exposure cannot be negative"):
            ExposureSnapshot(
                timestamp=datetime(2026, 1, 1, 12, 0, 0),
                asset_allocation={},
                gross_exposure=-15000.0,
                net_exposure=5000.0,
                leverage=1.5,
                buying_power=5000.0
            )

    def test_net_exposure_exceeds_gross(self):
        with pytest.raises(ValueError, match="abs.*net_exposure.*cannot exceed gross_exposure"):
            ExposureSnapshot(
                timestamp=datetime(2026, 1, 1, 12, 0, 0),
                asset_allocation={},
                gross_exposure=10000.0,
                net_exposure=15000.0,
                leverage=1.5,
                buying_power=5000.0
            )


class TestPortfolio:
    def test_valid_spot_portfolio(self):
        """Example 1: Spot BTC Purchase from design doc"""
        ledger = [
            LedgerEntry(
                entry_id="1",
                timestamp=datetime(2026, 1, 1, 12, 0, 0),
                transaction_type=TransactionType.DEPOSIT,
                asset="USDT",
                amount=10000.0,
                description="Initial deposit"
            ),
            LedgerEntry(
                entry_id="2",
                timestamp=datetime(2026, 1, 1, 13, 0, 0),
                transaction_type=TransactionType.TRADE_DEBIT,
                asset="USDT",
                amount=-5000.0,
                description="Buy 0.1 BTC"
            ),
            LedgerEntry(
                entry_id="3",
                timestamp=datetime(2026, 1, 1, 13, 0, 0),
                transaction_type=TransactionType.FEE_CHARGE,
                asset="USDT",
                amount=-5.0,
                description="Trading fee"
            )
        ]

        cash = CashAccount(
            ledger_cash_balance=4995.0,
            available_cash=4995.0,
            reserved_cash=0.0,
            locked_cash=0.0
        )

        holdings = {
            "BTC": AssetHolding(
                symbol="BTC",
                quantity=0.1,
                mark_price=50000.0,
                market_value=5000.0
            )
        }

        margin = MarginAccount(
            risk_mode=RiskMode.NONE,
            margin_mode=MarginMode.CROSS,
            initial_margin=0.0,
            maintenance_margin=0.0,
            margin_ratio=0.0,
            liquidation_buffer=0.0
        )

        portfolio = Portfolio(
            portfolio_id="port_1",
            account_type=AccountType.SPOT,
            lifecycle=PortfolioLifecycle.ACTIVE,
            ledger=ledger,
            cash_ledger=cash,
            margin_ledger=margin,
            positions={},
            holdings=holdings,
            equity=9995.0,
            last_updated=datetime(2026, 1, 1, 13, 0, 0)
        )

        assert portfolio.equity == 9995.0
        assert len(portfolio.holdings) == 1

    def test_valid_futures_portfolio(self):
        """Example 2: Long Futures Position from design doc"""
        margin_ctx = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.10,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0
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
            margin_context=margin_ctx,
            opened_at=datetime(2026, 1, 1, 12, 0, 0),
            updated_at=datetime(2026, 1, 1, 12, 0, 0)
        )

        cash = CashAccount(
            ledger_cash_balance=1000.0,
            available_cash=0.0,
            reserved_cash=0.0,
            locked_cash=1000.0
        )

        margin = MarginAccount(
            risk_mode=RiskMode.LIQUIDATION_ENABLED,
            margin_mode=MarginMode.CROSS,
            initial_margin=1000.0,
            maintenance_margin=500.0,
            margin_ratio=0.50,
            liquidation_buffer=500.0,
            liquidation_price={"BTCUSDT": 9473.68}
        )

        ledger = [
            LedgerEntry(
                entry_id="1",
                timestamp=datetime(2026, 1, 1, 12, 0, 0),
                transaction_type=TransactionType.DEPOSIT,
                asset="USDT",
                amount=1000.0,
                description="Initial deposit"
            )
        ]

        portfolio = Portfolio(
            portfolio_id="port_2",
            account_type=AccountType.FUTURES,
            lifecycle=PortfolioLifecycle.ACTIVE,
            ledger=ledger,
            cash_ledger=cash,
            margin_ledger=margin,
            positions={"BTCUSDT": position},
            holdings={},
            equity=1000.0,
            last_updated=datetime(2026, 1, 1, 12, 0, 0)
        )

        assert portfolio.equity == 1000.0
        assert len(portfolio.positions) == 1

    def test_equity_invariant_violation(self):
        cash = CashAccount(
            ledger_cash_balance=10000.0,
            available_cash=10000.0,
            reserved_cash=0.0,
            locked_cash=0.0
        )

        margin = MarginAccount(
            risk_mode=RiskMode.NONE,
            margin_mode=MarginMode.CROSS,
            initial_margin=0.0,
            maintenance_margin=0.0,
            margin_ratio=0.0,
            liquidation_buffer=0.0
        )

        with pytest.raises(ValueError, match="equity.*!="):
            Portfolio(
                portfolio_id="port_1",
                account_type=AccountType.SPOT,
                lifecycle=PortfolioLifecycle.ACTIVE,
                ledger=[],
                cash_ledger=cash,
                margin_ledger=margin,
                positions={},
                holdings={},
                equity=5000.0,
                last_updated=datetime(2026, 1, 1, 12, 0, 0)
            )

    def test_spot_account_with_futures_position(self):
        margin_ctx = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.10,
            maintenance_margin_ratio=0.05,
            allocated_margin=1000.0
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
            margin_context=margin_ctx,
            opened_at=datetime(2026, 1, 1, 12, 0, 0),
            updated_at=datetime(2026, 1, 1, 12, 0, 0)
        )

        cash = CashAccount(
            ledger_cash_balance=1000.0,
            available_cash=0.0,
            reserved_cash=0.0,
            locked_cash=1000.0
        )

        margin = MarginAccount(
            risk_mode=RiskMode.NONE,
            margin_mode=MarginMode.CROSS,
            initial_margin=0.0,
            maintenance_margin=0.0,
            margin_ratio=0.0,
            liquidation_buffer=0.0
        )

        with pytest.raises(ValueError, match="SPOT account cannot contain.*FUTURES position"):
            Portfolio(
                portfolio_id="port_1",
                account_type=AccountType.SPOT,
                lifecycle=PortfolioLifecycle.ACTIVE,
                ledger=[],
                cash_ledger=cash,
                margin_ledger=margin,
                positions={"BTCUSDT": position},
                holdings={},
                equity=1000.0,
                last_updated=datetime(2026, 1, 1, 12, 0, 0)
            )

    def test_futures_account_with_holdings(self):
        holding = AssetHolding(
            symbol="BTC",
            quantity=0.1,
            mark_price=50000.0,
            market_value=5000.0
        )

        cash = CashAccount(
            ledger_cash_balance=5000.0,
            available_cash=5000.0,
            reserved_cash=0.0,
            locked_cash=0.0
        )

        margin = MarginAccount(
            risk_mode=RiskMode.NONE,
            margin_mode=MarginMode.CROSS,
            initial_margin=0.0,
            maintenance_margin=0.0,
            margin_ratio=0.0,
            liquidation_buffer=0.0
        )

        with pytest.raises(ValueError, match="FUTURES account cannot contain asset holdings"):
            Portfolio(
                portfolio_id="port_1",
                account_type=AccountType.FUTURES,
                lifecycle=PortfolioLifecycle.ACTIVE,
                ledger=[],
                cash_ledger=cash,
                margin_ledger=margin,
                positions={},
                holdings={"BTC": holding},
                equity=10000.0,
                last_updated=datetime(2026, 1, 1, 12, 0, 0)
            )


class TestImmutability:
    def test_portfolio_immutability(self):
        cash = CashAccount(
            ledger_cash_balance=10000.0,
            available_cash=10000.0,
            reserved_cash=0.0,
            locked_cash=0.0
        )

        margin = MarginAccount(
            risk_mode=RiskMode.NONE,
            margin_mode=MarginMode.CROSS,
            initial_margin=0.0,
            maintenance_margin=0.0,
            margin_ratio=0.0,
            liquidation_buffer=0.0
        )

        portfolio = Portfolio(
            portfolio_id="port_1",
            account_type=AccountType.SPOT,
            lifecycle=PortfolioLifecycle.ACTIVE,
            ledger=[],
            cash_ledger=cash,
            margin_ledger=margin,
            positions={},
            holdings={},
            equity=10000.0,
            last_updated=datetime(2026, 1, 1, 12, 0, 0)
        )

        with pytest.raises(AttributeError):
            portfolio.equity = 5000.0

        with pytest.raises(AttributeError):
            portfolio.lifecycle = PortfolioLifecycle.CLOSED


class TestIsolatedMarginContext:
    def test_isolated_margin_increased_collateral(self):
        """Example 4: Isolated Margin Collateral Increase from design doc"""
        margin_ctx = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.10,
            maintenance_margin_ratio=0.05,
            allocated_margin=1500.0
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
            margin_required=1500.0,
            margin_context=margin_ctx,
            opened_at=datetime(2026, 1, 1, 12, 0, 0),
            updated_at=datetime(2026, 1, 1, 13, 0, 0)
        )

        assert position.margin_context.allocated_margin == 1500.0

        lp_isolated = (10000.0 - 1500.0) / (1 - 0.05)
        assert abs(lp_isolated - 8947.37) < 0.01
