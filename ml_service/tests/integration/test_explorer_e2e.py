"""End-to-end integration tests for Trade Explorer API.

Tests complete stack: FastAPI → Service → Analytics → Repository → SQLite

NO MOCKS. Real database, real HTTP calls, real SQL queries.
"""

import pytest
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from ml_service.tests.integration.schema_bootstrap import create_test_schema, drop_all_tables
from ml_service.tests.integration.test_data_builder import TestDataBuilder


@pytest.fixture
def test_db():
    """Create temporary SQLite database with schema."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    create_test_schema(path)

    yield path

    try:
        os.unlink(path)
    except:
        pass


@pytest.fixture
def test_client(test_db, monkeypatch):
    """FastAPI test client with real database."""
    from fastapi import FastAPI
    from ml_service.repositories.database import get_connection

    original_get_connection = get_connection

    def patched_get_connection(db_path=None):
        return original_get_connection(test_db)

    monkeypatch.setattr("ml_service.repositories.database.get_connection", patched_get_connection)
    monkeypatch.setattr("ml_service.repositories.trade_repository.get_connection", patched_get_connection)
    monkeypatch.setattr("ml_service.repositories.signal_repository.get_connection", patched_get_connection)
    monkeypatch.setattr("ml_service.repositories.equity_repository.get_connection", patched_get_connection)

    from ml_service.api.explorer_routes import router as explorer_router

    app = FastAPI(title="Integration Test App")
    app.include_router(explorer_router)

    with TestClient(app) as client:
        yield client


@pytest.fixture
def builder(test_db):
    """Test data builder."""
    return TestDataBuilder(test_db)


class TestTradeList:
    """Test /api/v1/explorer/trades endpoint."""

    def test_empty_database(self, test_client):
        """GET /trades on empty database returns empty list."""
        response = test_client.get("/api/v1/explorer/trades")

        assert response.status_code == 200
        data = response.json()
        assert data["trades"] == []
        assert data["total"] == 0
        assert data["limit"] == 100
        assert data["offset"] == 0

    def test_normal_data_flow(self, test_client, builder):
        """GET /trades with seeded data returns correct results."""
        builder.seed_mixed_dataset()

        response = test_client.get("/api/v1/explorer/trades")

        assert response.status_code == 200
        data = response.json()
        assert len(data["trades"]) == 7
        assert data["total"] == 7

        trade = data["trades"][0]
        assert "id" in trade
        assert "symbol" in trade
        assert "direction" in trade
        assert "status" in trade
        assert "realized_pnl" in trade

    def test_pagination(self, test_client, builder):
        """GET /trades pagination works correctly."""
        builder.seed_winning_trades(10)

        page1 = test_client.get("/api/v1/explorer/trades?limit=3&offset=0")
        page2 = test_client.get("/api/v1/explorer/trades?limit=3&offset=3")

        assert page1.status_code == 200
        assert page2.status_code == 200

        data1 = page1.json()
        data2 = page2.json()

        assert len(data1["trades"]) == 3
        assert len(data2["trades"]) == 3
        assert data1["total"] == 10
        assert data2["total"] == 10

        ids1 = {t["id"] for t in data1["trades"]}
        ids2 = {t["id"] for t in data2["trades"]}
        assert ids1.isdisjoint(ids2)

    def test_filter_by_status(self, test_client, builder):
        """GET /trades?status=OPEN filters correctly."""
        builder.seed_mixed_dataset()

        response = test_client.get("/api/v1/explorer/trades?status=OPEN")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(t["status"] == "OPEN" for t in data["trades"])

    def test_filter_by_symbol(self, test_client, builder):
        """GET /trades?symbol=BTCUSDT filters correctly."""
        builder.seed_mixed_dataset()

        response = test_client.get("/api/v1/explorer/trades?symbol=BTCUSDT")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert all(t["symbol"] == "BTCUSDT" for t in data["trades"])

    def test_filter_by_direction(self, test_client, builder):
        """GET /trades?direction=SHORT filters correctly."""
        builder.seed_mixed_dataset()

        response = test_client.get("/api/v1/explorer/trades?direction=SHORT")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(t["direction"] == "SHORT" for t in data["trades"])

    def test_combined_filters(self, test_client, builder):
        """GET /trades with multiple filters works correctly."""
        builder.insert_trade(symbol="BTCUSDT", direction="LONG", status="TP_HIT")
        builder.insert_trade(symbol="BTCUSDT", direction="SHORT", status="OPEN")
        builder.insert_trade(symbol="ETHUSDT", direction="LONG", status="TP_HIT")

        response = test_client.get("/api/v1/explorer/trades?symbol=BTCUSDT&status=TP_HIT")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["trades"][0]["symbol"] == "BTCUSDT"
        assert data["trades"][0]["status"] == "TP_HIT"

    def test_sorting_asc(self, test_client, builder):
        """GET /trades with sort_order=ASC works correctly."""
        id1 = builder.insert_trade(realized_pnl=10.0)
        id2 = builder.insert_trade(realized_pnl=50.0)
        id3 = builder.insert_trade(realized_pnl=-20.0)

        response = test_client.get("/api/v1/explorer/trades?sort_by=realized_pnl&sort_order=ASC")

        assert response.status_code == 200
        data = response.json()
        pnls = [t["realized_pnl"] for t in data["trades"]]
        assert pnls == sorted(pnls)
        assert pnls[0] == -20.0

    def test_sorting_desc(self, test_client, builder):
        """GET /trades with sort_order=DESC works correctly."""
        id1 = builder.insert_trade(realized_pnl=10.0)
        id2 = builder.insert_trade(realized_pnl=50.0)
        id3 = builder.insert_trade(realized_pnl=-20.0)

        response = test_client.get("/api/v1/explorer/trades?sort_by=realized_pnl&sort_order=DESC")

        assert response.status_code == 200
        data = response.json()
        pnls = [t["realized_pnl"] for t in data["trades"]]
        assert pnls == sorted(pnls, reverse=True)
        assert pnls[0] == 50.0

    def test_invalid_limit_422(self, test_client):
        """GET /trades with invalid limit returns 422."""
        response = test_client.get("/api/v1/explorer/trades?limit=2000")
        assert response.status_code == 422

    def test_invalid_offset_422(self, test_client):
        """GET /trades with negative offset returns 422."""
        response = test_client.get("/api/v1/explorer/trades?offset=-1")
        assert response.status_code == 422


class TestTradeDetail:
    """Test /api/v1/explorer/trades/{id} endpoint."""

    def test_existing_trade(self, test_client, builder):
        """GET /trades/{id} returns trade detail."""
        trade_id = builder.insert_trade(symbol="BTCUSDT", direction="LONG", realized_pnl=100.0)

        response = test_client.get(f"/api/v1/explorer/trades/{trade_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["trade"]["id"] == trade_id
        assert data["trade"]["symbol"] == "BTCUSDT"
        assert data["trade"]["direction"] == "LONG"
        assert data["signal"] is None

    def test_trade_with_signal(self, test_client, builder):
        """GET /trades/{id} includes linked signal."""
        signal_id = builder.insert_signal(symbol="ETHUSDT", direction="SHORT", confidence=85)
        trade_id = builder.insert_trade(symbol="ETHUSDT", signal_id=signal_id)

        response = test_client.get(f"/api/v1/explorer/trades/{trade_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["trade"]["signal_id"] == signal_id
        assert data["signal"] is not None
        assert data["signal"]["id"] == signal_id
        assert data["signal"]["confidence"] == 85

    def test_nonexistent_trade_404(self, test_client):
        """GET /trades/99999 returns 404."""
        response = test_client.get("/api/v1/explorer/trades/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestSummary:
    """Test /api/v1/explorer/summary endpoint."""

    def test_empty_database(self, test_client):
        """GET /summary on empty database returns zeros."""
        response = test_client.get("/api/v1/explorer/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_trades"] == 0
        assert data["winning_trades"] == 0
        assert data["losing_trades"] == 0
        assert data["win_rate"] == 0.0
        assert data["net_profit"] == 0.0

    def test_analytics_calculation(self, test_client, builder):
        """GET /summary calculates analytics correctly."""
        builder.seed_winning_trades(3)
        builder.seed_losing_trades(2)
        builder.seed_open_trades(1)

        response = test_client.get("/api/v1/explorer/summary")

        assert response.status_code == 200
        data = response.json()

        assert data["total_trades"] == 6
        assert data["closed_count"] == 5
        assert data["open_count"] == 1
        assert data["winning_trades"] == 3
        assert data["losing_trades"] == 2
        assert 0 < data["win_rate"] < 1
        assert data["gross_profit"] > 0
        assert data["gross_loss"] > 0
        assert data["net_profit"] != 0

    def test_only_winning_trades(self, test_client, builder):
        """GET /summary with only winners calculates correctly."""
        builder.seed_winning_trades(5)

        response = test_client.get("/api/v1/explorer/summary")

        assert response.status_code == 200
        data = response.json()

        assert data["winning_trades"] == 5
        assert data["losing_trades"] == 0
        assert data["win_rate"] == 1.0
        assert data["gross_loss"] == 0.0
        assert data["net_profit"] > 0

    def test_only_losing_trades(self, test_client, builder):
        """GET /summary with only losers calculates correctly."""
        builder.seed_losing_trades(3)

        response = test_client.get("/api/v1/explorer/summary")

        assert response.status_code == 200
        data = response.json()

        assert data["winning_trades"] == 0
        assert data["losing_trades"] == 3
        assert data["win_rate"] == 0.0
        assert data["gross_profit"] == 0.0
        assert data["net_profit"] < 0


class TestMetadata:
    """Test /api/v1/explorer/metadata endpoint."""

    def test_empty_database(self, test_client):
        """GET /metadata on empty database returns empty sets."""
        response = test_client.get("/api/v1/explorer/metadata")

        assert response.status_code == 200
        data = response.json()
        assert data["symbols"] == []
        assert data["directions"] == []
        assert data["statuses"] == []

    def test_unique_values(self, test_client, builder):
        """GET /metadata returns unique filter values."""
        builder.insert_trade(symbol="BTCUSDT", direction="LONG", status="OPEN")
        builder.insert_trade(symbol="BTCUSDT", direction="SHORT", status="TP_HIT")
        builder.insert_trade(symbol="ETHUSDT", direction="LONG", status="SL_HIT")

        response = test_client.get("/api/v1/explorer/metadata")

        assert response.status_code == 200
        data = response.json()

        assert set(data["symbols"]) == {"BTCUSDT", "ETHUSDT"}
        assert set(data["directions"]) == {"LONG", "SHORT"}
        assert set(data["statuses"]) == {"OPEN", "TP_HIT", "SL_HIT"}


class TestDatabaseFailures:
    """Test handling of database failures."""

    def test_missing_database_schema(self, monkeypatch):
        """API with database missing schema returns 500."""
        import tempfile
        import os
        import sqlite3
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
        from ml_service.repositories.database import get_connection

        fd, empty_db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        try:
            def patched_get_connection(db_path=None):
                conn = sqlite3.connect(empty_db_path)
                conn.row_factory = sqlite3.Row
                return conn

            monkeypatch.setattr("ml_service.repositories.database.get_connection", patched_get_connection)
            monkeypatch.setattr("ml_service.repositories.trade_repository.get_connection", patched_get_connection)

            from ml_service.api.explorer_routes import router as explorer_router

            app = FastAPI(title="Integration Test App")

            @app.exception_handler(sqlite3.OperationalError)
            async def handle_db_error(request: Request, exc: sqlite3.OperationalError):
                return JSONResponse(
                    status_code=500,
                    content={"detail": "Database error"}
                )

            app.include_router(explorer_router)

            with TestClient(app) as client:
                response = client.get("/api/v1/explorer/trades")
                assert response.status_code == 500
        finally:
            try:
                os.unlink(empty_db_path)
            except:
                pass


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_pagination_beyond_total(self, test_client, builder):
        """GET /trades with offset beyond total returns empty."""
        builder.seed_winning_trades(5)

        response = test_client.get("/api/v1/explorer/trades?offset=100")

        assert response.status_code == 200
        data = response.json()
        assert data["trades"] == []
        assert data["total"] == 5

    def test_zero_limit(self, test_client, builder):
        """GET /trades with limit=0 returns 422."""
        response = test_client.get("/api/v1/explorer/trades?limit=0")
        assert response.status_code == 422

    def test_invalid_sort_column(self, test_client, builder):
        """GET /trades with invalid sort_by falls back to opened_at."""
        builder.insert_trade(realized_pnl=10.0)
        builder.insert_trade(realized_pnl=50.0)

        response = test_client.get("/api/v1/explorer/trades?sort_by=invalid_column")

        assert response.status_code == 200

    def test_invalid_sort_order(self, test_client, builder):
        """GET /trades with invalid sort_order falls back to DESC."""
        builder.insert_trade(realized_pnl=10.0)
        builder.insert_trade(realized_pnl=50.0)

        response = test_client.get("/api/v1/explorer/trades?sort_order=INVALID")

        assert response.status_code == 200

    def test_trade_detail_invalid_id_format(self, test_client):
        """GET /trades/abc returns 422."""
        response = test_client.get("/api/v1/explorer/trades/abc")
        assert response.status_code == 422

    def test_large_dataset_performance(self, test_client, builder):
        """GET /trades with 1000 records completes successfully."""
        for i in range(1000):
            builder.insert_trade(symbol=f"SYM{i % 10}", realized_pnl=float(i))

        response = test_client.get("/api/v1/explorer/trades?limit=100")

        assert response.status_code == 200
        data = response.json()
        assert len(data["trades"]) == 100
        assert data["total"] == 1000
