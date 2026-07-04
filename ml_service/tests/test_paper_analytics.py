"""Unit tests for Phase 3: paper equity history + analytics + trades endpoints."""

import sys
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest

# Ensure ml_service root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import ml_service.trading.mode_manager as mm
import ml_service.trading.paper_broker as pb
from ml_service.trading.mode_manager import set_trading_mode
from ml_service.trading.paper_broker import (
    open_paper_position,
    close_paper_position,
    capture_equity_snapshot,
    get_equity_history,
    compute_paper_analytics,
    get_paper_trades,
)


@pytest.fixture(autouse=True)
def db_path(monkeypatch):
    """Each test gets its own temp DB; module-level _DB_PATH is saved & restored."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    test_db = Path(tmp.name)
    saved_mm = mm._DB_PATH
    saved_pb = pb._DB_PATH
    monkeypatch.setattr(mm, "_DB_PATH", test_db)
    monkeypatch.setattr(pb, "_DB_PATH", test_db)
    yield test_db
    mm._DB_PATH = saved_mm
    pb._DB_PATH = saved_pb
    if test_db.exists():
        test_db.unlink()


def _reset_db(db_path: Path):
    """Wipe and recreate all tables so each test starts clean."""
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS trading_system_state (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            trading_mode TEXT NOT NULL DEFAULT 'OFF',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO trading_system_state (id, trading_mode) VALUES (1, 'OFF');

        CREATE TABLE IF NOT EXISTS paper_account (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            balance REAL NOT NULL DEFAULT 10000.0,
            equity REAL NOT NULL DEFAULT 10000.0,
            unrealized_pnl REAL NOT NULL DEFAULT 0.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO paper_account (id, balance, equity, unrealized_pnl)
        VALUES (1, 10000.0, 10000.0, 0.0);

        CREATE TABLE IF NOT EXISTS paper_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL NOT NULL,
            current_price REAL,
            size_usdt REAL NOT NULL,
            qty REAL NOT NULL,
            stop_loss REAL,
            take_profit REAL,
            signal_id INTEGER,
            status TEXT NOT NULL DEFAULT 'OPEN',
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
            execution_policy TEXT DEFAULT 'FIXED_SL'
        );

        CREATE TABLE IF NOT EXISTS paper_equity_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equity REAL NOT NULL,
            balance REAL NOT NULL,
            unrealized_pnl REAL NOT NULL,
            snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_paper_equity_snapshot_time
        ON paper_equity_history(snapshot_time);
    """)
    conn.commit()
    conn.close()


def _make_signal(symbol="BTCUSDT", direction="long", price=100.0):
    return {
        "symbol": symbol, "direction": direction, "price": price,
        "take_profit": price * 1.1, "stop_loss": price * 0.9,
        "confidence": 70, "timeframe": "1h",
    }


# ─── Equity History ─────────────────────────────────────────────────────

def test_capture_equity_snapshot_creates_row(db_path):
    _reset_db(db_path)
    ok = capture_equity_snapshot()
    assert ok is True
    history = get_equity_history()
    assert len(history) == 1
    assert history[0]["equity"] == 10000.0
    print("✓ capture_equity_snapshot inserts a row")


def test_equity_history_empty_when_no_snapshots(db_path):
    _reset_db(db_path)
    history = get_equity_history()
    assert history == []
    print("✓ Empty equity history returns []")


def test_equity_history_multiple_snapshots_ordered(db_path):
    _reset_db(db_path)
    capture_equity_snapshot()
    capture_equity_snapshot()
    capture_equity_snapshot()
    history = get_equity_history()
    assert len(history) == 3
    # Ascending order by snapshot_time
    assert history[0]["timestamp"] <= history[1]["timestamp"] <= history[2]["timestamp"]
    print("✓ Multiple snapshots returned in ascending order")


def test_equity_history_reflects_balance_after_trade(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    r = open_paper_position(_make_signal(direction="long", price=100.0))
    close_paper_position(r["position_id"], status="TP_HIT", close_price=110.0)  # +10
    capture_equity_snapshot()
    history = get_equity_history()
    assert len(history) == 1
    assert abs(history[0]["balance"] - 10010.0) < 0.01
    print(f"✓ Snapshot balance reflects realized PnL: {history[0]['balance']}")


def test_equity_history_range_filter(db_path):
    _reset_db(db_path)
    # Insert an old snapshot manually
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO paper_equity_history (equity, balance, unrealized_pnl, snapshot_time) "
        "VALUES (?, ?, ?, ?)",
        (9000.0, 9000.0, 0.0,
         (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.execute(
        "INSERT INTO paper_equity_history (equity, balance, unrealized_pnl, snapshot_time) "
        "VALUES (?, ?, ?, ?)",
        (10000.0, 10000.0, 0.0,
         datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()

    # range_hours=1 (last hour) → only the recent snapshot
    recent = get_equity_history(range_hours=1)
    assert len(recent) == 1
    assert recent[0]["equity"] == 10000.0
    # No filter → both
    all_hist = get_equity_history()
    assert len(all_hist) == 2
    print("✓ Equity history range filter works")


# ─── Analytics ───────────────────────────────────────────────────────────

def test_analytics_empty_when_no_trades(db_path):
    _reset_db(db_path)
    a = compute_paper_analytics()
    assert a["total_trades"] == 0
    assert a["win_rate"] == 0.0
    assert a["profit_factor"] == 0.0
    print("✓ Empty analytics returns zeros")


def test_analytics_after_one_win(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    r = open_paper_position(_make_signal(direction="long", price=100.0))
    close_paper_position(r["position_id"], status="TP_HIT", close_price=110.0)
    a = compute_paper_analytics()
    assert a["total_trades"] == 1
    assert a["win_rate"] == 100.0
    assert a["total_realized_pnl"] > 0
    assert a["profit_factor"] > 0
    print(f"✓ Analytics after 1 win: win_rate={a['win_rate']}%")


def test_analytics_mixed_win_loss(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    r1 = open_paper_position(_make_signal(symbol="BTCUSDT", direction="long", price=100.0))
    close_paper_position(r1["position_id"], status="TP_HIT", close_price=110.0)  # +10
    r2 = open_paper_position(_make_signal(symbol="ETHUSDT", direction="long", price=100.0))
    close_paper_position(r2["position_id"], status="SL_HIT", close_price=90.0)  # -10
    a = compute_paper_analytics()
    assert a["total_trades"] == 2
    assert a["win_rate"] == 50.0
    assert abs(a["total_realized_pnl"] - 0.0) < 0.01  # +10 -10 = 0
    print(f"✓ Mixed 1W/1L: win_rate={a['win_rate']}% pnl={a['total_realized_pnl']}")


def test_analytics_profit_factor_inf_when_no_losses(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    r = open_paper_position(_make_signal(direction="long", price=100.0))
    close_paper_position(r["position_id"], status="TP_HIT", close_price=110.0)
    a = compute_paper_analytics()
    assert a["profit_factor"] == float("inf")
    print("✓ Profit factor = inf when no losses")


def test_analytics_open_positions_counted(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    open_paper_position(_make_signal(direction="long", price=100.0))
    open_paper_position(_make_signal(symbol="ETHUSDT", direction="short", price=200.0))
    a = compute_paper_analytics()
    assert a["open_positions"] == 2
    assert a["closed_positions"] == 0
    print(f"✓ Analytics counts 2 open positions")


def test_analytics_expectancy_is_avg_pnl(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    r = open_paper_position(_make_signal(direction="long", price=100.0))
    close_paper_position(r["position_id"], status="TP_HIT", close_price=110.0)  # +10
    a = compute_paper_analytics()
    assert abs(a["expectancy"] - a["avg_trade_pnl"]) < 0.01
    print(f"✓ Expectancy == avg_trade_pnl: {a['expectancy']}")


# ─── Trades endpoint ─────────────────────────────────────────────────────

def test_paper_trades_empty_when_no_closed(db_path):
    _reset_db(db_path)
    trades = get_paper_trades()
    assert trades == []
    print("✓ get_paper_trades empty when no closed positions")


def test_paper_trades_returns_closed_only(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    open_paper_position(_make_signal(direction="long", price=100.0))  # stays OPEN
    r = open_paper_position(_make_signal(symbol="ETHUSDT", direction="long", price=100.0))
    close_paper_position(r["position_id"], status="TP_HIT", close_price=110.0)  # closed

    trades = get_paper_trades()
    assert len(trades) == 1
    assert trades[0]["symbol"] == "ETHUSDT"
    print("✓ get_paper_trades returns only closed positions")


def test_paper_trades_shape(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    r = open_paper_position(_make_signal(direction="long", price=100.0))
    close_paper_position(r["position_id"], status="TP_HIT", close_price=110.0)
    trades = get_paper_trades()
    t = trades[0]
    assert "symbol" in t
    assert "direction" in t
    assert "entry_price" in t
    assert "exit_price" in t
    assert "realized_pnl" in t
    assert "opened_at" in t
    assert "closed_at" in t
    assert "status" in t
    print("✓ Paper trade has correct shape")


def test_paper_trades_newest_first(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    r1 = open_paper_position(_make_signal(symbol="BTCUSDT", direction="long", price=100.0))
    close_paper_position(r1["position_id"], status="TP_HIT", close_price=110.0)
    r2 = open_paper_position(_make_signal(symbol="ETHUSDT", direction="long", price=100.0))
    close_paper_position(r2["position_id"], status="TP_HIT", close_price=110.0)
    trades = get_paper_trades()
    assert len(trades) == 2
    # Newest (ETH, closed later) should be first
    assert trades[0]["symbol"] == "ETHUSDT"
    print("✓ Paper trades ordered newest first")


def test_paper_trades_limit(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]:
        r = open_paper_position(_make_signal(symbol=sym, direction="long", price=100.0))
        close_paper_position(r["position_id"], status="TP_HIT", close_price=110.0)
    trades = get_paper_trades(limit=2)
    assert len(trades) == 2
    print("✓ Paper trades respects limit")


# ─── Migration idempotency ───────────────────────────────────────────────

def test_migration_019_idempotent(db_path):
    """The paper_equity_history CREATE TABLE is idempotent (IF NOT EXISTS)."""
    _reset_db(db_path)
    migration_sql = (Path(__file__).parent.parent / "migrations" / "019_paper_equity_history.sql").read_text()

    # Apply twice to the test DB — both must succeed
    conn = sqlite3.connect(str(db_path))
    for i in range(2):
        for statement in migration_sql.split(";"):
            statement = statement.strip()
            if statement and not statement.startswith("--"):
                try:
                    conn.execute(statement)
                except sqlite3.OperationalError as e:
                    if "already exists" not in str(e).lower():
                        raise
    conn.commit()

    # Verify the table + index exist
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='paper_equity_history'"
    ).fetchall()
    indexes = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_paper_equity_snapshot_time'"
    ).fetchall()
    conn.close()

    assert len(tables) == 1
    assert len(indexes) == 1
    print("✓ Migration 019 idempotent (table + index created)")
