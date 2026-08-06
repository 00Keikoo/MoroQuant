"""
Ledger Engine - Single Source of Truth for Cash Mutations

The Ledger Engine is the ONLY component allowed to create cash state transitions.
All operations create immutable LedgerEntry records and return new immutable CashAccount states.
"""

from datetime import datetime
from typing import List
import uuid

from ml_service.portfolio.models import (
    CashAccount,
    LedgerEntry,
    TransactionType,
)


class LedgerService:
    """
    Ledger Service responsible for all portfolio cash mutations.

    Financial Rules:
    - Ledger is the single source of truth
    - All operations create immutable LedgerEntry
    - All operations return new immutable CashAccount
    - Never mutate existing objects

    Cash Account Invariant:
    ledger_cash_balance = available_cash + reserved_cash + locked_cash
    """

    def deposit(
        self,
        cash_account: CashAccount,
        amount: float,
        timestamp: datetime,
        description: str,
        asset: str = "USDT"
    ) -> tuple[CashAccount, LedgerEntry]:
        """
        Deposit cash into the account.

        State Transition:
        - available_cash += amount
        - ledger_cash_balance += amount

        Args:
            cash_account: Current cash account state
            amount: Amount to deposit (must be positive)
            timestamp: Transaction timestamp
            description: Description of the deposit
            asset: Asset symbol (default: USDT)

        Returns:
            Tuple of (new_cash_account, ledger_entry)

        Raises:
            ValueError: If amount is negative or zero
        """
        if amount <= 0:
            raise ValueError(f"Deposit amount must be positive: {amount}")

        entry = LedgerEntry(
            entry_id=self._generate_entry_id(),
            timestamp=timestamp,
            transaction_type=TransactionType.DEPOSIT,
            asset=asset,
            amount=amount,
            description=description
        )

        new_cash_account = CashAccount(
            ledger_cash_balance=cash_account.ledger_cash_balance + amount,
            available_cash=cash_account.available_cash + amount,
            reserved_cash=cash_account.reserved_cash,
            locked_cash=cash_account.locked_cash
        )

        return new_cash_account, entry

    def withdraw(
        self,
        cash_account: CashAccount,
        amount: float,
        timestamp: datetime,
        description: str,
        asset: str = "USDT"
    ) -> tuple[CashAccount, LedgerEntry]:
        """
        Withdraw cash from the account.

        State Transition:
        - available_cash -= amount
        - ledger_cash_balance -= amount

        Args:
            cash_account: Current cash account state
            amount: Amount to withdraw (must be positive)
            timestamp: Transaction timestamp
            description: Description of the withdrawal
            asset: Asset symbol (default: USDT)

        Returns:
            Tuple of (new_cash_account, ledger_entry)

        Raises:
            ValueError: If amount is negative/zero or exceeds available cash
        """
        if amount <= 0:
            raise ValueError(f"Withdrawal amount must be positive: {amount}")

        if amount > cash_account.available_cash:
            raise ValueError(
                f"Insufficient available cash: attempted withdrawal {amount}, "
                f"available {cash_account.available_cash}"
            )

        entry = LedgerEntry(
            entry_id=self._generate_entry_id(),
            timestamp=timestamp,
            transaction_type=TransactionType.WITHDRAWAL,
            asset=asset,
            amount=-amount,
            description=description
        )

        new_cash_account = CashAccount(
            ledger_cash_balance=cash_account.ledger_cash_balance - amount,
            available_cash=cash_account.available_cash - amount,
            reserved_cash=cash_account.reserved_cash,
            locked_cash=cash_account.locked_cash
        )

        return new_cash_account, entry

    def reserve_cash(
        self,
        cash_account: CashAccount,
        amount: float,
        timestamp: datetime,
        description: str,
        asset: str = "USDT"
    ) -> tuple[CashAccount, LedgerEntry]:
        """
        Reserve cash for an order (move from available to reserved).

        State Transition:
        - available_cash -= amount
        - reserved_cash += amount
        - ledger_cash_balance unchanged

        Args:
            cash_account: Current cash account state
            amount: Amount to reserve (must be positive)
            timestamp: Transaction timestamp
            description: Description of the reservation
            asset: Asset symbol (default: USDT)

        Returns:
            Tuple of (new_cash_account, ledger_entry)

        Raises:
            ValueError: If amount is negative/zero or exceeds available cash
        """
        if amount <= 0:
            raise ValueError(f"Reservation amount must be positive: {amount}")

        if amount > cash_account.available_cash:
            raise ValueError(
                f"Insufficient available cash for reservation: attempted {amount}, "
                f"available {cash_account.available_cash}"
            )

        entry = LedgerEntry(
            entry_id=self._generate_entry_id(),
            timestamp=timestamp,
            transaction_type=TransactionType.TRADE_DEBIT,
            asset=asset,
            amount=0.0,
            description=f"RESERVE: {description}"
        )

        new_cash_account = CashAccount(
            ledger_cash_balance=cash_account.ledger_cash_balance,
            available_cash=cash_account.available_cash - amount,
            reserved_cash=cash_account.reserved_cash + amount,
            locked_cash=cash_account.locked_cash
        )

        return new_cash_account, entry

    def release_reserved_cash(
        self,
        cash_account: CashAccount,
        amount: float,
        timestamp: datetime,
        description: str,
        asset: str = "USDT"
    ) -> tuple[CashAccount, LedgerEntry]:
        """
        Release reserved cash back to available (e.g., order cancelled).

        State Transition:
        - reserved_cash -= amount
        - available_cash += amount
        - ledger_cash_balance unchanged

        Args:
            cash_account: Current cash account state
            amount: Amount to release (must be positive)
            timestamp: Transaction timestamp
            description: Description of the release
            asset: Asset symbol (default: USDT)

        Returns:
            Tuple of (new_cash_account, ledger_entry)

        Raises:
            ValueError: If amount is negative/zero or exceeds reserved cash
        """
        if amount <= 0:
            raise ValueError(f"Release amount must be positive: {amount}")

        if amount > cash_account.reserved_cash:
            raise ValueError(
                f"Insufficient reserved cash for release: attempted {amount}, "
                f"reserved {cash_account.reserved_cash}"
            )

        entry = LedgerEntry(
            entry_id=self._generate_entry_id(),
            timestamp=timestamp,
            transaction_type=TransactionType.TRADE_CREDIT,
            asset=asset,
            amount=0.0,
            description=f"RELEASE: {description}"
        )

        new_cash_account = CashAccount(
            ledger_cash_balance=cash_account.ledger_cash_balance,
            available_cash=cash_account.available_cash + amount,
            reserved_cash=cash_account.reserved_cash - amount,
            locked_cash=cash_account.locked_cash
        )

        return new_cash_account, entry

    def apply_fee(
        self,
        cash_account: CashAccount,
        fee_amount: float,
        timestamp: datetime,
        description: str,
        asset: str = "USDT"
    ) -> tuple[CashAccount, LedgerEntry]:
        """
        Apply a fee charge to the account.

        State Transition:
        - ledger_cash_balance -= fee_amount
        - available_cash -= fee_amount

        Args:
            cash_account: Current cash account state
            fee_amount: Fee amount (must be positive)
            timestamp: Transaction timestamp
            description: Description of the fee
            asset: Asset symbol (default: USDT)

        Returns:
            Tuple of (new_cash_account, ledger_entry)

        Raises:
            ValueError: If fee_amount is negative/zero or exceeds available cash
        """
        if fee_amount <= 0:
            raise ValueError(f"Fee amount must be positive: {fee_amount}")

        if fee_amount > cash_account.available_cash:
            raise ValueError(
                f"Insufficient available cash for fee: attempted {fee_amount}, "
                f"available {cash_account.available_cash}"
            )

        entry = LedgerEntry(
            entry_id=self._generate_entry_id(),
            timestamp=timestamp,
            transaction_type=TransactionType.FEE_CHARGE,
            asset=asset,
            amount=-fee_amount,
            description=description
        )

        new_cash_account = CashAccount(
            ledger_cash_balance=cash_account.ledger_cash_balance - fee_amount,
            available_cash=cash_account.available_cash - fee_amount,
            reserved_cash=cash_account.reserved_cash,
            locked_cash=cash_account.locked_cash
        )

        return new_cash_account, entry

    def apply_funding(
        self,
        cash_account: CashAccount,
        funding_amount: float,
        timestamp: datetime,
        description: str,
        asset: str = "USDT"
    ) -> tuple[CashAccount, LedgerEntry]:
        """
        Apply a funding payment (positive or negative).

        State Transition:
        - ledger_cash_balance += funding_amount (can be negative)
        - available_cash += funding_amount (can be negative)

        Positive funding: cash increases (receive funding)
        Negative funding: cash decreases (pay funding)

        Args:
            cash_account: Current cash account state
            funding_amount: Funding amount (positive=receive, negative=pay)
            timestamp: Transaction timestamp
            description: Description of the funding
            asset: Asset symbol (default: USDT)

        Returns:
            Tuple of (new_cash_account, ledger_entry)

        Raises:
            ValueError: If negative funding exceeds available cash
        """
        if funding_amount < 0 and abs(funding_amount) > cash_account.available_cash:
            raise ValueError(
                f"Insufficient available cash for funding payment: "
                f"attempted {abs(funding_amount)}, available {cash_account.available_cash}"
            )

        entry = LedgerEntry(
            entry_id=self._generate_entry_id(),
            timestamp=timestamp,
            transaction_type=TransactionType.FUNDING_ADJUSTMENT,
            asset=asset,
            amount=funding_amount,
            description=description
        )

        new_cash_account = CashAccount(
            ledger_cash_balance=cash_account.ledger_cash_balance + funding_amount,
            available_cash=cash_account.available_cash + funding_amount,
            reserved_cash=cash_account.reserved_cash,
            locked_cash=cash_account.locked_cash
        )

        return new_cash_account, entry

    def apply_realized_pnl(
        self,
        cash_account: CashAccount,
        pnl_amount: float,
        timestamp: datetime,
        description: str,
        asset: str = "USDT"
    ) -> tuple[CashAccount, LedgerEntry]:
        """
        Apply realized profit/loss from a closed position.

        State Transition:
        - ledger_cash_balance += pnl_amount (can be negative)
        - available_cash += pnl_amount (can be negative)

        Positive PnL: profit increases cash
        Negative PnL: loss decreases cash

        Args:
            cash_account: Current cash account state
            pnl_amount: Realized PnL amount (positive=profit, negative=loss)
            timestamp: Transaction timestamp
            description: Description of the PnL
            asset: Asset symbol (default: USDT)

        Returns:
            Tuple of (new_cash_account, ledger_entry)

        Raises:
            ValueError: If negative PnL exceeds available cash
        """
        if pnl_amount < 0 and abs(pnl_amount) > cash_account.available_cash:
            raise ValueError(
                f"Insufficient available cash for realized loss: "
                f"attempted {abs(pnl_amount)}, available {cash_account.available_cash}"
            )

        transaction_type = TransactionType.TRADE_CREDIT if pnl_amount >= 0 else TransactionType.TRADE_DEBIT

        entry = LedgerEntry(
            entry_id=self._generate_entry_id(),
            timestamp=timestamp,
            transaction_type=transaction_type,
            asset=asset,
            amount=pnl_amount,
            description=description
        )

        new_cash_account = CashAccount(
            ledger_cash_balance=cash_account.ledger_cash_balance + pnl_amount,
            available_cash=cash_account.available_cash + pnl_amount,
            reserved_cash=cash_account.reserved_cash,
            locked_cash=cash_account.locked_cash
        )

        return new_cash_account, entry

    @staticmethod
    def _generate_entry_id() -> str:
        """Generate a unique ledger entry ID."""
        return f"ledger_{uuid.uuid4().hex[:16]}"
