"""Unit tests for ml_service.trading.paper_broker (Paper Broker Engine)."""

import sys
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest

# Ensure ml_service root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import trading.mode_manager as mm
import trading.paper_broker as pb
import trading.regime_execution_policy as rep
from ml_service.trading.mode_manager import set_trading_mode, get_trading_mode, VALID_MODES
from ml_service.trading.paper_broker import (
    STARTING_BALANCE,
    MAX_OPEN_POSITIONS,
    RISK_PER_TRADE_PCT,
    open_paper_position,
    close_paper_position,
    update_open_positions,
    calculate_equity,
    get_portfolio_summary,
    get_open_positions,
    get_closed_positions,
    get_account,
)


@pytest.fixture(autouse=True)
def db_path(monkeypatch):
    """Each test gets its own temp DB; module-level _DB_PATH is saved & restored."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    test_db = Path(tmp.name)
    saved_mm = mm._DB_PATH
    saved_pb = pb._DB_PATH
    saved_rep = rep._DB_PATH
    monkeypatch.setattr(mm, "_DB_PATH", test_db)
    monkeypatch.setattr(pb, "_DB_PATH", test_db)
    monkeypatch.setattr(rep, "_DB_PATH", test_db)
    yield test_db
    mm._DB_PATH = saved_mm
    pb._DB_PATH = saved_pb
    rep._DB_PATH = saved_rep
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
            skip_reason TEXT
        );

        CREATE TABLE IF NOT EXISTS regime_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            regime TEXT UNIQUE,
            is_active INTEGER NOT NULL DEFAULT 1,
            reason TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            direction TEXT NOT NULL,
            confidence INTEGER NOT NULL,
            features_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


def _make_signal(symbol="BTCUSDT", direction="long", price=100.0,
                 tp=None, sl=None):
    """Build a minimal signal dict mimicking generate_signal() output."""
    return {
        "symbol": symbol,
        "direction": direction,
        "price": price,
        "take_profit": tp,
        "stop_loss": sl,
        "confidence": 70,
        "timeframe": "1h",
    }


def _insert_open_position(db_path: Path, symbol, direction, entry_price,
                          qty=1.0, current_price=None, tp=None, sl=None,
                          opened_at=None):
    """Insert a raw OPEN position bypassing the open() logic."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """INSERT INTO paper_positions
           (symbol, direction, entry_price, current_price, size_usdt, qty,
            stop_loss, take_profit, status, realized_pnl, opened_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', 0.0, ?)""",
        (symbol, direction, entry_price, current_price or entry_price,
         qty * entry_price, qty, sl, tp,
         opened_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


# ─── 1. Account initialization ───────────────────────────────────────────

def test_account_default_balance(db_path):
    _reset_db(db_path)
    acct = get_account()
    assert acct["balance"] == STARTING_BALANCE
    assert acct["equity"] == STARTING_BALANCE
    print(f"✓ Account defaults to {STARTING_BALANCE} USDT")


def test_starting_balance_is_10000():
    assert STARTING_BALANCE == 10000.0
    print("✓ STARTING_BALANCE == 10000")


# ─── 2. Mode gating ──────────────────────────────────────────────────────

def test_open_refused_when_mode_off(db_path):
    _reset_db(db_path)
    set_trading_mode("OFF")
    result = open_paper_position(_make_signal(direction="long"))
    assert result is None
    assert len(get_open_positions()) == 0
    print("✓ open_paper_position refused when mode=OFF")


def test_open_refused_when_mode_live(db_path):
    _reset_db(db_path)
    set_trading_mode("LIVE")
    result = open_paper_position(_make_signal(direction="long"))
    assert result is None
    print("✓ open_paper_position refused when mode=LIVE")


def test_open_refused_when_mode_maintenance(db_path):
    _reset_db(db_path)
    set_trading_mode("MAINTENANCE")
    result = open_paper_position(_make_signal(direction="long"))
    assert result is None
    print("✓ open_paper_position refused when mode=MAINTENANCE")


# ─── 3. Neutral signal rejection ─────────────────────────────────────────

def test_neutral_signal_skipped(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    result = open_paper_position(_make_signal(direction="neutral"))
    assert result is None
    assert len(get_open_positions()) == 0
    print("✓ Neutral signal skipped")


# ─── 4. Successful open ──────────────────────────────────────────────────

def test_open_long_position(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    sig = _make_signal(symbol="BTCUSDT", direction="long", price=100.0,
                       tp=110.0, sl=90.0)
    result = open_paper_position(sig)
    assert result is not None
    assert result["symbol"] == "BTCUSDT"
    assert result["direction"] == "LONG"
    assert result["entry_price"] == 100.0
    assert result["position_id"] > 0
    print(f"✓ Opened LONG position id={result['position_id']}")


def test_open_short_position(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    sig = _make_signal(symbol="ETHUSDT", direction="short", price=200.0)
    result = open_paper_position(sig)
    assert result is not None
    assert result["direction"] == "SHORT"
    print("✓ Opened SHORT position")


# ─── 5. Position sizing ──────────────────────────────────────────────────

def test_position_size_is_1pct_of_equity(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    sig = _make_signal(symbol="BTCUSDT", direction="long", price=50.0)
    result = open_paper_position(sig)
    expected_size = STARTING_BALANCE * RISK_PER_TRADE_PCT  # 100.0
    assert abs(result["size_usdt"] - expected_size) < 0.01
    print(f"✓ Position size = {result['size_usdt']} (1% of {STARTING_BALANCE})")


def test_qty_computed_from_size_and_price(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    sig = _make_signal(direction="long", price=100.0)
    result = open_paper_position(sig)
    # size=100, price=100 → qty=1.0
    assert abs(result["qty"] - 1.0) < 0.0001
    print(f"✓ qty={result['qty']} (size/price)")


# ─── 6. Max open positions limit ──────────────────────────────────────────

def test_max_open_positions_enforced(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    # Temporarily set MAX_OPEN_POSITIONS to 3 for testing
    try:
        pb.MAX_OPEN_POSITIONS = 3
        for i in range(3):
            open_paper_position(_make_signal(symbol=f"SYM{i}", direction="long", price=10.0))
        # Next open should be refused
        result = open_paper_position(_make_signal(symbol="EXTRA", direction="long", price=10.0))
        assert result is None
        assert len(get_open_positions()) == 3
        print("✓ Max open positions enforced when set to 3")
    finally:
        pb.MAX_OPEN_POSITIONS = None


# ─── 7. One position per symbol ───────────────────────────────────────────

def test_one_position_per_symbol(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    open_paper_position(_make_signal(symbol="BTCUSDT", direction="long", price=100.0))
    result = open_paper_position(_make_signal(symbol="BTCUSDT", direction="long", price=101.0))
    assert result is None
    assert len(get_open_positions()) == 1
    print("✓ One open position per symbol enforced")


# ─── 8. Missing price handling ────────────────────────────────────────────

def test_open_without_price_returns_none(db_path, monkeypatch):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    sig = _make_signal(direction="long", price=None)
    # Force _fetch_price to return None (no network access in tests)
    monkeypatch.setattr(pb, "_fetch_price", lambda symbol: None)
    result = open_paper_position(sig)
    assert result is None
    print("✓ Missing entry price handled gracefully")


# ─── 9. Close position ──────────────────────────────────────────────────

def test_close_manual_close(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    result = open_paper_position(_make_signal(direction="long", price=100.0))
    pid = result["position_id"]
    closed = close_paper_position(pid, status="MANUAL_CLOSE", close_price=100.0)
    assert closed is not None
    assert closed["status"] == "MANUAL_CLOSE"
    assert len(get_open_positions()) == 0
    print("✓ MANUAL_CLOSE closes position")


def test_close_invalid_status_rejected(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    result = open_paper_position(_make_signal(direction="long", price=100.0))
    pid = result["position_id"]
    closed = close_paper_position(pid, status="INVALID")
    assert closed is None
    print("✓ Invalid close status rejected")


def test_close_nonexistent_position_returns_none(db_path):
    _reset_db(db_path)
    closed = close_paper_position(9999, status="MANUAL_CLOSE")
    assert closed is None
    print("✓ Closing nonexistent position returns None")


# ─── 10. PnL realization ───────────────────────────────────────────────

def test_long_winning_pnl_positive(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    result = open_paper_position(_make_signal(direction="long", price=100.0))
    pid = result["position_id"]
    # qty=1.0, entry=100, close=110 → +10%
    closed = close_paper_position(pid, status="TP_HIT", close_price=110.0)
    assert closed["realized_pnl"] > 0
    # 1.0 * 100 * 0.10 = 10.0
    assert abs(closed["realized_pnl"] - 10.0) < 0.01
    print(f"✓ LONG win pnl={closed['realized_pnl']}")


def test_short_winning_pnl_positive(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    result = open_paper_position(_make_signal(symbol="ETHUSDT", direction="short", price=200.0))
    pid = result["position_id"]
    # qty=0.5, entry=200, close=190 (price down → SHORT wins)
    closed = close_paper_position(pid, status="TP_HIT", close_price=190.0)
    assert closed["realized_pnl"] > 0
    print(f"✓ SHORT win pnl={closed['realized_pnl']}")


def test_losing_pnl_negative(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    result = open_paper_position(_make_signal(direction="long", price=100.0))
    pid = result["position_id"]
    closed = close_paper_position(pid, status="SL_HIT", close_price=90.0)
    assert closed["realized_pnl"] < 0
    print(f"✓ Losing position pnl={closed['realized_pnl']}")


def test_realized_pnl_updates_balance(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    result = open_paper_position(_make_signal(direction="long", price=100.0))
    pid = result["position_id"]
    close_paper_position(pid, status="TP_HIT", close_price=110.0)
    acct = get_account()
    # balance was 10000, +10 pnl → 10010
    assert abs(acct["balance"] - 10010.0) < 0.01
    print(f"✓ Balance updated to {acct['balance']} after realized pnl")


# ─── 11. Equity calculation ────────────────────────────────────────────────

def test_equity_equals_balance_with_no_open(db_path):
    _reset_db(db_path)
    eq = calculate_equity()
    assert abs(eq["equity"] - STARTING_BALANCE) < 0.01
    assert abs(eq["unrealized_pnl"]) < 0.01
    print("✓ Equity == balance with no open positions")


def test_equity_reflects_unrealized_long_profit(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    # Open LONG at 100, qty=1.0
    open_paper_position(_make_signal(direction="long", price=100.0))
    # Manually bump current_price to 110 to simulate unrealized profit
    conn = sqlite3.connect(str(db_path))
    conn.execute("UPDATE paper_positions SET current_price = 110.0 WHERE status = 'OPEN'")
    conn.commit()
    conn.close()
    eq = calculate_equity()
    # unrealized = 1.0 * 100 * 0.10 = 10
    assert abs(eq["unrealized_pnl"] - 10.0) < 0.01
    assert abs(eq["equity"] - 10010.0) < 0.01
    print(f"✓ Equity reflects unrealized LONG profit: {eq['equity']}")


def test_equity_reflects_unrealized_short_profit(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    open_paper_position(_make_signal(symbol="ETHUSDT", direction="short", price=200.0))
    # SHORT at 200, qty=0.5; price drops to 190 → SHORT profit
    conn = sqlite3.connect(str(db_path))
    conn.execute("UPDATE paper_positions SET current_price = 190.0 WHERE status = 'OPEN'")
    conn.commit()
    conn.close()
    eq = calculate_equity()
    # SHORT: move = -(190-200)/200 = 0.05
    # pnl = qty * entry * move = 0.5 * 200 * 0.05 = 5.0
    assert abs(eq["unrealized_pnl"] - 5.0) < 0.01
    print(f"✓ Equity reflects unrealized SHORT profit: {eq['unrealized_pnl']}")


# ─── 12. Lifecycle / update_open_positions ────────────────────────────────

def test_lifecycle_closes_tp_hit_long(db_path, monkeypatch):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    # LONG entry=100, tp=110; force _fetch_price to return None so current_price is used
    monkeypatch.setattr(pb, "_fetch_price", lambda symbol: None)
    _insert_open_position(db_path, "BTCUSDT", "LONG", 100.0, qty=1.0,
                         current_price=115.0, tp=110.0, sl=90.0)
    summary = update_open_positions()
    assert summary["tp"] == 1
    assert len(get_open_positions()) == 0
    print("✓ Lifecycle closed LONG on TP hit")


def test_lifecycle_closes_sl_hit_long(db_path, monkeypatch):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    monkeypatch.setattr(pb, "_fetch_price", lambda symbol: None)
    _insert_open_position(db_path, "BTCUSDT", "LONG", 100.0, qty=1.0,
                         current_price=85.0, tp=110.0, sl=90.0)
    summary = update_open_positions()
    assert summary["sl"] == 1
    print("✓ Lifecycle closed LONG on SL hit")


def test_lifecycle_closes_tp_hit_short(db_path, monkeypatch):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    monkeypatch.setattr(pb, "_fetch_price", lambda symbol: None)
    # SHORT: tp below entry. price 85 <= tp 90 → TP hit
    _insert_open_position(db_path, "ETHUSDT", "SHORT", 100.0, qty=1.0,
                         current_price=85.0, tp=90.0, sl=110.0)
    summary = update_open_positions()
    assert summary["tp"] == 1
    print("✓ Lifecycle closed SHORT on TP hit")


def test_lifecycle_closes_sl_hit_short(db_path, monkeypatch):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    monkeypatch.setattr(pb, "_fetch_price", lambda symbol: None)
    # SHORT: sl above entry. price 115 >= sl 110 → SL hit
    _insert_open_position(db_path, "ETHUSDT", "SHORT", 100.0, qty=1.0,
                         current_price=115.0, tp=90.0, sl=110.0)
    summary = update_open_positions()
    assert summary["sl"] == 1
    print("✓ Lifecycle closed SHORT on SL hit")


def test_lifecycle_no_close_when_price_in_range(db_path, monkeypatch):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    monkeypatch.setattr(pb, "_fetch_price", lambda symbol: None)
    _insert_open_position(db_path, "BTCUSDT", "LONG", 100.0, qty=1.0,
                         current_price=105.0, tp=110.0, sl=90.0)
    summary = update_open_positions()
    assert summary["tp"] == 0 and summary["sl"] == 0 and summary["expired"] == 0
    assert len(get_open_positions()) == 1
    print("✓ Lifecycle keeps position open when in range")


def test_lifecycle_closes_expired(db_path, monkeypatch):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    monkeypatch.setattr(pb, "_fetch_price", lambda symbol: None)
    # opened 8 days ago → expired
    old_ts = (datetime.now(timezone.utc) - timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S")
    _insert_open_position(db_path, "BTCUSDT", "LONG", 100.0, qty=1.0,
                         current_price=100.0, tp=110.0, sl=90.0,
                         opened_at=old_ts)
    summary = update_open_positions()
    assert summary["expired"] == 1
    print("✓ Lifecycle closed expired position")


# ─── 13. Portfolio summary & win rate ────────────────────────────────────

def test_portfolio_summary_structure(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    summary = get_portfolio_summary()
    assert "account" in summary
    assert "open_positions" in summary
    assert "closed_positions" in summary
    assert "stats" in summary
    assert summary["account"]["balance"] == STARTING_BALANCE
    print("✓ Portfolio summary has correct structure")


def test_win_rate_calculation(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    # Open and close 2 positions: 1 win, 1 loss
    r1 = open_paper_position(_make_signal(symbol="BTCUSDT", direction="long", price=100.0))
    close_paper_position(r1["position_id"], status="TP_HIT", close_price=110.0)  # win
    r2 = open_paper_position(_make_signal(symbol="ETHUSDT", direction="long", price=100.0))
    close_paper_position(r2["position_id"], status="SL_HIT", close_price=90.0)  # loss

    summary = get_portfolio_summary()
    assert summary["stats"]["closed_count"] == 2
    assert summary["stats"]["wins"] == 1
    assert summary["stats"]["losses"] == 1
    assert abs(summary["stats"]["win_rate"] - 50.0) < 0.01
    print(f"✓ Win rate = {summary['stats']['win_rate']}% (1W/1L)")


def test_total_realized_pnl_in_summary(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    r = open_paper_position(_make_signal(direction="long", price=100.0))
    close_paper_position(r["position_id"], status="TP_HIT", close_price=110.0)  # +10
    summary = get_portfolio_summary()
    assert abs(summary["stats"]["total_realized_pnl"] - 10.0) < 0.01
    print(f"✓ total_realized_pnl = {summary['stats']['total_realized_pnl']}")


# ─── 14. Execution Intelligence Layer Filters ───────────────────────────

def test_confidence_filter(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    
    # 60 confidence -> skipped
    sig_low = _make_signal(symbol="BTCUSDT", direction="long", price=100.0)
    sig_low["confidence"] = 60
    r_low = open_paper_position(sig_low)
    assert r_low is None
    
    # 75 confidence -> accepted
    sig_high = _make_signal(symbol="BTCUSDT", direction="long", price=100.0)
    sig_high["confidence"] = 75
    r_high = open_paper_position(sig_high)
    assert r_high is not None
    print("✓ Confidence filter verified (60 skipped, 75 accepted)")


def test_regime_filter(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    
    # choppy_low_vol -> skipped
    sig_choppy = _make_signal(symbol="BTCUSDT", direction="long", price=100.0)
    sig_choppy["regime"] = "choppy_low_vol"
    r_choppy = open_paper_position(sig_choppy)
    assert r_choppy is None
    
    # trending_normal_vol -> accepted
    sig_trending = _make_signal(symbol="BTCUSDT", direction="long", price=100.0)
    sig_trending["regime"] = "trending_normal_vol"
    r_trending = open_paper_position(sig_trending)
    assert r_trending is not None
    print("✓ Regime filter verified (choppy_low_vol skipped, trending_normal_vol accepted)")


def test_edge_filter(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    
    # 0.10 edge -> skipped (short 0.10, neutral 0.40, long 0.50) -> 0.50 - 0.40 = 0.10
    sig_low_edge = _make_signal(symbol="BTCUSDT", direction="long", price=100.0)
    sig_low_edge["prob_short"] = 0.10
    sig_low_edge["prob_neutral"] = 0.40
    sig_low_edge["prob_long"] = 0.50
    r_low = open_paper_position(sig_low_edge)
    assert r_low is None
    
    # 0.25 edge -> accepted (short 0.10, neutral 0.30, long 0.60) -> 0.60 - 0.30 = 0.30 >= 0.20
    sig_high_edge = _make_signal(symbol="BTCUSDT", direction="long", price=100.0)
    sig_high_edge["prob_short"] = 0.10
    sig_high_edge["prob_neutral"] = 0.30
    sig_high_edge["prob_long"] = 0.60
    r_high = open_paper_position(sig_high_edge)
    assert r_high is not None
    print("✓ Edge filter verified (0.10 edge skipped, 0.30 edge accepted)")


def test_cooldown_filter(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    
    # Open and hit SL
    r1 = open_paper_position(_make_signal(symbol="BTCUSDT", direction="long", price=100.0))
    assert r1 is not None
    close_paper_position(r1["position_id"], status="SL_HIT", close_price=90.0)
    
    # Attempt to open same symbol, same direction immediately -> skipped
    r2 = open_paper_position(_make_signal(symbol="BTCUSDT", direction="long", price=100.0))
    assert r2 is None
    
    # Bypassing the cooldown using a different direction -> accepted
    r3 = open_paper_position(_make_signal(symbol="BTCUSDT", direction="short", price=100.0))
    assert r3 is not None
    
    # Wait, what if SL was 8 hours ago?
    # We can insert a raw closed position with closed_at set to 8 hours ago
    conn = sqlite3.connect(str(db_path))
    eight_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """INSERT INTO paper_positions
           (symbol, direction, entry_price, current_price, size_usdt, qty,
            status, realized_pnl, opened_at, closed_at)
           VALUES ('ETHUSDT', 'LONG', 100.0, 90.0, 100.0, 1.0, 'SL_HIT', -10.0, ?, ?)""",
        ((datetime.now(timezone.utc) - timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
         eight_hours_ago),
    )
    conn.commit()
    conn.close()
    
    r4 = open_paper_position(_make_signal(symbol="ETHUSDT", direction="long", price=100.0))
    assert r4 is not None
    print("✓ Cooldown filter verified (recent SL hit skipped, older SL hit accepted)")


def test_unlimited_positions(db_path):
    _reset_db(db_path)
    set_trading_mode("PAPER")
    
    # Open 20 symbols -> accepted
    for i in range(20):
        r = open_paper_position(_make_signal(symbol=f"SYM{i}", direction="long", price=100.0))
        assert r is not None
        
    # Duplicate symbol -> rejected
    r_dup = open_paper_position(_make_signal(symbol="SYM0", direction="long", price=100.0))
    assert r_dup is None
    print("✓ Unlimited positions filter verified (20 distinct accepted, duplicate symbol rejected)")
