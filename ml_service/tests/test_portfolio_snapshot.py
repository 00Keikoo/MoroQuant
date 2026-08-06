"""
Tests for Portfolio Snapshot Persistence Layer

Validates:
- Snapshot creation and immutability
- Repository persistence operations
- Historical replay and deterministic restoration
- Multi-portfolio isolation
- Chronological ordering
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from ml_service.portfolio.models import (
    AccountType,
    AssetHolding,
    CashAccount,
    LedgerEntry,
    MarginAccount,
    MarginMode,
    Portfolio,
    PortfolioLifecycle,
    Position,
    PositionLifecycle,
    PositionMarginContext,
    PositionType,
    RiskMode,
    TransactionType,
)
from ml_service.portfolio.snapshot import (
    MarginStateSnapshot,
    PortfolioSnapshot,
    PortfolioSnapshotService,
    SnapshotCreated,
    SnapshotComparison,
)
from ml_service.portfolio.repository import InMemorySnapshotRepository


@pytest.fixture
def base_timestamp():
    return datetime(2026, 8, 3, 10, 0, 0)


@pytest.fixture
def portfolio_id():
    return "portfolio-test-001"


@pytest.fixture
def empty_portfolio(portfolio_id, base_timestamp):
    """Create an empty FUTURES portfolio."""
    return Portfolio(
        portfolio_id=portfolio_id,
        account_type=AccountType.FUTURES,
        lifecycle=PortfolioLifecycle.EMPTY,
        ledger=[],
        cash_ledger=CashAccount(
            ledger_cash_balance=10000.0,
            available_cash=10000.0,
            reserved_cash=0.0,
            locked_cash=0.0,
        ),
        margin_ledger=MarginAccount(
            risk_mode=RiskMode.LIQUIDATION_ENABLED,
            margin_mode=MarginMode.CROSS,
            initial_margin=0.0,
            maintenance_margin=0.0,
            margin_ratio=0.0,
            liquidation_buffer=0.0,
            liquidation_price={},
        ),
        positions={},
        holdings={},
        equity=10000.0,
        last_updated=base_timestamp,
    )


@pytest.fixture
def portfolio_with_position(portfolio_id, base_timestamp):
    """Create portfolio with one open position."""
    margin_context = PositionMarginContext(
        leverage=10.0,
        initial_margin_ratio=0.10,
        maintenance_margin_ratio=0.05,
        allocated_margin=1000.0,
    )

    position = Position(
        symbol="BTCUSDT",
        position_type=PositionType.FUTURES,
        status=PositionLifecycle.OPEN,
        quantity=1.0,
        average_entry_price=50000.0,
        average_exit_price=0.0,
        unrealized_pnl=0.0,
        realized_pnl=0.0,
        margin_required=1000.0,
        margin_context=margin_context,
        opened_at=base_timestamp,
        updated_at=base_timestamp,
    )

    return Portfolio(
        portfolio_id=portfolio_id,
        account_type=AccountType.FUTURES,
        lifecycle=PortfolioLifecycle.ACTIVE,
        ledger=[
            LedgerEntry(
                entry_id="entry-001",
                timestamp=base_timestamp,
                transaction_type=TransactionType.DEPOSIT,
                asset="USDT",
                amount=10000.0,
                description="Initial deposit",
            ),
            LedgerEntry(
                entry_id="entry-002",
                timestamp=base_timestamp,
                transaction_type=TransactionType.FEE_CHARGE,
                asset="USDT",
                amount=-5.0,
                description="Trading fee",
            ),
        ],
        cash_ledger=CashAccount(
            ledger_cash_balance=9995.0,
            available_cash=8995.0,
            reserved_cash=0.0,
            locked_cash=1000.0,
        ),
        margin_ledger=MarginAccount(
            risk_mode=RiskMode.LIQUIDATION_ENABLED,
            margin_mode=MarginMode.CROSS,
            initial_margin=1000.0,
            maintenance_margin=500.0,
            margin_ratio=0.05,
            liquidation_buffer=9495.0,
            liquidation_price={"BTCUSDT": 47368.42},
        ),
        positions={"BTCUSDT": position},
        holdings={},
        equity=9995.0,
        last_updated=base_timestamp,
    )


@pytest.fixture
def snapshot_service():
    return PortfolioSnapshotService()


@pytest.fixture
def repository():
    return InMemorySnapshotRepository()


class TestSnapshotCreation:
    """Test 1: Create snapshot."""

    def test_create_snapshot_from_empty_portfolio(self, snapshot_service, empty_portfolio, base_timestamp):
        snapshot, event = snapshot_service.create_snapshot(empty_portfolio, base_timestamp)

        assert isinstance(snapshot, PortfolioSnapshot)
        assert snapshot.portfolio_id == empty_portfolio.portfolio_id
        assert snapshot.timestamp == base_timestamp
        assert snapshot.cash_balance == 10000.0
        assert snapshot.equity == 10000.0
        assert len(snapshot.positions) == 0
        assert len(snapshot.holdings) == 0
        assert snapshot.margin_state.maintenance_margin == 0.0
        assert snapshot.margin_state.margin_ratio == 0.0

        assert isinstance(event, SnapshotCreated)
        assert event.snapshot_id == snapshot.snapshot_id
        assert event.portfolio_id == empty_portfolio.portfolio_id
        assert event.equity == 10000.0

    def test_create_snapshot_from_portfolio_with_position(
        self, snapshot_service, portfolio_with_position, base_timestamp
    ):
        snapshot, event = snapshot_service.create_snapshot(portfolio_with_position, base_timestamp)

        assert snapshot.portfolio_id == portfolio_with_position.portfolio_id
        assert snapshot.cash_balance == 9995.0
        assert snapshot.equity == 9995.0
        assert len(snapshot.positions) == 1
        assert "BTCUSDT" in snapshot.positions
        assert snapshot.positions["BTCUSDT"].quantity == 1.0
        assert snapshot.margin_state.maintenance_margin == 500.0
        assert snapshot.margin_state.margin_ratio == 0.05
        assert "BTCUSDT" in snapshot.margin_state.liquidation_prices

    def test_snapshot_uses_portfolio_timestamp_by_default(
        self, snapshot_service, empty_portfolio
    ):
        snapshot, _ = snapshot_service.create_snapshot(empty_portfolio)
        assert snapshot.timestamp == empty_portfolio.last_updated

    def test_snapshot_can_override_timestamp(
        self, snapshot_service, empty_portfolio, base_timestamp
    ):
        custom_timestamp = base_timestamp + timedelta(hours=1)
        snapshot, _ = snapshot_service.create_snapshot(empty_portfolio, custom_timestamp)
        assert snapshot.timestamp == custom_timestamp


class TestSnapshotImmutability:
    """Test 2: Snapshot immutability."""

    def test_snapshot_is_frozen(self, snapshot_service, empty_portfolio):
        snapshot, _ = snapshot_service.create_snapshot(empty_portfolio)

        with pytest.raises(Exception):
            snapshot.equity = 5000.0

    def test_margin_state_is_frozen(self, snapshot_service, empty_portfolio):
        snapshot, _ = snapshot_service.create_snapshot(empty_portfolio)

        with pytest.raises(Exception):
            snapshot.margin_state.margin_ratio = 0.5

    def test_positions_dict_is_independent(self, snapshot_service, portfolio_with_position):
        snapshot, _ = snapshot_service.create_snapshot(portfolio_with_position)

        original_positions = snapshot.positions
        modified_positions = dict(snapshot.positions)

        eth_margin_context = PositionMarginContext(
            leverage=10.0,
            initial_margin_ratio=0.10,
            maintenance_margin_ratio=0.05,
            allocated_margin=300.0,
        )

        modified_positions["ETHUSDT"] = Position(
            symbol="ETHUSDT",
            position_type=PositionType.FUTURES,
            status=PositionLifecycle.OPEN,
            quantity=10.0,
            average_entry_price=3000.0,
            average_exit_price=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            margin_required=300.0,
            margin_context=eth_margin_context,
            opened_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert len(original_positions) == 1
        assert "ETHUSDT" not in original_positions


class TestRepositorySave:
    """Test 3: Save snapshot."""

    def test_save_snapshot(self, repository, snapshot_service, empty_portfolio):
        snapshot, _ = snapshot_service.create_snapshot(empty_portfolio)
        repository.save(snapshot)

        assert repository.count() == 1
        assert repository.count_for_portfolio(empty_portfolio.portfolio_id) == 1

    def test_save_multiple_snapshots(self, repository, snapshot_service, empty_portfolio, base_timestamp):
        snapshots = []
        for i in range(5):
            timestamp = base_timestamp + timedelta(minutes=i)
            snapshot, _ = snapshot_service.create_snapshot(empty_portfolio, timestamp)
            repository.save(snapshot)
            snapshots.append(snapshot)

        assert repository.count() == 5
        assert repository.count_for_portfolio(empty_portfolio.portfolio_id) == 5

    def test_save_duplicate_snapshot_raises_error(self, repository, snapshot_service, empty_portfolio):
        snapshot, _ = snapshot_service.create_snapshot(empty_portfolio)
        repository.save(snapshot)

        with pytest.raises(ValueError, match="already exists"):
            repository.save(snapshot)


class TestRepositoryRetrieval:
    """Test 4: Retrieve snapshot."""

    def test_get_existing_snapshot(self, repository, snapshot_service, empty_portfolio):
        snapshot, _ = snapshot_service.create_snapshot(empty_portfolio)
        repository.save(snapshot)

        retrieved = repository.get(snapshot.snapshot_id)
        assert retrieved is not None
        assert retrieved.snapshot_id == snapshot.snapshot_id
        assert retrieved.portfolio_id == snapshot.portfolio_id
        assert retrieved.equity == snapshot.equity

    def test_get_nonexistent_snapshot_returns_none(self, repository):
        retrieved = repository.get("nonexistent-id")
        assert retrieved is None


class TestLatestSnapshotQuery:
    """Test 5: Latest snapshot query."""

    def test_get_latest_from_empty_repository(self, repository, portfolio_id):
        latest = repository.get_latest(portfolio_id)
        assert latest is None

    def test_get_latest_snapshot(self, repository, snapshot_service, empty_portfolio, base_timestamp):
        snapshots = []
        for i in range(5):
            timestamp = base_timestamp + timedelta(minutes=i)
            snapshot, _ = snapshot_service.create_snapshot(empty_portfolio, timestamp)
            repository.save(snapshot)
            snapshots.append(snapshot)

        latest = repository.get_latest(empty_portfolio.portfolio_id)
        assert latest is not None
        assert latest.snapshot_id == snapshots[-1].snapshot_id
        assert latest.timestamp == snapshots[-1].timestamp


class TestHistoricalSnapshotQuery:
    """Test 6: Historical snapshot query."""

    def test_get_history_returns_snapshots_in_time_range(
        self, repository, snapshot_service, empty_portfolio, base_timestamp
    ):
        timestamps = [base_timestamp + timedelta(hours=i) for i in range(10)]

        for ts in timestamps:
            snapshot, _ = snapshot_service.create_snapshot(empty_portfolio, ts)
            repository.save(snapshot)

        start_time = base_timestamp + timedelta(hours=2)
        end_time = base_timestamp + timedelta(hours=7)

        history = repository.get_history(empty_portfolio.portfolio_id, start_time, end_time)

        assert len(history) == 6
        for snapshot in history:
            assert start_time <= snapshot.timestamp <= end_time

    def test_get_history_returns_chronological_order(
        self, repository, snapshot_service, empty_portfolio, base_timestamp
    ):
        timestamps = [
            base_timestamp + timedelta(hours=5),
            base_timestamp + timedelta(hours=1),
            base_timestamp + timedelta(hours=8),
            base_timestamp + timedelta(hours=3),
        ]

        for ts in timestamps:
            snapshot, _ = snapshot_service.create_snapshot(empty_portfolio, ts)
            repository.save(snapshot)

        start_time = base_timestamp
        end_time = base_timestamp + timedelta(hours=10)

        history = repository.get_history(empty_portfolio.portfolio_id, start_time, end_time)

        assert len(history) == 4
        for i in range(len(history) - 1):
            assert history[i].timestamp <= history[i + 1].timestamp


class TestSnapshotRestoration:
    """Test 7: Restore snapshot."""

    def test_restore_snapshot(self, snapshot_service, empty_portfolio, portfolio_with_position):
        snapshot, _ = snapshot_service.create_snapshot(portfolio_with_position)

        restored = snapshot_service.restore_snapshot(snapshot, empty_portfolio)

        assert restored.portfolio_id == snapshot.portfolio_id
        assert restored.equity == snapshot.equity
        assert len(restored.positions) == len(snapshot.positions)
        assert "BTCUSDT" in restored.positions
        assert restored.margin_ledger.maintenance_margin == snapshot.margin_state.maintenance_margin
        assert restored.margin_ledger.margin_ratio == snapshot.margin_state.margin_ratio
        assert restored.last_updated == snapshot.timestamp

    def test_restore_snapshot_with_mismatched_portfolio_raises_error(
        self, snapshot_service, empty_portfolio, portfolio_with_position
    ):
        snapshot, _ = snapshot_service.create_snapshot(portfolio_with_position)

        different_portfolio = Portfolio(
            portfolio_id="different-portfolio",
            account_type=AccountType.FUTURES,
            lifecycle=PortfolioLifecycle.EMPTY,
            ledger=[],
            cash_ledger=CashAccount(
                ledger_cash_balance=5000.0,
                available_cash=5000.0,
                reserved_cash=0.0,
                locked_cash=0.0,
            ),
            margin_ledger=MarginAccount(
                risk_mode=RiskMode.NONE,
                margin_mode=MarginMode.CROSS,
                initial_margin=0.0,
                maintenance_margin=0.0,
                margin_ratio=0.0,
                liquidation_buffer=0.0,
                liquidation_price={},
            ),
            positions={},
            holdings={},
            equity=5000.0,
            last_updated=datetime.now(),
        )

        with pytest.raises(ValueError, match="Portfolio ID mismatch"):
            snapshot_service.restore_snapshot(snapshot, different_portfolio)


class TestSnapshotComparison:
    """Test 8: Compare snapshots."""

    def test_compare_empty_snapshots(self, snapshot_service, empty_portfolio, base_timestamp):
        snapshot_a, _ = snapshot_service.create_snapshot(empty_portfolio, base_timestamp)
        snapshot_b, _ = snapshot_service.create_snapshot(empty_portfolio, base_timestamp + timedelta(minutes=5))

        comparison = snapshot_service.compare_snapshots(snapshot_a, snapshot_b)

        assert comparison.snapshot_a_id == snapshot_a.snapshot_id
        assert comparison.snapshot_b_id == snapshot_b.snapshot_id
        assert comparison.equity_delta == 0.0
        assert comparison.cash_delta == 0.0
        assert len(comparison.positions_added) == 0
        assert len(comparison.positions_removed) == 0
        assert len(comparison.holdings_delta) == 0

    def test_compare_with_position_change(
        self, snapshot_service, empty_portfolio, portfolio_with_position
    ):
        snapshot_a, _ = snapshot_service.create_snapshot(empty_portfolio)
        snapshot_b, _ = snapshot_service.create_snapshot(portfolio_with_position)

        comparison = snapshot_service.compare_snapshots(snapshot_a, snapshot_b)

        assert comparison.equity_delta == pytest.approx(-5.0)
        assert comparison.cash_delta == pytest.approx(-5.0)
        assert "BTCUSDT" in comparison.positions_added
        assert len(comparison.positions_removed) == 0

    def test_compare_different_portfolios_raises_error(
        self, snapshot_service, empty_portfolio, base_timestamp
    ):
        snapshot_a, _ = snapshot_service.create_snapshot(empty_portfolio)

        different_portfolio = Portfolio(
            portfolio_id="different-portfolio",
            account_type=AccountType.FUTURES,
            lifecycle=PortfolioLifecycle.EMPTY,
            ledger=[],
            cash_ledger=CashAccount(
                ledger_cash_balance=5000.0,
                available_cash=5000.0,
                reserved_cash=0.0,
                locked_cash=0.0,
            ),
            margin_ledger=MarginAccount(
                risk_mode=RiskMode.NONE,
                margin_mode=MarginMode.CROSS,
                initial_margin=0.0,
                maintenance_margin=0.0,
                margin_ratio=0.0,
                liquidation_buffer=0.0,
                liquidation_price={},
            ),
            positions={},
            holdings={},
            equity=5000.0,
            last_updated=base_timestamp,
        )

        snapshot_b, _ = snapshot_service.create_snapshot(different_portfolio)

        with pytest.raises(ValueError, match="different portfolios"):
            snapshot_service.compare_snapshots(snapshot_a, snapshot_b)


class TestDeterministicReplay:
    """Test 9: Deterministic replay."""

    def test_snapshot_restore_produces_identical_state(
        self, snapshot_service, portfolio_with_position
    ):
        snapshot, _ = snapshot_service.create_snapshot(portfolio_with_position)

        restored_once = snapshot_service.restore_snapshot(snapshot, portfolio_with_position)
        snapshot_2, _ = snapshot_service.create_snapshot(restored_once)

        restored_twice = snapshot_service.restore_snapshot(snapshot_2, portfolio_with_position)

        assert restored_once.equity == restored_twice.equity
        assert restored_once.cash_ledger.ledger_cash_balance == restored_twice.cash_ledger.ledger_cash_balance
        assert len(restored_once.positions) == len(restored_twice.positions)

        for symbol in restored_once.positions:
            pos_1 = restored_once.positions[symbol]
            pos_2 = restored_twice.positions[symbol]
            assert pos_1.quantity == pos_2.quantity
            assert pos_1.average_entry_price == pos_2.average_entry_price
            assert pos_1.unrealized_pnl == pos_2.unrealized_pnl

    def test_multiple_restore_cycles_maintain_determinism(
        self, snapshot_service, repository, portfolio_with_position
    ):
        original_snapshot, _ = snapshot_service.create_snapshot(portfolio_with_position)
        repository.save(original_snapshot)

        current_portfolio = portfolio_with_position
        for _ in range(5):
            restored = snapshot_service.restore_snapshot(original_snapshot, current_portfolio)
            current_portfolio = restored

        final_snapshot, _ = snapshot_service.create_snapshot(current_portfolio)

        assert final_snapshot.equity == original_snapshot.equity
        assert final_snapshot.cash_balance == original_snapshot.cash_balance
        assert len(final_snapshot.positions) == len(original_snapshot.positions)


class TestMultiplePortfolioIsolation:
    """Test 10: Multiple portfolio isolation."""

    def test_repository_isolates_portfolios(
        self, repository, snapshot_service, base_timestamp
    ):
        portfolio_a = Portfolio(
            portfolio_id="portfolio-a",
            account_type=AccountType.FUTURES,
            lifecycle=PortfolioLifecycle.EMPTY,
            ledger=[],
            cash_ledger=CashAccount(10000.0, 10000.0, 0.0, 0.0),
            margin_ledger=MarginAccount(
                RiskMode.NONE, MarginMode.CROSS, 0.0, 0.0, 0.0, 0.0, {}
            ),
            positions={},
            holdings={},
            equity=10000.0,
            last_updated=base_timestamp,
        )

        portfolio_b = Portfolio(
            portfolio_id="portfolio-b",
            account_type=AccountType.FUTURES,
            lifecycle=PortfolioLifecycle.EMPTY,
            ledger=[],
            cash_ledger=CashAccount(5000.0, 5000.0, 0.0, 0.0),
            margin_ledger=MarginAccount(
                RiskMode.NONE, MarginMode.CROSS, 0.0, 0.0, 0.0, 0.0, {}
            ),
            positions={},
            holdings={},
            equity=5000.0,
            last_updated=base_timestamp,
        )

        for i in range(3):
            ts = base_timestamp + timedelta(minutes=i)
            snap_a, _ = snapshot_service.create_snapshot(portfolio_a, ts)
            snap_b, _ = snapshot_service.create_snapshot(portfolio_b, ts)
            repository.save(snap_a)
            repository.save(snap_b)

        assert repository.count_for_portfolio("portfolio-a") == 3
        assert repository.count_for_portfolio("portfolio-b") == 3
        assert repository.count() == 6

        latest_a = repository.get_latest("portfolio-a")
        latest_b = repository.get_latest("portfolio-b")

        assert latest_a.portfolio_id == "portfolio-a"
        assert latest_a.equity == 10000.0
        assert latest_b.portfolio_id == "portfolio-b"
        assert latest_b.equity == 5000.0


class TestChronologicalOrdering:
    """Test 11: Chronological ordering."""

    def test_snapshots_maintain_chronological_order(
        self, repository, snapshot_service, empty_portfolio, base_timestamp
    ):
        timestamps = [
            base_timestamp + timedelta(hours=7),
            base_timestamp + timedelta(hours=2),
            base_timestamp + timedelta(hours=9),
            base_timestamp + timedelta(hours=1),
            base_timestamp + timedelta(hours=5),
        ]

        for ts in timestamps:
            snapshot, _ = snapshot_service.create_snapshot(empty_portfolio, ts)
            repository.save(snapshot)

        history = repository.get_history(
            empty_portfolio.portfolio_id,
            base_timestamp,
            base_timestamp + timedelta(hours=10)
        )

        for i in range(len(history) - 1):
            assert history[i].timestamp < history[i + 1].timestamp

    def test_latest_returns_most_recent_regardless_of_save_order(
        self, repository, snapshot_service, empty_portfolio, base_timestamp
    ):
        timestamps = [
            base_timestamp + timedelta(hours=5),
            base_timestamp + timedelta(hours=1),
            base_timestamp + timedelta(hours=9),
            base_timestamp + timedelta(hours=3),
        ]

        for ts in timestamps:
            snapshot, _ = snapshot_service.create_snapshot(empty_portfolio, ts)
            repository.save(snapshot)

        latest = repository.get_latest(empty_portfolio.portfolio_id)
        assert latest.timestamp == base_timestamp + timedelta(hours=9)


class TestInvalidSnapshotRejection:
    """Test 12: Invalid snapshot rejection."""

    def test_reject_snapshot_with_empty_id(self, base_timestamp):
        with pytest.raises(ValueError, match="snapshot_id cannot be empty"):
            PortfolioSnapshot(
                snapshot_id="",
                portfolio_id="test-portfolio",
                timestamp=base_timestamp,
                cash_balance=10000.0,
                equity=10000.0,
                positions={},
                holdings={},
                margin_state=MarginStateSnapshot(0.0, 0.0, {}),
            )

    def test_reject_snapshot_with_empty_portfolio_id(self, base_timestamp):
        with pytest.raises(ValueError, match="portfolio_id cannot be empty"):
            PortfolioSnapshot(
                snapshot_id="snap-001",
                portfolio_id="",
                timestamp=base_timestamp,
                cash_balance=10000.0,
                equity=10000.0,
                positions={},
                holdings={},
                margin_state=MarginStateSnapshot(0.0, 0.0, {}),
            )

    def test_reject_snapshot_with_negative_equity(self, base_timestamp):
        with pytest.raises(ValueError, match="equity cannot be negative"):
            PortfolioSnapshot(
                snapshot_id="snap-001",
                portfolio_id="test-portfolio",
                timestamp=base_timestamp,
                cash_balance=10000.0,
                equity=-1000.0,
                positions={},
                holdings={},
                margin_state=MarginStateSnapshot(0.0, 0.0, {}),
            )

    def test_reject_margin_state_with_negative_maintenance_margin(self):
        with pytest.raises(ValueError, match="maintenance_margin cannot be negative"):
            MarginStateSnapshot(
                maintenance_margin=-100.0,
                margin_ratio=0.5,
                liquidation_prices={},
            )

    def test_reject_margin_state_with_negative_margin_ratio(self):
        with pytest.raises(ValueError, match="margin_ratio cannot be negative"):
            MarginStateSnapshot(
                maintenance_margin=100.0,
                margin_ratio=-0.5,
                liquidation_prices={},
            )

    def test_repository_delete_operations(self, repository, snapshot_service, empty_portfolio):
        snapshot, _ = snapshot_service.create_snapshot(empty_portfolio)
        repository.save(snapshot)

        assert repository.count() == 1

        result = repository.delete(snapshot.snapshot_id)
        assert result is True
        assert repository.count() == 0

        result = repository.delete("nonexistent-id")
        assert result is False
