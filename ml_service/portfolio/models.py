"""
Immutable Portfolio Domain Models

Pure domain layer with no database, filesystem, or external API access.
All models use frozen dataclasses for immutability.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class AccountType(Enum):
    SPOT = "SPOT"
    MARGIN = "MARGIN"
    FUTURES = "FUTURES"


class PositionType(Enum):
    SPOT = "SPOT"
    MARGIN = "MARGIN"
    FUTURES = "FUTURES"


class RiskMode(Enum):
    NONE = "NONE"
    MARGIN = "MARGIN"
    LIQUIDATION_ENABLED = "LIQUIDATION_ENABLED"


class MarginMode(Enum):
    CROSS = "CROSS"
    ISOLATED = "ISOLATED"


class PortfolioLifecycle(Enum):
    EMPTY = "EMPTY"
    ACTIVE = "ACTIVE"
    MARGIN_CALL = "MARGIN_CALL"
    LIQUIDATED = "LIQUIDATED"
    CLOSED = "CLOSED"


class PositionLifecycle(Enum):
    OPENING = "OPENING"
    OPEN = "OPEN"
    PARTIALLY_CLOSED = "PARTIALLY_CLOSED"
    CLOSED = "CLOSED"


class TransactionType(Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRADE_DEBIT = "TRADE_DEBIT"
    TRADE_CREDIT = "TRADE_CREDIT"
    FEE_CHARGE = "FEE_CHARGE"
    FUNDING_ADJUSTMENT = "FUNDING_ADJUSTMENT"


@dataclass(frozen=True)
class LedgerEntry:
    """Ledger transaction representing the single source of truth for cash movements."""
    entry_id: str
    timestamp: datetime
    transaction_type: TransactionType
    asset: str
    amount: float
    description: str

    def __post_init__(self):
        if not isinstance(self.transaction_type, TransactionType):
            raise ValueError(f"Invalid transaction_type: {self.transaction_type}")
        if not self.entry_id:
            raise ValueError("entry_id cannot be empty")
        if not self.asset:
            raise ValueError("asset cannot be empty")


@dataclass(frozen=True)
class CashAccount:
    """Cash ledger segments within the portfolio."""
    ledger_cash_balance: float
    available_cash: float
    reserved_cash: float
    locked_cash: float

    def __post_init__(self):
        if self.reserved_cash < 0:
            raise ValueError(f"reserved_cash cannot be negative: {self.reserved_cash}")
        if self.locked_cash < 0:
            raise ValueError(f"locked_cash cannot be negative: {self.locked_cash}")
        if self.available_cash < 0:
            raise ValueError(f"available_cash cannot be negative: {self.available_cash}")

        expected_balance = self.available_cash + self.reserved_cash + self.locked_cash
        if abs(self.ledger_cash_balance - expected_balance) > 1e-8:
            raise ValueError(
                f"Cash account invariant violated: "
                f"ledger_cash_balance ({self.ledger_cash_balance}) != "
                f"available ({self.available_cash}) + reserved ({self.reserved_cash}) + locked ({self.locked_cash})"
            )


@dataclass(frozen=True)
class PositionMarginContext:
    """Position-level margin configuration and collateralization state."""
    leverage: float
    initial_margin_ratio: float
    maintenance_margin_ratio: float
    allocated_margin: float

    def __post_init__(self):
        if self.leverage <= 0:
            raise ValueError(f"leverage must be positive: {self.leverage}")
        if not (0 < self.initial_margin_ratio <= 1):
            raise ValueError(f"initial_margin_ratio must be in (0, 1]: {self.initial_margin_ratio}")
        if not (0 < self.maintenance_margin_ratio <= 1):
            raise ValueError(f"maintenance_margin_ratio must be in (0, 1]: {self.maintenance_margin_ratio}")
        if self.maintenance_margin_ratio >= self.initial_margin_ratio:
            raise ValueError(
                f"maintenance_margin_ratio ({self.maintenance_margin_ratio}) "
                f"must be less than initial_margin_ratio ({self.initial_margin_ratio})"
            )
        if self.allocated_margin < 0:
            raise ValueError(f"allocated_margin cannot be negative: {self.allocated_margin}")

        expected_imr = 1.0 / self.leverage
        if abs(self.initial_margin_ratio - expected_imr) > 1e-6:
            raise ValueError(
                f"initial_margin_ratio ({self.initial_margin_ratio}) "
                f"must equal 1/leverage ({expected_imr})"
            )


@dataclass(frozen=True)
class MarginAccount:
    """Margin and collateral ledger parameters."""
    risk_mode: RiskMode
    margin_mode: MarginMode
    initial_margin: float
    maintenance_margin: float
    margin_ratio: float
    liquidation_buffer: float
    liquidation_price: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.risk_mode, RiskMode):
            raise ValueError(f"Invalid risk_mode: {self.risk_mode}")
        if not isinstance(self.margin_mode, MarginMode):
            raise ValueError(f"Invalid margin_mode: {self.margin_mode}")
        if self.initial_margin < 0:
            raise ValueError(f"initial_margin cannot be negative: {self.initial_margin}")
        if self.maintenance_margin < 0:
            raise ValueError(f"maintenance_margin cannot be negative: {self.maintenance_margin}")
        if self.margin_ratio < 0:
            raise ValueError(f"margin_ratio cannot be negative: {self.margin_ratio}")


@dataclass(frozen=True)
class AssetHolding:
    """Tracks non-leveraged spot asset inventory."""
    symbol: str
    quantity: float
    mark_price: float
    market_value: float

    def __post_init__(self):
        if not self.symbol:
            raise ValueError("symbol cannot be empty")
        if self.quantity < 0:
            raise ValueError(f"quantity cannot be negative: {self.quantity}")
        if self.mark_price < 0:
            raise ValueError(f"mark_price cannot be negative: {self.mark_price}")

        expected_value = self.quantity * self.mark_price
        if abs(self.market_value - expected_value) > 1e-8:
            raise ValueError(
                f"market_value ({self.market_value}) != quantity * mark_price ({expected_value})"
            )


@dataclass(frozen=True)
class Position:
    """An active trading position with exposure."""
    symbol: str
    position_type: PositionType
    status: PositionLifecycle
    quantity: float
    average_entry_price: float
    average_exit_price: float
    unrealized_pnl: float
    realized_pnl: float
    margin_required: float
    margin_context: Optional[PositionMarginContext]
    opened_at: datetime
    updated_at: datetime

    def __post_init__(self):
        if not self.symbol:
            raise ValueError("symbol cannot be empty")
        if not isinstance(self.position_type, PositionType):
            raise ValueError(f"Invalid position_type: {self.position_type}")
        if not isinstance(self.status, PositionLifecycle):
            raise ValueError(f"Invalid status: {self.status}")
        if self.quantity == 0 and self.status in (PositionLifecycle.OPEN, PositionLifecycle.OPENING):
            raise ValueError(f"quantity cannot be zero for {self.status} position")
        if self.average_entry_price <= 0:
            raise ValueError(f"average_entry_price must be positive: {self.average_entry_price}")
        if self.margin_required < 0:
            raise ValueError(f"margin_required cannot be negative: {self.margin_required}")
        if self.position_type in (PositionType.MARGIN, PositionType.FUTURES) and self.margin_context is None:
            raise ValueError(f"margin_context required for {self.position_type} positions")
        if self.position_type == PositionType.SPOT and self.margin_context is not None:
            raise ValueError("margin_context must be None for SPOT positions")


@dataclass(frozen=True)
class EquitySnapshot:
    timestamp: datetime
    ledger_cash: float
    holdings_value: float
    unrealized_pnl: float
    total_equity: float

    def __post_init__(self):
        expected_equity = self.ledger_cash + self.holdings_value + self.unrealized_pnl
        if abs(self.total_equity - expected_equity) > 1e-8:
            raise ValueError(
                f"total_equity ({self.total_equity}) != "
                f"ledger_cash ({self.ledger_cash}) + holdings_value ({self.holdings_value}) + "
                f"unrealized_pnl ({self.unrealized_pnl})"
            )


@dataclass(frozen=True)
class ExposureSnapshot:
    timestamp: datetime
    asset_allocation: Dict[str, float]
    gross_exposure: float
    net_exposure: float
    leverage: float
    buying_power: float

    def __post_init__(self):
        if self.gross_exposure < 0:
            raise ValueError(f"gross_exposure cannot be negative: {self.gross_exposure}")
        if abs(self.net_exposure) > self.gross_exposure:
            raise ValueError(
                f"abs(net_exposure) ({abs(self.net_exposure)}) "
                f"cannot exceed gross_exposure ({self.gross_exposure})"
            )
        if self.leverage < 0:
            raise ValueError(f"leverage cannot be negative: {self.leverage}")
        if self.buying_power < 0:
            raise ValueError(f"buying_power cannot be negative: {self.buying_power}")


@dataclass(frozen=True)
class Portfolio:
    portfolio_id: str
    account_type: AccountType
    lifecycle: PortfolioLifecycle
    ledger: List[LedgerEntry]
    cash_ledger: CashAccount
    margin_ledger: MarginAccount
    positions: Dict[str, Position]
    holdings: Dict[str, AssetHolding]
    equity: float
    last_updated: datetime

    def __post_init__(self):
        if not self.portfolio_id:
            raise ValueError("portfolio_id cannot be empty")
        if not isinstance(self.account_type, AccountType):
            raise ValueError(f"Invalid account_type: {self.account_type}")
        if not isinstance(self.lifecycle, PortfolioLifecycle):
            raise ValueError(f"Invalid lifecycle: {self.lifecycle}")

        holdings_value = sum(h.market_value for h in self.holdings.values())
        unrealized_pnl = sum(p.unrealized_pnl for p in self.positions.values())
        expected_equity = self.cash_ledger.ledger_cash_balance + holdings_value + unrealized_pnl

        if abs(self.equity - expected_equity) > 1e-8:
            raise ValueError(
                f"equity ({self.equity}) != "
                f"ledger_cash ({self.cash_ledger.ledger_cash_balance}) + "
                f"holdings_value ({holdings_value}) + unrealized_pnl ({unrealized_pnl})"
            )

        if self.account_type == AccountType.SPOT and self.positions:
            for symbol, pos in self.positions.items():
                if pos.position_type != PositionType.SPOT:
                    raise ValueError(
                        f"SPOT account cannot contain {pos.position_type} position: {symbol}"
                    )

        if self.account_type == AccountType.FUTURES and self.holdings:
            raise ValueError("FUTURES account cannot contain asset holdings")
