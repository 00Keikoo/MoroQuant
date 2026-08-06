"""
Equity Engine - Deterministic Portfolio Valuation

Implements the Universal Equity Formula:
    Equity = Ledger Cash Balance + Σ Asset Holdings Market Value + Σ Position Unrealized PnL

Pure functional accounting - no side effects, no database access.
All calculations are deterministic given inputs.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict
from uuid import uuid4

from ml_service.portfolio.models import (
    AssetHolding,
    CashAccount,
    EquitySnapshot,
    Portfolio,
    Position,
)


@dataclass(frozen=True)
class EquityUpdated:
    """Event emitted when portfolio equity changes."""
    portfolio_id: str
    timestamp: datetime
    previous_equity: float
    current_equity: float
    change: float


class EquityService:
    """
    Equity calculation engine for deterministic portfolio valuation.

    Financial Invariants:
    1. Ledger cash already includes realized PnL, fees, and funding
    2. Asset holdings valued at mark price (quantity × mark_price)
    3. Position unrealized PnL calculated from mark-to-market
    4. Total equity = cash + holdings + unrealized PnL
    """

    @staticmethod
    def calculate_holdings_value(
        asset_holdings: Dict[str, AssetHolding],
        mark_prices: Dict[str, float]
    ) -> float:
        """
        Calculate total market value of spot asset holdings.

        Formula: Σ (quantity × mark_price)

        Args:
            asset_holdings: Dictionary of symbol -> AssetHolding
            mark_prices: Dictionary of symbol -> current mark price

        Returns:
            Total market value in quote currency (e.g., USDT)

        Raises:
            ValueError: If mark price missing for any holding
        """
        if not asset_holdings:
            return 0.0

        total_value = 0.0

        for symbol, holding in asset_holdings.items():
            if symbol not in mark_prices:
                raise ValueError(
                    f"Missing mark price for asset holding: {symbol}"
                )

            mark_price = mark_prices[symbol]
            if mark_price < 0:
                raise ValueError(
                    f"Invalid mark price for {symbol}: {mark_price}"
                )

            market_value = holding.quantity * mark_price
            total_value += market_value

        return total_value

    @staticmethod
    def calculate_unrealized_pnl(
        positions: Dict[str, Position],
        mark_prices: Dict[str, float]
    ) -> float:
        """
        Calculate total unrealized PnL across all positions.

        Formula:
            LONG: (mark_price - average_entry_price) × quantity
            SHORT: (average_entry_price - mark_price) × |quantity|

        Args:
            positions: Dictionary of symbol -> Position
            mark_prices: Dictionary of symbol -> current mark price

        Returns:
            Total unrealized PnL (can be positive or negative)

        Raises:
            ValueError: If mark price missing for any position
        """
        if not positions:
            return 0.0

        total_unrealized_pnl = 0.0

        for symbol, position in positions.items():
            if symbol not in mark_prices:
                raise ValueError(
                    f"Missing mark price for position: {symbol}"
                )

            mark_price = mark_prices[symbol]
            if mark_price <= 0:
                raise ValueError(
                    f"Invalid mark price for {symbol}: {mark_price}"
                )

            # LONG: positive quantity, SHORT: negative quantity
            if position.quantity > 0:
                # Long position
                pnl = (mark_price - position.average_entry_price) * position.quantity
            elif position.quantity < 0:
                # Short position
                pnl = (position.average_entry_price - mark_price) * abs(position.quantity)
            else:
                # Zero quantity position should not exist in active positions
                raise ValueError(
                    f"Invalid position with zero quantity: {symbol}"
                )

            total_unrealized_pnl += pnl

        return total_unrealized_pnl

    @staticmethod
    def calculate_equity(
        cash_account: CashAccount,
        asset_holdings: Dict[str, AssetHolding],
        positions: Dict[str, Position],
        mark_prices: Dict[str, float]
    ) -> float:
        """
        Calculate total portfolio equity using the Universal Equity Formula.

        Formula:
            Equity = Ledger Cash Balance
                   + Σ Asset Holdings Market Value
                   + Σ Position Unrealized PnL

        Important: Ledger cash balance ALREADY includes:
            - Realized PnL
            - Fees paid
            - Funding payments
            - Deposits and withdrawals

        DO NOT add these again to avoid double-counting.

        Args:
            cash_account: Cash ledger with balances
            asset_holdings: Spot asset inventory
            positions: Active trading positions
            mark_prices: Current mark prices for all assets/positions

        Returns:
            Total portfolio equity

        Raises:
            ValueError: If validation fails or mark prices missing
        """
        if cash_account is None:
            raise ValueError("cash_account cannot be None")

        if mark_prices is None:
            raise ValueError("mark_prices cannot be None")

        # Component 1: Ledger cash (already includes realized PnL, fees, funding)
        ledger_cash = cash_account.ledger_cash_balance

        # Component 2: Asset holdings market value
        holdings_value = EquityService.calculate_holdings_value(
            asset_holdings or {},
            mark_prices
        )

        # Component 3: Position unrealized PnL
        unrealized_pnl = EquityService.calculate_unrealized_pnl(
            positions or {},
            mark_prices
        )

        # Universal Equity Formula
        total_equity = ledger_cash + holdings_value + unrealized_pnl

        return total_equity

    @staticmethod
    def create_equity_snapshot(
        portfolio: Portfolio,
        timestamp: datetime,
        mark_prices: Dict[str, float]
    ) -> EquitySnapshot:
        """
        Create an immutable equity snapshot for the portfolio at a given timestamp.

        Args:
            portfolio: Current portfolio state
            timestamp: Snapshot timestamp
            mark_prices: Current mark prices

        Returns:
            Immutable EquitySnapshot with all equity components

        Raises:
            ValueError: If validation fails
        """
        if portfolio is None:
            raise ValueError("portfolio cannot be None")

        if timestamp is None:
            raise ValueError("timestamp cannot be None")

        if mark_prices is None:
            raise ValueError("mark_prices cannot be None")

        # Calculate equity components
        ledger_cash = portfolio.cash_ledger.ledger_cash_balance

        holdings_value = EquityService.calculate_holdings_value(
            portfolio.holdings,
            mark_prices
        )

        unrealized_pnl = EquityService.calculate_unrealized_pnl(
            portfolio.positions,
            mark_prices
        )

        total_equity = ledger_cash + holdings_value + unrealized_pnl

        # Create immutable snapshot
        snapshot = EquitySnapshot(
            timestamp=timestamp,
            ledger_cash=ledger_cash,
            holdings_value=holdings_value,
            unrealized_pnl=unrealized_pnl,
            total_equity=total_equity
        )

        return snapshot

    @staticmethod
    def create_equity_updated_event(
        portfolio_id: str,
        timestamp: datetime,
        previous_equity: float,
        current_equity: float
    ) -> EquityUpdated:
        """
        Create an EquityUpdated event when portfolio equity changes.

        Args:
            portfolio_id: Portfolio identifier
            timestamp: Event timestamp
            previous_equity: Previous equity value
            current_equity: Current equity value

        Returns:
            EquityUpdated event
        """
        if not portfolio_id:
            raise ValueError("portfolio_id cannot be empty")

        if timestamp is None:
            raise ValueError("timestamp cannot be None")

        change = current_equity - previous_equity

        return EquityUpdated(
            portfolio_id=portfolio_id,
            timestamp=timestamp,
            previous_equity=previous_equity,
            current_equity=current_equity,
            change=change
        )
