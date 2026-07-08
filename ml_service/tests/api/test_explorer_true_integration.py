"""TRUE Integration Tests for Trade Explorer API.

Tests the complete stack with a temporary SQLite database:
- Real Repositories
- Real ExplorerQueryService
- Real TradeAnalytics
- Real FastAPI Routes
- Real Database

No mocks. Tests actual behavior end-to-end.
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from fastapi import FastAPI
from ml_service.api.explorer_routes import router as explorer_router, get_explorer_service
from ml_service.services.explorer_query_service import ExplorerQueryService
from ml_service.repositories.trade_repository import TradeRepository
from ml_service.repositories.signal_repository import SignalRepository
from ml_service.repositories.equity_repository import EquityRepository


@pytest.fixture(scope="function")
def temp_db():
    """Create temporary SQLite database with schema."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
    db_path = temp_file.name
    temp_file.close()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL CHECK(direction IN ('LONG', 'SHORT')),
            entry_price REAL NOT NULL,
            current_price REAL,
            size_usdt REAL NOT NULL,
            qty REAL NOT NULL,
            stop_loss REAL,
            take_profit REAL,
            signal_id INTEGER,
            status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'TP_HIT', 'SL_HIT', 'EXPIRED', 'MANUAL_CLOSE')),
            realized_pnl REAL NOT NULL DEFAULT 0.0,
            opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP,
            confidence INTEGER,
            regime TEXT,
            timeframe TEXT,
            prob_short REAL,
            prob_neutral REAL,
            prob_long REAL,
            execution_edge REAL,
            skip_reason TEXT,
            mae REAL DEFAULT 0.0,
            mfe REAL DEFAULT 0.0,
            mae_timestamp TIMESTAMP,
            mfe_timestamp TIMESTAMP,
            profit_capture_ratio REAL,
            final_exit_reason TEXT,
            trailing_stop_activated INTEGER DEFAULT 0,
            sl_move_count INTEGER DEFAULT 0,
            break_even_triggered INTEGER DEFAULT 0,
            execution_policy TEXT DEFAULT 'FIXED_SL' CHECK(execution_policy IN ('OFF', 'FIXED_SL', 'BREAK_EVEN', 'TRAILING'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            direction TEXT NOT NULL CHECK(direction IN ('long', 'short', 'neutral')),
            confidence INTEGER NOT NULL CHECK(confidence >= 0 AND confidence <= 100),
            features_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_account (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            balance REAL NOT NULL,
            equity REAL NOT NULL,
            margin_used REAL NOT NULL,
            unrealized_pnl REAL NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("CREATE INDEX idx_paper_positions_status ON paper_positions(status)")
    cursor.execute("CREATE INDEX idx_paper_positions_symbol ON paper_positions(symbol)")
    cursor.execute("CREATE INDEX idx_signals_symbol_timeframe ON signals(symbol, timeframe, timestamp DESC)")

    conn.commit()
    conn.close()

    yield db_path

    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def seeded_db(temp_db):
    """Seed database with realistic test data."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO signals (id, symbol, timeframe, timestamp, direction, confidence, created_at)
        VALUES
            (1, 'BTCUSDT', '1h', 1720252800, 'long', 85, '2026-07-06T08:00:00'),
            (2, 'ETHUSDT', '4h', 1720249200, 'short', 75, '2026-07-05T10:00:00'),
            (3, 'SOLUSDT', '1h', 1720180800, 'long', 90, '2026-07-04T14:00:00')
    """)

    cursor.execute("""
        INSERT INTO paper_positions
        (id, symbol, direction, entry_price, current_price, size_usdt, qty, stop_loss, take_profit,
         signal_id, status, realized_pnl, opened_at, closed_at, confidence, regime, timeframe)
        VALUES
            (1, 'BTCUSDT', 'LONG', 50000.0, 51000.0, 1000.0, 0.02, 49000.0, 52000.0,
             1, 'OPEN', 0.0, '2026-07-06T08:00:00', NULL, 85, 'TRENDING', '1h'),

            (2, 'ETHUSDT', 'SHORT', 3000.0, 2950.0, 500.0, 0.16, 3050.0, 2900.0,
             2, 'TP_HIT', 50.0, '2026-07-05T10:00:00', '2026-07-06T10:00:00', 75, 'RANGING', '4h'),

            (3, 'BTCUSDT', 'SHORT', 51000.0, 50500.0, 800.0, 0.016, 51500.0, 50000.0,
             NULL, 'SL_HIT', -50.0, '2026-07-04T14:00:00', '2026-07-05T16:00:00', NULL, NULL, NULL),

            (4, 'SOLUSDT', 'LONG', 150.0, 155.0, 300.0, 2.0, 145.0, 160.0,
             3, 'TP_HIT', 30.0, '2026-07-04T14:00:00', '2026-07-05T18:00:00', 90, 'TRENDING', '1h'),

            (5, 'ETHUSDT', 'LONG', 2900.0, 2920.0, 600.0, 0.2, 2850.0, 2950.0,
             NULL, 'OPEN', 0.0, '2026-07-06T12:00:00', NULL, NULL, NULL, NULL),

            (6, 'BTCUSDT', 'LONG', 49500.0, 50000.0, 1200.0, 0.024, 48500.0, 51000.0,
             NULL, 'TP_HIT', 120.0, '2026-07-03T08:00:00', '2026-07-04T08:00:00', NULL, NULL, NULL)
    """)

    cursor.execute("""
        INSERT INTO paper_account (id, balance, equity, margin_used, unrealized_pnl)
        VALUES (1, 10000.0, 10150.0, 1900.0, 150.0)
    """)

    conn.commit()
    conn.close()

    return temp_db


@pytest.fixture
def client(seeded_db):
    """Test client with real service using seeded database."""
    test_app = FastAPI()
    test_app.include_router(explorer_router)

    def get_test_service():
        trade_repo = TradeRepository(db_path=seeded_db)
        signal_repo = SignalRepository(db_path=seeded_db)
        equity_repo = EquityRepository(db_path=seeded_db)
        return ExplorerQueryService(trade_repo, signal_repo, equity_repo)

    test_app.dependency_overrides[get_explorer_service] = get_test_service
    client = TestClient(test_app)
    yield client
    test_app.dependency_overrides.clear()


class TestTradesEndpointIntegration:
    """Integration tests for GET /api/v1/explorer/trades."""

    def test_get_all_trades_default(self, client):
        """Should return all trades with default pagination."""
        response = client.get("/api/v1/explorer/trades")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 6
        assert data["limit"] == 100
        assert data["offset"] == 0
        assert len(data["trades"]) == 6

        # Default sort is opened_at DESC, so ID 5 (2026-07-06T12:00:00) comes first
        assert data["trades"][0]["id"] == 5
        assert data["trades"][0]["symbol"] == "ETHUSDT"
        assert data["trades"][0]["status"] == "OPEN"

    def test_pagination_works(self, client):
        """Should paginate correctly."""
        response = client.get("/api/v1/explorer/trades?limit=2&offset=0")
        assert response.status_code == 200
        page1 = response.json()
        assert page1["total"] == 6
        assert page1["limit"] == 2
        assert page1["offset"] == 0
        assert len(page1["trades"]) == 2

        response = client.get("/api/v1/explorer/trades?limit=2&offset=2")
        assert response.status_code == 200
        page2 = response.json()
        assert page2["total"] == 6
        assert page2["offset"] == 2
        assert len(page2["trades"]) == 2

        assert page1["trades"][0]["id"] != page2["trades"][0]["id"]

    def test_filter_by_status(self, client):
        """Should filter by status."""
        response = client.get("/api/v1/explorer/trades?status=OPEN")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(t["status"] == "OPEN" for t in data["trades"])

    def test_filter_by_symbol(self, client):
        """Should filter by symbol."""
        response = client.get("/api/v1/explorer/trades?symbol=BTCUSDT")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert all(t["symbol"] == "BTCUSDT" for t in data["trades"])

    def test_filter_by_direction(self, client):
        """Should filter by direction."""
        response = client.get("/api/v1/explorer/trades?direction=LONG")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 4
        assert all(t["direction"] == "LONG" for t in data["trades"])

    def test_multiple_filters(self, client):
        """Should apply multiple filters."""
        response = client.get("/api/v1/explorer/trades?symbol=BTCUSDT&status=OPEN")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["trades"][0]["symbol"] == "BTCUSDT"
        assert data["trades"][0]["status"] == "OPEN"

    def test_sorting_by_realized_pnl_asc(self, client):
        """Should sort by realized_pnl ascending."""
        response = client.get("/api/v1/explorer/trades?sort_by=realized_pnl&sort_order=ASC")

        assert response.status_code == 200
        data = response.json()
        pnls = [t["realized_pnl"] for t in data["trades"]]
        assert pnls == sorted(pnls)
        assert data["trades"][0]["realized_pnl"] == -50.0

    def test_sorting_by_opened_at_desc(self, client):
        """Should sort by opened_at descending."""
        response = client.get("/api/v1/explorer/trades?sort_by=opened_at&sort_order=DESC")

        assert response.status_code == 200
        data = response.json()
        assert data["trades"][0]["opened_at"] > data["trades"][-1]["opened_at"]

    def test_limit_validation(self, client):
        """Should reject invalid limit."""
        response = client.get("/api/v1/explorer/trades?limit=2000")
        assert response.status_code == 422

        response = client.get("/api/v1/explorer/trades?limit=0")
        assert response.status_code == 422

    def test_offset_validation(self, client):
        """Should reject negative offset."""
        response = client.get("/api/v1/explorer/trades?offset=-1")
        assert response.status_code == 422

    def test_invalid_parameter_types(self, client):
        """Should reject invalid parameter types."""
        response = client.get("/api/v1/explorer/trades?limit=abc")
        assert response.status_code == 422

        response = client.get("/api/v1/explorer/trades?offset=xyz")
        assert response.status_code == 422


class TestTradeDetailEndpointIntegration:
    """Integration tests for GET /api/v1/explorer/trades/{id}."""

    def test_get_trade_with_signal(self, client):
        """Should return trade with linked signal."""
        response = client.get("/api/v1/explorer/trades/1")

        assert response.status_code == 200
        data = response.json()
        assert data["trade"]["id"] == 1
        assert data["trade"]["symbol"] == "BTCUSDT"
        assert data["trade"]["signal_id"] == 1
        assert data["signal"] is not None
        assert data["signal"]["id"] == 1
        assert data["signal"]["confidence"] == 85
        assert data["signal"]["direction"] == "long"

    def test_get_trade_without_signal(self, client):
        """Should return trade without signal."""
        response = client.get("/api/v1/explorer/trades/3")

        assert response.status_code == 200
        data = response.json()
        assert data["trade"]["id"] == 3
        assert data["trade"]["signal_id"] is None
        assert data["signal"] is None

    def test_trade_not_found(self, client):
        """Should return 404 for non-existent trade."""
        response = client.get("/api/v1/explorer/trades/999")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_invalid_trade_id(self, client):
        """Should return 422 for invalid ID type."""
        response = client.get("/api/v1/explorer/trades/invalid")
        assert response.status_code == 422


class TestSummaryEndpointIntegration:
    """Integration tests for GET /api/v1/explorer/summary."""

    def test_get_summary_calculates_correctly(self, client):
        """Should calculate analytics from real data."""
        response = client.get("/api/v1/explorer/summary")

        assert response.status_code == 200
        data = response.json()

        assert data["total_trades"] == 6
        assert data["open_count"] == 2
        assert data["closed_count"] == 4
        assert data["long_count"] == 4
        assert data["short_count"] == 2

        assert data["winning_trades"] == 3
        assert data["losing_trades"] == 1
        assert data["win_rate"] == 0.75

        assert data["gross_profit"] == 200.0
        assert data["gross_loss"] == 50.0
        assert data["net_profit"] == 150.0

        assert data["largest_win"] == 120.0
        assert data["largest_loss"] == -50.0

    def test_summary_response_schema(self, client):
        """Should match OpenAPI schema."""
        response = client.get("/api/v1/explorer/summary")

        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "total_trades", "winning_trades", "losing_trades", "win_rate",
            "gross_profit", "gross_loss", "net_profit", "average_profit", "average_loss",
            "average_hold_duration_seconds", "average_trade_duration_seconds",
            "largest_win", "largest_loss", "long_count", "short_count",
            "open_count", "closed_count"
        ]

        for field in required_fields:
            assert field in data
            assert isinstance(data[field], (int, float))


class TestMetadataEndpointIntegration:
    """Integration tests for GET /api/v1/explorer/metadata."""

    def test_get_metadata(self, client):
        """Should return available filter values."""
        response = client.get("/api/v1/explorer/metadata")

        assert response.status_code == 200
        data = response.json()

        assert set(data["symbols"]) == {"BTCUSDT", "ETHUSDT", "SOLUSDT"}
        assert set(data["directions"]) == {"LONG", "SHORT"}
        assert set(data["statuses"]) == {"OPEN", "TP_HIT", "SL_HIT"}

    def test_metadata_schema(self, client):
        """Should match OpenAPI schema."""
        response = client.get("/api/v1/explorer/metadata")

        assert response.status_code == 200
        data = response.json()

        assert "symbols" in data
        assert "directions" in data
        assert "statuses" in data
        assert isinstance(data["symbols"], list)
        assert isinstance(data["directions"], list)
        assert isinstance(data["statuses"], list)


class TestEmptyDatabaseScenarios:
    """Tests with empty database."""

    def test_empty_trades_list(self, temp_db):
        """Should handle empty database gracefully."""
        test_app = FastAPI()
        test_app.include_router(explorer_router)

        def get_empty_service():
            trade_repo = TradeRepository(db_path=temp_db)
            signal_repo = SignalRepository(db_path=temp_db)
            equity_repo = EquityRepository(db_path=temp_db)
            return ExplorerQueryService(trade_repo, signal_repo, equity_repo)

        test_app.dependency_overrides[get_explorer_service] = get_empty_service
        client = TestClient(test_app)

        response = client.get("/api/v1/explorer/trades")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["trades"]) == 0

    def test_empty_summary(self, temp_db):
        """Should return zero values for empty dataset."""
        test_app = FastAPI()
        test_app.include_router(explorer_router)

        def get_empty_service():
            trade_repo = TradeRepository(db_path=temp_db)
            signal_repo = SignalRepository(db_path=temp_db)
            equity_repo = EquityRepository(db_path=temp_db)
            return ExplorerQueryService(trade_repo, signal_repo, equity_repo)

        test_app.dependency_overrides[get_explorer_service] = get_empty_service
        client = TestClient(test_app)

        response = client.get("/api/v1/explorer/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_trades"] == 0
        assert data["win_rate"] == 0.0
        assert data["net_profit"] == 0.0

    def test_empty_metadata(self, temp_db):
        """Should return empty sets for empty dataset."""
        test_app = FastAPI()
        test_app.include_router(explorer_router)

        def get_empty_service():
            trade_repo = TradeRepository(db_path=temp_db)
            signal_repo = SignalRepository(db_path=temp_db)
            equity_repo = EquityRepository(db_path=temp_db)
            return ExplorerQueryService(trade_repo, signal_repo, equity_repo)

        test_app.dependency_overrides[get_explorer_service] = get_empty_service
        client = TestClient(test_app)

        response = client.get("/api/v1/explorer/metadata")
        assert response.status_code == 200
        data = response.json()
        assert data["symbols"] == []
        assert data["directions"] == []
        assert data["statuses"] == []


class TestDatabaseErrorScenarios:
    """Test database error handling."""

    def test_invalid_database_path(self):
        """Should handle database connection errors."""
        test_app = FastAPI()
        test_app.include_router(explorer_router)

        def get_broken_service():
            trade_repo = TradeRepository(db_path="/nonexistent/path/db.db")
            signal_repo = SignalRepository(db_path="/nonexistent/path/db.db")
            equity_repo = EquityRepository(db_path="/nonexistent/path/db.db")
            return ExplorerQueryService(trade_repo, signal_repo, equity_repo)

        test_app.dependency_overrides[get_explorer_service] = get_broken_service
        client = TestClient(test_app)

        with pytest.raises(Exception):
            client.get("/api/v1/explorer/trades")


class TestEndToEndWorkflows:
    """End-to-end workflow tests."""

    def test_browse_filter_detail_workflow(self, client):
        """Should support browse → filter → detail workflow."""
        metadata_response = client.get("/api/v1/explorer/metadata")
        assert metadata_response.status_code == 200
        symbols = metadata_response.json()["symbols"]
        assert "BTCUSDT" in symbols

        trades_response = client.get("/api/v1/explorer/trades?symbol=BTCUSDT&status=OPEN")
        assert trades_response.status_code == 200
        trades = trades_response.json()["trades"]
        assert len(trades) == 1
        trade_id = trades[0]["id"]

        detail_response = client.get(f"/api/v1/explorer/trades/{trade_id}")
        assert detail_response.status_code == 200
        assert detail_response.json()["trade"]["id"] == trade_id

    def test_pagination_through_all_trades(self, client):
        """Should paginate through entire dataset."""
        all_trades = []
        offset = 0
        limit = 2

        while True:
            response = client.get(f"/api/v1/explorer/trades?limit={limit}&offset={offset}")
            assert response.status_code == 200
            data = response.json()

            if not data["trades"]:
                break

            all_trades.extend(data["trades"])
            offset += limit

            if len(all_trades) >= data["total"]:
                break

        assert len(all_trades) == 6
        trade_ids = [t["id"] for t in all_trades]
        assert len(trade_ids) == len(set(trade_ids))
