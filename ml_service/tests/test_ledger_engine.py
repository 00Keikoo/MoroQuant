"""
Test Suite for Ledger Engine

Tests all LedgerService operations including:
- Deposits and withdrawals
- Cash reservations and releases
- Fee deductions
- Funding payments
- Realized PnL
- Immutability guarantees
- Financial invariants
"""

import pytest
from datetime import datetime
from ml_service.portfolio.models import CashAccount, TransactionType
from ml_service.portfolio.ledger import LedgerService


@pytest.fixture
def ledger_service():
    """Create a LedgerService instance."""
    return LedgerService()


@pytest.fixture
def empty_cash_account():
    """Create an empty cash account."""
    return CashAccount(
        ledger_cash_balance=0.0,
        available_cash=0.0,
        reserved_cash=0.0,
        locked_cash=0.0
    )


@pytest.fixture
def funded_cash_account():
    """Create a funded cash account with 10,000 USDT."""
    return CashAccount(
        ledger_cash_balance=10000.0,
        available_cash=10000.0,
        reserved_cash=0.0,
        locked_cash=0.0
    )


@pytest.fixture
def cash_account_with_reserved():
    """Create a cash account with reserved funds."""
    return CashAccount(
        ledger_cash_balance=10000.0,
        available_cash=7000.0,
        reserved_cash=3000.0,
        locked_cash=0.0
    )


class TestDeposit:
    """Test deposit operations."""

    def test_deposit_increases_available_cash(self, ledger_service, empty_cash_account):
        amount = 5000.0
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.deposit(
            empty_cash_account,
            amount,
            timestamp,
            "Initial deposit"
        )

        assert new_account.available_cash == 5000.0
        assert new_account.ledger_cash_balance == 5000.0
        assert new_account.reserved_cash == 0.0
        assert new_account.locked_cash == 0.0

    def test_deposit_creates_ledger_entry(self, ledger_service, empty_cash_account):
        amount = 5000.0
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.deposit(
            empty_cash_account,
            amount,
            timestamp,
            "Initial deposit"
        )

        assert entry.transaction_type == TransactionType.DEPOSIT
        assert entry.amount == 5000.0
        assert entry.asset == "USDT"
        assert entry.description == "Initial deposit"
        assert entry.timestamp == timestamp

    def test_deposit_maintains_invariant(self, ledger_service, funded_cash_account):
        amount = 3000.0
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.deposit(
            funded_cash_account,
            amount,
            timestamp,
            "Additional deposit"
        )

        assert new_account.ledger_cash_balance == (
            new_account.available_cash + new_account.reserved_cash + new_account.locked_cash
        )

    def test_deposit_rejects_negative_amount(self, ledger_service, empty_cash_account):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        with pytest.raises(ValueError, match="Deposit amount must be positive"):
            ledger_service.deposit(empty_cash_account, -1000.0, timestamp, "Invalid")

    def test_deposit_rejects_zero_amount(self, ledger_service, empty_cash_account):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        with pytest.raises(ValueError, match="Deposit amount must be positive"):
            ledger_service.deposit(empty_cash_account, 0.0, timestamp, "Invalid")

    def test_deposit_immutability(self, ledger_service, funded_cash_account):
        original_balance = funded_cash_account.ledger_cash_balance
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.deposit(
            funded_cash_account,
            1000.0,
            timestamp,
            "Test immutability"
        )

        assert funded_cash_account.ledger_cash_balance == original_balance
        assert new_account is not funded_cash_account


class TestWithdrawal:
    """Test withdrawal operations."""

    def test_withdrawal_decreases_available_cash(self, ledger_service, funded_cash_account):
        amount = 3000.0
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.withdraw(
            funded_cash_account,
            amount,
            timestamp,
            "Withdrawal"
        )

        assert new_account.available_cash == 7000.0
        assert new_account.ledger_cash_balance == 7000.0
        assert new_account.reserved_cash == 0.0
        assert new_account.locked_cash == 0.0

    def test_withdrawal_creates_ledger_entry(self, ledger_service, funded_cash_account):
        amount = 3000.0
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.withdraw(
            funded_cash_account,
            amount,
            timestamp,
            "Withdrawal"
        )

        assert entry.transaction_type == TransactionType.WITHDRAWAL
        assert entry.amount == -3000.0
        assert entry.asset == "USDT"
        assert entry.description == "Withdrawal"

    def test_withdrawal_rejects_insufficient_funds(self, ledger_service, funded_cash_account):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        with pytest.raises(ValueError, match="Insufficient available cash"):
            ledger_service.withdraw(funded_cash_account, 15000.0, timestamp, "Too much")

    def test_withdrawal_rejects_negative_amount(self, ledger_service, funded_cash_account):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        with pytest.raises(ValueError, match="Withdrawal amount must be positive"):
            ledger_service.withdraw(funded_cash_account, -1000.0, timestamp, "Invalid")


class TestReserveCash:
    """Test cash reservation operations."""

    def test_reserve_moves_cash_from_available_to_reserved(self, ledger_service, funded_cash_account):
        amount = 3000.0
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.reserve_cash(
            funded_cash_account,
            amount,
            timestamp,
            "Order margin reservation"
        )

        assert new_account.available_cash == 7000.0
        assert new_account.reserved_cash == 3000.0
        assert new_account.ledger_cash_balance == 10000.0
        assert new_account.locked_cash == 0.0

    def test_reserve_maintains_ledger_balance(self, ledger_service, funded_cash_account):
        amount = 3000.0
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.reserve_cash(
            funded_cash_account,
            amount,
            timestamp,
            "Order reservation"
        )

        assert new_account.ledger_cash_balance == funded_cash_account.ledger_cash_balance

    def test_reserve_creates_ledger_entry(self, ledger_service, funded_cash_account):
        amount = 3000.0
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.reserve_cash(
            funded_cash_account,
            amount,
            timestamp,
            "Order reservation"
        )

        assert entry.transaction_type == TransactionType.TRADE_DEBIT
        assert entry.amount == 0.0
        assert "RESERVE" in entry.description

    def test_reserve_rejects_insufficient_funds(self, ledger_service, funded_cash_account):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        with pytest.raises(ValueError, match="Insufficient available cash"):
            ledger_service.reserve_cash(funded_cash_account, 15000.0, timestamp, "Too much")

    def test_reserve_rejects_negative_amount(self, ledger_service, funded_cash_account):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        with pytest.raises(ValueError, match="Reservation amount must be positive"):
            ledger_service.reserve_cash(funded_cash_account, -1000.0, timestamp, "Invalid")


class TestReleaseReservedCash:
    """Test reserved cash release operations."""

    def test_release_moves_cash_from_reserved_to_available(self, ledger_service, cash_account_with_reserved):
        amount = 2000.0
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.release_reserved_cash(
            cash_account_with_reserved,
            amount,
            timestamp,
            "Order cancelled"
        )

        assert new_account.available_cash == 9000.0
        assert new_account.reserved_cash == 1000.0
        assert new_account.ledger_cash_balance == 10000.0
        assert new_account.locked_cash == 0.0

    def test_release_maintains_ledger_balance(self, ledger_service, cash_account_with_reserved):
        amount = 2000.0
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.release_reserved_cash(
            cash_account_with_reserved,
            amount,
            timestamp,
            "Order cancelled"
        )

        assert new_account.ledger_cash_balance == cash_account_with_reserved.ledger_cash_balance

    def test_release_creates_ledger_entry(self, ledger_service, cash_account_with_reserved):
        amount = 2000.0
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.release_reserved_cash(
            cash_account_with_reserved,
            amount,
            timestamp,
            "Order cancelled"
        )

        assert entry.transaction_type == TransactionType.TRADE_CREDIT
        assert entry.amount == 0.0
        assert "RELEASE" in entry.description

    def test_release_rejects_insufficient_reserved(self, ledger_service, cash_account_with_reserved):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        with pytest.raises(ValueError, match="Insufficient reserved cash"):
            ledger_service.release_reserved_cash(cash_account_with_reserved, 5000.0, timestamp, "Too much")

    def test_release_rejects_negative_amount(self, ledger_service, cash_account_with_reserved):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        with pytest.raises(ValueError, match="Release amount must be positive"):
            ledger_service.release_reserved_cash(cash_account_with_reserved, -1000.0, timestamp, "Invalid")


class TestApplyFee:
    """Test fee application operations."""

    def test_fee_decreases_cash(self, ledger_service, funded_cash_account):
        fee_amount = 50.0
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.apply_fee(
            funded_cash_account,
            fee_amount,
            timestamp,
            "Trading fee"
        )

        assert new_account.available_cash == 9950.0
        assert new_account.ledger_cash_balance == 9950.0

    def test_fee_creates_ledger_entry(self, ledger_service, funded_cash_account):
        fee_amount = 50.0
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.apply_fee(
            funded_cash_account,
            fee_amount,
            timestamp,
            "Trading fee"
        )

        assert entry.transaction_type == TransactionType.FEE_CHARGE
        assert entry.amount == -50.0
        assert entry.description == "Trading fee"

    def test_fee_rejects_insufficient_funds(self, ledger_service, funded_cash_account):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        with pytest.raises(ValueError, match="Insufficient available cash"):
            ledger_service.apply_fee(funded_cash_account, 15000.0, timestamp, "Too much")

    def test_fee_rejects_negative_amount(self, ledger_service, funded_cash_account):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        with pytest.raises(ValueError, match="Fee amount must be positive"):
            ledger_service.apply_fee(funded_cash_account, -50.0, timestamp, "Invalid")


class TestApplyFunding:
    """Test funding payment operations."""

    def test_positive_funding_increases_cash(self, ledger_service, funded_cash_account):
        funding_amount = 100.0
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.apply_funding(
            funded_cash_account,
            funding_amount,
            timestamp,
            "Funding received"
        )

        assert new_account.available_cash == 10100.0
        assert new_account.ledger_cash_balance == 10100.0

    def test_negative_funding_decreases_cash(self, ledger_service, funded_cash_account):
        funding_amount = -100.0
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.apply_funding(
            funded_cash_account,
            funding_amount,
            timestamp,
            "Funding payment"
        )

        assert new_account.available_cash == 9900.0
        assert new_account.ledger_cash_balance == 9900.0

    def test_funding_creates_ledger_entry(self, ledger_service, funded_cash_account):
        funding_amount = 100.0
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.apply_funding(
            funded_cash_account,
            funding_amount,
            timestamp,
            "Funding received"
        )

        assert entry.transaction_type == TransactionType.FUNDING_ADJUSTMENT
        assert entry.amount == 100.0
        assert entry.description == "Funding received"

    def test_negative_funding_rejects_insufficient_funds(self, ledger_service, funded_cash_account):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        with pytest.raises(ValueError, match="Insufficient available cash"):
            ledger_service.apply_funding(funded_cash_account, -15000.0, timestamp, "Too much")


class TestApplyRealizedPnL:
    """Test realized PnL operations."""

    def test_realized_profit_increases_cash(self, ledger_service, funded_cash_account):
        pnl_amount = 500.0
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.apply_realized_pnl(
            funded_cash_account,
            pnl_amount,
            timestamp,
            "Position closed with profit"
        )

        assert new_account.available_cash == 10500.0
        assert new_account.ledger_cash_balance == 10500.0

    def test_realized_loss_decreases_cash(self, ledger_service, funded_cash_account):
        pnl_amount = -500.0
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.apply_realized_pnl(
            funded_cash_account,
            pnl_amount,
            timestamp,
            "Position closed with loss"
        )

        assert new_account.available_cash == 9500.0
        assert new_account.ledger_cash_balance == 9500.0

    def test_profit_creates_trade_credit_entry(self, ledger_service, funded_cash_account):
        pnl_amount = 500.0
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.apply_realized_pnl(
            funded_cash_account,
            pnl_amount,
            timestamp,
            "Profit"
        )

        assert entry.transaction_type == TransactionType.TRADE_CREDIT
        assert entry.amount == 500.0

    def test_loss_creates_trade_debit_entry(self, ledger_service, funded_cash_account):
        pnl_amount = -500.0
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.apply_realized_pnl(
            funded_cash_account,
            pnl_amount,
            timestamp,
            "Loss"
        )

        assert entry.transaction_type == TransactionType.TRADE_DEBIT
        assert entry.amount == -500.0

    def test_loss_rejects_insufficient_funds(self, ledger_service, funded_cash_account):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        with pytest.raises(ValueError, match="Insufficient available cash"):
            ledger_service.apply_realized_pnl(funded_cash_account, -15000.0, timestamp, "Too much")


class TestImmutability:
    """Test immutability guarantees."""

    def test_operations_return_new_objects(self, ledger_service, funded_cash_account):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.deposit(
            funded_cash_account,
            1000.0,
            timestamp,
            "Test"
        )

        assert new_account is not funded_cash_account
        assert id(new_account) != id(funded_cash_account)

    def test_original_account_unchanged_after_deposit(self, ledger_service, funded_cash_account):
        original_balance = funded_cash_account.ledger_cash_balance
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        ledger_service.deposit(funded_cash_account, 1000.0, timestamp, "Test")

        assert funded_cash_account.ledger_cash_balance == original_balance

    def test_original_account_unchanged_after_withdrawal(self, ledger_service, funded_cash_account):
        original_balance = funded_cash_account.ledger_cash_balance
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        ledger_service.withdraw(funded_cash_account, 1000.0, timestamp, "Test")

        assert funded_cash_account.ledger_cash_balance == original_balance


class TestFinancialInvariants:
    """Test financial invariants are maintained."""

    def test_cash_invariant_after_deposit(self, ledger_service, funded_cash_account):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.deposit(
            funded_cash_account,
            3000.0,
            timestamp,
            "Test"
        )

        assert new_account.ledger_cash_balance == (
            new_account.available_cash + new_account.reserved_cash + new_account.locked_cash
        )

    def test_cash_invariant_after_withdrawal(self, ledger_service, funded_cash_account):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.withdraw(
            funded_cash_account,
            3000.0,
            timestamp,
            "Test"
        )

        assert new_account.ledger_cash_balance == (
            new_account.available_cash + new_account.reserved_cash + new_account.locked_cash
        )

    def test_cash_invariant_after_reserve(self, ledger_service, funded_cash_account):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.reserve_cash(
            funded_cash_account,
            3000.0,
            timestamp,
            "Test"
        )

        assert new_account.ledger_cash_balance == (
            new_account.available_cash + new_account.reserved_cash + new_account.locked_cash
        )

    def test_cash_invariant_after_release(self, ledger_service, cash_account_with_reserved):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.release_reserved_cash(
            cash_account_with_reserved,
            2000.0,
            timestamp,
            "Test"
        )

        assert new_account.ledger_cash_balance == (
            new_account.available_cash + new_account.reserved_cash + new_account.locked_cash
        )

    def test_cash_invariant_after_fee(self, ledger_service, funded_cash_account):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.apply_fee(
            funded_cash_account,
            50.0,
            timestamp,
            "Test"
        )

        assert new_account.ledger_cash_balance == (
            new_account.available_cash + new_account.reserved_cash + new_account.locked_cash
        )

    def test_cash_invariant_after_funding(self, ledger_service, funded_cash_account):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.apply_funding(
            funded_cash_account,
            100.0,
            timestamp,
            "Test"
        )

        assert new_account.ledger_cash_balance == (
            new_account.available_cash + new_account.reserved_cash + new_account.locked_cash
        )

    def test_cash_invariant_after_pnl(self, ledger_service, funded_cash_account):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        new_account, entry = ledger_service.apply_realized_pnl(
            funded_cash_account,
            500.0,
            timestamp,
            "Test"
        )

        assert new_account.ledger_cash_balance == (
            new_account.available_cash + new_account.reserved_cash + new_account.locked_cash
        )


class TestComplexScenarios:
    """Test complex multi-operation scenarios."""

    def test_full_deposit_withdrawal_lifecycle(self, ledger_service, empty_cash_account):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        account1, _ = ledger_service.deposit(empty_cash_account, 10000.0, timestamp, "Initial")
        account2, _ = ledger_service.withdraw(account1, 3000.0, timestamp, "Withdrawal")
        account3, _ = ledger_service.deposit(account2, 5000.0, timestamp, "Add more")

        assert account3.ledger_cash_balance == 12000.0
        assert account3.available_cash == 12000.0

    def test_reserve_and_release_lifecycle(self, ledger_service, funded_cash_account):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        account1, _ = ledger_service.reserve_cash(funded_cash_account, 3000.0, timestamp, "Reserve")
        assert account1.available_cash == 7000.0
        assert account1.reserved_cash == 3000.0

        account2, _ = ledger_service.release_reserved_cash(account1, 3000.0, timestamp, "Release")
        assert account2.available_cash == 10000.0
        assert account2.reserved_cash == 0.0
        assert account2.ledger_cash_balance == 10000.0

    def test_trading_lifecycle_with_fees_and_pnl(self, ledger_service, funded_cash_account):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        account1, _ = ledger_service.reserve_cash(funded_cash_account, 5000.0, timestamp, "Order")
        account2, _ = ledger_service.apply_fee(account1, 50.0, timestamp, "Trading fee")
        account3, _ = ledger_service.apply_realized_pnl(account2, 1000.0, timestamp, "Profit")

        assert account3.ledger_cash_balance == 10950.0
        assert account3.available_cash == 5950.0
        assert account3.reserved_cash == 5000.0
