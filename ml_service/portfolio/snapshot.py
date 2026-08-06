"""
Portfolio Snapshot Domain Models and Service

Immutable snapshot layer for portfolio persistence, historical replay,
and deterministic research simulations.

Pure domain layer with no database or external API access.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from ml_service.portfolio.models import (
    Portfolio,
    Position,
    AssetHolding,
    CashAccount,
    MarginAccount,
)


@dataclass(frozen=True)
class MarginStateSnapshot:
    """Immutable margin state at snapshot time."""
    maintenance_margin: float
    margin_ratio: float
    liquidation_prices: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if self.maintenance_margin < 0:
            raise ValueError(f"maintenance_margin cannot be negative: {self.maintenance_margin}")
        if self.margin_ratio < 0:
            raise ValueError(f"margin_ratio cannot be negative: {self.margin_ratio}")


@dataclass(frozen=True)
class PortfolioSnapshot:
    """
    Immutable portfolio snapshot for persistence and replay.

    Captures complete portfolio state at a specific timestamp,
    enabling deterministic restoration and historical analysis.
    """
    snapshot_id: str
    portfolio_id: str
    timestamp: datetime
    cash_balance: float
    equity: float
    positions: Dict[str, Position]
    holdings: Dict[str, AssetHolding]
    margin_state: MarginStateSnapshot
    events: List[object] = field(default_factory=list)

    def __post_init__(self):
        if not self.snapshot_id:
            raise ValueError("snapshot_id cannot be empty")
        if not self.portfolio_id:
            raise ValueError("portfolio_id cannot be empty")
        if self.equity < 0:
            raise ValueError(f"equity cannot be negative: {self.equity}")


@dataclass(frozen=True)
class SnapshotCreated:
    """Event emitted when a snapshot is created."""
    snapshot_id: str
    portfolio_id: str
    timestamp: datetime
    equity: float


@dataclass(frozen=True)
class SnapshotComparison:
    """Result of comparing two snapshots."""
    snapshot_a_id: str
    snapshot_b_id: str
    timestamp_a: datetime
    timestamp_b: datetime
    equity_delta: float
    cash_delta: float
    positions_added: List[str]
    positions_removed: List[str]
    positions_modified: List[str]
    holdings_delta: Dict[str, float]


class PortfolioSnapshotService:
    """
    Service for creating, restoring, and comparing portfolio snapshots.

    Maintains immutability and deterministic state transitions.
    No business logic calculations - pure snapshot operations.
    """

    def create_snapshot(
        self,
        portfolio: Portfolio,
        timestamp: Optional[datetime] = None
    ) -> tuple[PortfolioSnapshot, SnapshotCreated]:
        """
        Create an immutable snapshot of the portfolio state.

        Args:
            portfolio: Current portfolio state
            timestamp: Optional override timestamp (defaults to portfolio.last_updated)

        Returns:
            Tuple of (PortfolioSnapshot, SnapshotCreated event)
        """
        if timestamp is None:
            timestamp = portfolio.last_updated

        snapshot_id = str(uuid4())

        margin_state = MarginStateSnapshot(
            maintenance_margin=portfolio.margin_ledger.maintenance_margin,
            margin_ratio=portfolio.margin_ledger.margin_ratio,
            liquidation_prices=dict(portfolio.margin_ledger.liquidation_price),
        )

        snapshot = PortfolioSnapshot(
            snapshot_id=snapshot_id,
            portfolio_id=portfolio.portfolio_id,
            timestamp=timestamp,
            cash_balance=portfolio.cash_ledger.ledger_cash_balance,
            equity=portfolio.equity,
            positions=dict(portfolio.positions),
            holdings=dict(portfolio.holdings),
            margin_state=margin_state,
            events=[],
        )

        event = SnapshotCreated(
            snapshot_id=snapshot_id,
            portfolio_id=portfolio.portfolio_id,
            timestamp=timestamp,
            equity=portfolio.equity,
        )

        return snapshot, event

    def restore_snapshot(
        self,
        snapshot: PortfolioSnapshot,
        portfolio: Portfolio
    ) -> Portfolio:
        """
        Restore portfolio state from a snapshot.

        Deterministically reconstructs portfolio state. Does not recalculate
        business logic - uses captured snapshot values directly.

        Args:
            snapshot: Snapshot to restore from
            portfolio: Current portfolio to update

        Returns:
            New Portfolio instance with restored state
        """
        if snapshot.portfolio_id != portfolio.portfolio_id:
            raise ValueError(
                f"Portfolio ID mismatch: snapshot={snapshot.portfolio_id}, "
                f"portfolio={portfolio.portfolio_id}"
            )

        total_holdings_value = sum(h.market_value for h in snapshot.holdings.values())
        total_unrealized_pnl = sum(p.unrealized_pnl for p in snapshot.positions.values())

        available_cash = snapshot.cash_balance - portfolio.cash_ledger.reserved_cash - portfolio.cash_ledger.locked_cash

        restored_cash_ledger = replace(
            portfolio.cash_ledger,
            ledger_cash_balance=snapshot.cash_balance,
            available_cash=available_cash if available_cash >= 0 else 0.0,
        )

        restored_margin_ledger = replace(
            portfolio.margin_ledger,
            maintenance_margin=snapshot.margin_state.maintenance_margin,
            margin_ratio=snapshot.margin_state.margin_ratio,
            liquidation_price=dict(snapshot.margin_state.liquidation_prices),
        )

        restored_portfolio = replace(
            portfolio,
            positions=dict(snapshot.positions),
            holdings=dict(snapshot.holdings),
            equity=snapshot.equity,
            cash_ledger=restored_cash_ledger,
            margin_ledger=restored_margin_ledger,
            last_updated=snapshot.timestamp,
        )

        return restored_portfolio

    def compare_snapshots(
        self,
        snapshot_a: PortfolioSnapshot,
        snapshot_b: PortfolioSnapshot
    ) -> SnapshotComparison:
        """
        Compare two snapshots and identify differences.

        Args:
            snapshot_a: First snapshot (typically earlier)
            snapshot_b: Second snapshot (typically later)

        Returns:
            SnapshotComparison detailing all differences
        """
        if snapshot_a.portfolio_id != snapshot_b.portfolio_id:
            raise ValueError(
                f"Cannot compare snapshots from different portfolios: "
                f"{snapshot_a.portfolio_id} vs {snapshot_b.portfolio_id}"
            )

        positions_a = set(snapshot_a.positions.keys())
        positions_b = set(snapshot_b.positions.keys())

        positions_added = list(positions_b - positions_a)
        positions_removed = list(positions_a - positions_b)

        positions_modified = []
        for symbol in positions_a & positions_b:
            pos_a = snapshot_a.positions[symbol]
            pos_b = snapshot_b.positions[symbol]
            if pos_a != pos_b:
                positions_modified.append(symbol)

        holdings_delta = {}
        all_holdings = set(snapshot_a.holdings.keys()) | set(snapshot_b.holdings.keys())
        for symbol in all_holdings:
            qty_a = snapshot_a.holdings.get(symbol, AssetHolding(symbol, 0, 0, 0)).quantity
            qty_b = snapshot_b.holdings.get(symbol, AssetHolding(symbol, 0, 0, 0)).quantity
            delta = qty_b - qty_a
            if abs(delta) > 1e-10:
                holdings_delta[symbol] = delta

        return SnapshotComparison(
            snapshot_a_id=snapshot_a.snapshot_id,
            snapshot_b_id=snapshot_b.snapshot_id,
            timestamp_a=snapshot_a.timestamp,
            timestamp_b=snapshot_b.timestamp,
            equity_delta=snapshot_b.equity - snapshot_a.equity,
            cash_delta=snapshot_b.cash_balance - snapshot_a.cash_balance,
            positions_added=positions_added,
            positions_removed=positions_removed,
            positions_modified=positions_modified,
            holdings_delta=holdings_delta,
        )
