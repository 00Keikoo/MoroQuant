"""
Portfolio Service - Aggregate Orchestrator

Coordinates all portfolio engines:
- Ledger Engine (cash mutations)
- Position Engine (position lifecycle)
- Equity Engine (portfolio valuation)
- Margin Engine (margin requirements and liquidation)

Pure functional orchestration with immutable state transitions.
"""

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from ml_service.portfolio.models import (
    AccountType,
    AssetHolding,
    CashAccount,
    EquitySnapshot,
    LedgerEntry,
    MarginAccount,
    Portfolio,
    PortfolioLifecycle,
    Position,
    PositionType,
    RiskMode,
    MarginMode,
)
from ml_service.portfolio.ledger import LedgerService
from ml_service.portfolio.position import PositionService, PositionOpened, PositionUpdated, PositionClosed
from ml_service.portfolio.equity import EquityService, EquityUpdated
from ml_service.portfolio.margin import MarginService, HealthStatus, MarginUpdated, LiquidationTriggered


@dataclass(frozen=True)
class FillEvent:
    """Execution fill event from order execution."""
    symbol: str
    position_type: PositionType
    quantity: float
    execution_price: float
    fee_amount: float
    timestamp: datetime
    margin_context: Optional[object] = None


@dataclass(frozen=True)
class PortfolioState:
    """Immutable portfolio state snapshot."""
    portfolio_id: str
    timestamp: datetime
    cash_account: CashAccount
    positions: Dict[str, Position]
    asset_holdings: Dict[str, AssetHolding]
    equity_snapshot: EquitySnapshot
    margin_status: MarginAccount
    events: List[object]


@dataclass(frozen=True)
class PortfolioUpdated:
    """Event emitted when portfolio state changes."""
    portfolio_id: str
    timestamp: datetime
    equity: float
    margin_status: MarginAccount


@dataclass(frozen=True)
class LiquidationDetected:
    """Event emitted when liquidation is triggered."""
    portfolio_id: str
    position_id: str
    liquidation_price: float
    timestamp: datetime


class PortfolioService:
    """
    Portfolio Service - Aggregate orchestrator for all portfolio operations.

    Coordinates:
    - Ledger Engine: cash mutations
    - Position Engine: position lifecycle
    - Equity Engine: portfolio valuation
    - Margin Engine: margin and liquidation

    All operations maintain immutable state transitions and deterministic calculations.
    """

    def __init__(
        self,
        ledger_service: LedgerService,
        position_service: PositionService,
        equity_service: EquityService,
        margin_service: MarginService
    ):
        """
        Initialize portfolio service with all engine dependencies.

        Args:
            ledger_service: Ledger engine for cash mutations
            position_service: Position engine for position lifecycle
            equity_service: Equity engine for portfolio valuation
            margin_service: Margin engine for margin calculations
        """
        self.ledger = ledger_service
        self.position = position_service
        self.equity = equity_service
        self.margin = margin_service

    def initialize_portfolio(
        self,
        portfolio_id: str,
        initial_cash: float,
        account_type: AccountType = AccountType.SPOT,
        timestamp: Optional[datetime] = None
    ) -> Portfolio:
        """
        Initialize an empty portfolio with starting cash.

        Args:
            portfolio_id: Unique portfolio identifier
            initial_cash: Initial cash balance
            account_type: Account type (SPOT, MARGIN, FUTURES)
            timestamp: Initialization timestamp

        Returns:
            New immutable Portfolio state
        """
        if timestamp is None:
            timestamp = datetime.now()

        if initial_cash < 0:
            raise ValueError(f"initial_cash cannot be negative: {initial_cash}")

        cash_account = CashAccount(
            ledger_cash_balance=initial_cash,
            available_cash=initial_cash,
            reserved_cash=0.0,
            locked_cash=0.0
        )

        margin_account = MarginAccount(
            risk_mode=RiskMode.NONE if account_type == AccountType.SPOT else RiskMode.LIQUIDATION_ENABLED,
            margin_mode=MarginMode.CROSS,
            initial_margin=0.0,
            maintenance_margin=0.0,
            margin_ratio=0.0,
            liquidation_buffer=0.0,
            liquidation_price={}
        )

        portfolio = Portfolio(
            portfolio_id=portfolio_id,
            account_type=account_type,
            lifecycle=PortfolioLifecycle.EMPTY if initial_cash == 0 else PortfolioLifecycle.ACTIVE,
            ledger=[],
            cash_ledger=cash_account,
            margin_ledger=margin_account,
            positions={},
            holdings={},
            equity=initial_cash,
            last_updated=timestamp
        )

        return portfolio

    def apply_fill(
        self,
        portfolio: Portfolio,
        fill_event: FillEvent
    ) -> Tuple[Portfolio, List[object]]:
        """
        Apply an execution fill to the portfolio.

        Flow:
        1. Update Ledger (trade cost + fees)
        2. Update Position (open/increase/reduce)
        3. Generate domain events
        4. Return new immutable Portfolio state

        Args:
            portfolio: Current portfolio state
            fill_event: Execution fill event

        Returns:
            Tuple of (new_portfolio, events)
        """
        events = []
        current_cash = portfolio.cash_ledger
        current_positions = dict(portfolio.positions)
        current_holdings = dict(portfolio.holdings)
        ledger_entries = list(portfolio.ledger)

        symbol = fill_event.symbol
        quantity = fill_event.quantity
        price = fill_event.execution_price
        fee = fill_event.fee_amount
        timestamp = fill_event.timestamp

        if fill_event.position_type == PositionType.SPOT:
            new_cash, fee_entry = self.ledger.apply_fee(
                current_cash, fee, timestamp, f"Spot trade fee for {symbol}"
            )
            ledger_entries.append(fee_entry)

            trade_cost = abs(quantity) * price

            if quantity > 0:
                new_cash, trade_entry = self.ledger.apply_realized_pnl(
                    new_cash, -trade_cost, timestamp, f"Spot buy {symbol}"
                )
                ledger_entries.append(trade_entry)

                if symbol in current_holdings:
                    old_holding = current_holdings[symbol]
                    new_quantity = old_holding.quantity + quantity
                else:
                    new_quantity = quantity

                new_holding = AssetHolding(
                    symbol=symbol,
                    quantity=new_quantity,
                    mark_price=price,
                    market_value=new_quantity * price
                )
                current_holdings[symbol] = new_holding
            else:
                if symbol not in current_holdings:
                    raise ValueError(f"Cannot sell {symbol}: no holding exists")

                old_holding = current_holdings[symbol]
                sell_quantity = abs(quantity)

                if sell_quantity > old_holding.quantity:
                    raise ValueError(
                        f"Cannot sell {sell_quantity} {symbol}: only {old_holding.quantity} available"
                    )

                proceeds = sell_quantity * price
                new_cash, trade_entry = self.ledger.apply_realized_pnl(
                    new_cash, proceeds, timestamp, f"Spot sell {symbol}"
                )
                ledger_entries.append(trade_entry)

                new_quantity = old_holding.quantity - sell_quantity
                if new_quantity > 0:
                    new_holding = AssetHolding(
                        symbol=symbol,
                        quantity=new_quantity,
                        mark_price=price,
                        market_value=new_quantity * price
                    )
                    current_holdings[symbol] = new_holding
                else:
                    del current_holdings[symbol]

            current_cash = new_cash

        else:
            new_cash, fee_entry = self.ledger.apply_fee(
                current_cash, fee, timestamp, f"Futures trade fee for {symbol}"
            )
            ledger_entries.append(fee_entry)
            current_cash = new_cash

            if symbol not in current_positions:
                position, pos_event = self.position.open_position(
                    symbol=symbol,
                    position_type=fill_event.position_type,
                    quantity=quantity,
                    entry_price=price,
                    timestamp=timestamp,
                    margin_context=fill_event.margin_context
                )
                current_positions[symbol] = position
                events.append(pos_event)
            else:
                existing_position = current_positions[symbol]
                is_same_direction = (existing_position.quantity > 0 and quantity > 0) or \
                                   (existing_position.quantity < 0 and quantity < 0)

                if is_same_direction:
                    position, pos_event = self.position.increase_position(
                        existing_position, quantity, price, timestamp
                    )
                    current_positions[symbol] = position
                    events.append(pos_event)
                else:
                    reduce_quantity = abs(quantity)
                    if reduce_quantity < abs(existing_position.quantity):
                        position, pos_event = self.position.reduce_position(
                            existing_position, reduce_quantity, price, timestamp
                        )
                        current_positions[symbol] = position
                        events.append(pos_event)

                        if pos_event.realized_pnl != 0:
                            new_cash, pnl_entry = self.ledger.apply_realized_pnl(
                                current_cash, pos_event.realized_pnl, timestamp,
                                f"Realized PnL from {symbol} reduction"
                            )
                            ledger_entries.append(pnl_entry)
                            current_cash = new_cash
                    else:
                        position, pos_event = self.position.close_position(
                            existing_position, price, timestamp
                        )

                        if pos_event.realized_pnl != 0:
                            new_cash, pnl_entry = self.ledger.apply_realized_pnl(
                                current_cash, pos_event.realized_pnl, timestamp,
                                f"Realized PnL from {symbol} close"
                            )
                            ledger_entries.append(pnl_entry)
                            current_cash = new_cash

                        del current_positions[symbol]
                        events.append(pos_event)

                        if reduce_quantity > abs(existing_position.quantity):
                            remaining_quantity = reduce_quantity - abs(existing_position.quantity)
                            flip_quantity = remaining_quantity if quantity > 0 else -remaining_quantity

                            position, pos_event = self.position.open_position(
                                symbol=symbol,
                                position_type=fill_event.position_type,
                                quantity=flip_quantity,
                                entry_price=price,
                                timestamp=timestamp,
                                margin_context=fill_event.margin_context
                            )
                            current_positions[symbol] = position
                            events.append(pos_event)

        # Calculate new equity based on updated state
        holdings_value = sum(h.market_value for h in current_holdings.values())
        unrealized_pnl = sum(p.unrealized_pnl for p in current_positions.values())
        new_equity = current_cash.ledger_cash_balance + holdings_value + unrealized_pnl

        new_portfolio = Portfolio(
            portfolio_id=portfolio.portfolio_id,
            account_type=portfolio.account_type,
            lifecycle=PortfolioLifecycle.ACTIVE,
            ledger=ledger_entries,
            cash_ledger=current_cash,
            margin_ledger=portfolio.margin_ledger,
            positions=current_positions,
            holdings=current_holdings,
            equity=new_equity,
            last_updated=timestamp
        )

        return new_portfolio, events

    def update_market_prices(
        self,
        portfolio: Portfolio,
        mark_prices: Dict[str, float],
        timestamp: datetime
    ) -> Tuple[Portfolio, List[object]]:
        """
        Update portfolio with new market prices.

        Flow:
        1. Update asset valuations (holdings)
        2. Calculate Equity = Ledger Cash + Holdings Value + Unrealized PnL
        3. Evaluate Margin (maintenance margin, margin ratio, liquidation status)
        4. Create Portfolio Snapshot

        Args:
            portfolio: Current portfolio state
            mark_prices: Current mark prices for all symbols
            timestamp: Update timestamp

        Returns:
            Tuple of (new_portfolio, events)
        """
        events = []

        updated_holdings = {}
        for symbol, holding in portfolio.holdings.items():
            if symbol in mark_prices:
                updated_holding = AssetHolding(
                    symbol=symbol,
                    quantity=holding.quantity,
                    mark_price=mark_prices[symbol],
                    market_value=holding.quantity * mark_prices[symbol]
                )
                updated_holdings[symbol] = updated_holding
            else:
                updated_holdings[symbol] = holding

        updated_positions = {}
        for symbol, position in portfolio.positions.items():
            if symbol in mark_prices:
                unrealized_pnl = self.position.calculate_unrealized_pnl(
                    position, mark_prices[symbol]
                )
                updated_position = replace(position, unrealized_pnl=unrealized_pnl)
                updated_positions[symbol] = updated_position
            else:
                updated_positions[symbol] = position

        # Calculate equity snapshot components directly
        ledger_cash = portfolio.cash_ledger.ledger_cash_balance
        holdings_value = self.equity.calculate_holdings_value(updated_holdings, mark_prices)
        unrealized_pnl = self.equity.calculate_unrealized_pnl(updated_positions, mark_prices)
        total_equity = ledger_cash + holdings_value + unrealized_pnl

        equity_snapshot = EquitySnapshot(
            timestamp=timestamp,
            ledger_cash=ledger_cash,
            holdings_value=holdings_value,
            unrealized_pnl=unrealized_pnl,
            total_equity=total_equity
        )

        total_maintenance_margin = 0.0
        liquidation_prices = {}

        for symbol, position in updated_positions.items():
            if position.position_type != PositionType.SPOT and symbol in mark_prices:
                mm = self.margin.calculate_maintenance_margin(position, mark_prices[symbol])
                total_maintenance_margin += mm

                if position.quantity > 0:
                    liq_price = self.margin.calculate_long_liquidation_price(position)
                elif position.quantity < 0:
                    liq_price = self.margin.calculate_short_liquidation_price(position)
                else:
                    liq_price = None

                if liq_price is not None:
                    liquidation_prices[symbol] = liq_price

        margin_ratio = self.margin.calculate_margin_ratio(
            equity_snapshot.total_equity, total_maintenance_margin
        ) or 0.0

        health_status = self.margin.evaluate_margin_health(
            equity_snapshot.total_equity,
            list(updated_positions.values()),
            mark_prices
        )

        updated_margin_ledger = MarginAccount(
            risk_mode=portfolio.margin_ledger.risk_mode,
            margin_mode=portfolio.margin_ledger.margin_mode,
            initial_margin=portfolio.margin_ledger.initial_margin,
            maintenance_margin=total_maintenance_margin,
            margin_ratio=margin_ratio,
            liquidation_buffer=equity_snapshot.total_equity - total_maintenance_margin,
            liquidation_price=liquidation_prices
        )

        if health_status == HealthStatus.LIQUIDATION:
            for symbol, liq_price in liquidation_prices.items():
                events.append(LiquidationDetected(
                    portfolio_id=portfolio.portfolio_id,
                    position_id=symbol,
                    liquidation_price=liq_price,
                    timestamp=timestamp
                ))

        lifecycle = portfolio.lifecycle
        if health_status == HealthStatus.LIQUIDATION:
            lifecycle = PortfolioLifecycle.LIQUIDATED
        elif health_status in (HealthStatus.DANGER, HealthStatus.WARNING):
            lifecycle = PortfolioLifecycle.MARGIN_CALL
        elif len(updated_positions) == 0 and len(updated_holdings) == 0:
            lifecycle = PortfolioLifecycle.EMPTY if equity_snapshot.total_equity == 0 else PortfolioLifecycle.ACTIVE
        else:
            lifecycle = PortfolioLifecycle.ACTIVE

        new_portfolio = Portfolio(
            portfolio_id=portfolio.portfolio_id,
            account_type=portfolio.account_type,
            lifecycle=lifecycle,
            ledger=portfolio.ledger,
            cash_ledger=portfolio.cash_ledger,
            margin_ledger=updated_margin_ledger,
            positions=updated_positions,
            holdings=updated_holdings,
            equity=equity_snapshot.total_equity,
            last_updated=timestamp
        )

        events.append(PortfolioUpdated(
            portfolio_id=portfolio.portfolio_id,
            timestamp=timestamp,
            equity=equity_snapshot.total_equity,
            margin_status=updated_margin_ledger
        ))

        return new_portfolio, events

    def calculate_portfolio_state(
        self,
        portfolio: Portfolio,
        mark_prices: Dict[str, float],
        timestamp: datetime
    ) -> PortfolioState:
        """
        Calculate complete portfolio state snapshot.

        Args:
            portfolio: Current portfolio state
            mark_prices: Current mark prices
            timestamp: Snapshot timestamp

        Returns:
            PortfolioState snapshot
        """
        updated_portfolio, events = self.update_market_prices(
            portfolio, mark_prices, timestamp
        )

        equity_snapshot = self.equity.create_equity_snapshot(
            updated_portfolio, timestamp, mark_prices
        )

        return PortfolioState(
            portfolio_id=updated_portfolio.portfolio_id,
            timestamp=timestamp,
            cash_account=updated_portfolio.cash_ledger,
            positions=updated_portfolio.positions,
            asset_holdings=updated_portfolio.holdings,
            equity_snapshot=equity_snapshot,
            margin_status=updated_portfolio.margin_ledger,
            events=events
        )

    def close_position(
        self,
        portfolio: Portfolio,
        position_id: str,
        exit_price: float,
        timestamp: datetime
    ) -> Tuple[Portfolio, List[object]]:
        """
        Close a position completely.

        Args:
            portfolio: Current portfolio state
            position_id: Position symbol to close
            exit_price: Exit price
            timestamp: Close timestamp

        Returns:
            Tuple of (new_portfolio, events)
        """
        if position_id not in portfolio.positions:
            raise ValueError(f"Position not found: {position_id}")

        position = portfolio.positions[position_id]

        closed_position, close_event = self.position.close_position(
            position, exit_price, timestamp
        )

        events = [close_event]

        new_cash = portfolio.cash_ledger
        if close_event.realized_pnl != 0:
            new_cash, pnl_entry = self.ledger.apply_realized_pnl(
                new_cash,
                close_event.realized_pnl,
                timestamp,
                f"Realized PnL from {position_id} close"
            )
            ledger_entries = list(portfolio.ledger)
            ledger_entries.append(pnl_entry)
        else:
            ledger_entries = portfolio.ledger

        new_positions = dict(portfolio.positions)
        del new_positions[position_id]

        # Calculate new equity
        holdings_value = sum(h.market_value for h in portfolio.holdings.values())
        unrealized_pnl = sum(p.unrealized_pnl for p in new_positions.values())
        new_equity = new_cash.ledger_cash_balance + holdings_value + unrealized_pnl

        new_portfolio = Portfolio(
            portfolio_id=portfolio.portfolio_id,
            account_type=portfolio.account_type,
            lifecycle=portfolio.lifecycle,
            ledger=ledger_entries,
            cash_ledger=new_cash,
            margin_ledger=portfolio.margin_ledger,
            positions=new_positions,
            holdings=portfolio.holdings,
            equity=new_equity,
            last_updated=timestamp
        )

        return new_portfolio, events
