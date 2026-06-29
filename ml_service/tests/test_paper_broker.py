"""Unit tests for ml_service.trading.paper_broker (Paper Broker Engine)."""

import sys
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Ensure ml_service root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Override DB path to a temp file BEFORE importing modules ──────────
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
_TEST_DB_PATH = Path(_tmp.name)

import trading.mode_manager as mm
import trading.paper_broker as pb
mm._DB_PATH = _TEST_DB_PATH
pb._DB_PATH = _TEST_DB_PATH

from trading.mode_manager import set_trading_mode, get_trading_mode, VALID_MODES
from trading.paper_broker import (
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


def _reset_db():
    """Wipe and recreate both tables so each test starts clean."""
    if _TEST_DB_PATH.exists():
        _TEST_DB_PATH.unlink()
    conn = sqlite3.connect(str(_TEST_DB_PATH))
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
            closed_at TIMESTAMP
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


def _insert_open_position(symbol, direction, entry_price, qty=1.0,
                          current_price=None, tp=None, sl=None,
                          opened_at=None):
    """Insert a raw OPEN position bypassing the open() logic."""
    conn = sqlite3.connect(str(_TEST_DB_PATH))
    conn.execute(
        """INSERT INTO paper_positions
           (symbol, direction, entry_price, current_price, size_usdt, qty,
            stop_loss, take_profit, status, realized_pnl, opened_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', 0.0, ?)""",
        (symbol, direction, entry_price, current_price or entry_price,
         qty * entry_price, qty, sl, tp, opened_at or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


# ─── 1. Account initialization ───────────────────────────────────────────

def test_account_default_balance():
    _reset_db()
    acct = get_account()
    assert acct["balance"] == STARTING_BALANCE
    assert acct["equity"] == STARTING_BALANCE
    print(f"✓ Account defaults to {STARTING_BALANCE} USDT")


def test_starting_balance_is_10000():
    assert STARTING_BALANCE == 10000.0
    print("✓ STARTING_BALANCE == 10000")


# ─── 2. Mode gating ──────────────────────────────────────────────────────

def test_open_refused_when_mode_off():
    _reset_db()
    set_trading_mode("OFF")
    result = open_paper_position(_make_signal(direction="long"))
    assert result is None
    assert len(get_open_positions()) == 0
    print("✓ open_paper_position refused when mode=OFF")


def test_open_refused_when_mode_live():
    _reset_db()
    set_trading_mode("LIVE")
    result = open_paper_position(_make_signal(direction="long"))
    assert result is None
    print("✓ open_paper_position refused when mode=LIVE")


def test_open_refused_when_mode_maintenance():
    _reset_db()
    set_trading_mode("MAINTENANCE")
    result = open_paper_position(_make_signal(direction="long"))
    assert result is None
    print("✓ open_paper_position refused when mode=MAINTENANCE")


# ─── 3. Neutral signal rejection ─────────────────────────────────────────

def test_neutral_signal_skipped():
    _reset_db()
    set_trading_mode("PAPER")
    result = open_paper_position(_make_signal(direction="neutral"))
    assert result is None
    assert len(get_open_positions()) == 0
    print("✓ Neutral signal skipped")


# ─── 4. Successful open ──────────────────────────────────────────────────

def test_open_long_position():
    _reset_db()
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


def test_open_short_position():
    _reset_db()
    set_trading_mode("PAPER")
    sig = _make_signal(symbol="ETHUSDT", direction="short", price=200.0)
    result = open_paper_position(sig)
    assert result is not None
    assert result["direction"] == "SHORT"
    print("✓ Opened SHORT position")


# ─── 5. Position sizing ──────────────────────────────────────────────────

def test_position_size_is_1pct_of_equity():
    _reset_db()
    set_trading_mode("PAPER")
    sig = _make_signal(symbol="BTCUSDT", direction="long", price=50.0)
    result = open_paper_position(sig)
    expected_size = STARTING_BALANCE * RISK_PER_TRADE_PCT  # 100.0
    assert abs(result["size_usdt"] - expected_size) < 0.01
    print(f"✓ Position size = {result['size_usdt']} (1% of {STARTING_BALANCE})")


def test_qty_computed_from_size_and_price():
    _reset_db()
    set_trading_mode("PAPER")
    sig = _make_signal(direction="long", price=100.0)
    result = open_paper_position(sig)
    # size=100, price=100 → qty=1.0
    assert abs(result["qty"] - 1.0) < 0.0001
    print(f"✓ qty={result['qty']} (size/price)")


# ─── 6. Max open positions limit ──────────────────────────────────────────

def test_max_open_positions_enforced():
    _reset_db()
    set_trading_mode("PAPER")
    # Open MAX_OPEN_POSITIONS distinct symbols
    for i in range(MAX_OPEN_POSITIONS):
        open_paper_position(_make_signal(symbol=f"SYM{i}", direction="long", price=10.0))
    # Next open should be refused
    result = open_paper_position(_make_signal(symbol="EXTRA", direction="long", price=10.0))
    assert result is None
    assert len(get_open_positions()) == MAX_OPEN_POSITIONS
    print(f"✓ Max open positions ({MAX_OPEN_POSITIONS}) enforced")


# ─── 7. One position per symbol ───────────────────────────────────────────

def test_one_position_per_symbol():
    _reset_db()
    set_trading_mode("PAPER")
    open_paper_position(_make_signal(symbol="BTCUSDT", direction="long", price=100.0))
    result = open_paper_position(_make_signal(symbol="BTCUSDT", direction="long", price=101.0))
    assert result is None
    assert len(get_open_positions()) == 1
    print("✓ One open position per symbol enforced")


# ─── 8. Missing price handling ────────────────────────────────────────────

def test_open_without_price_returns_none():
    _reset_db()
    set_trading_mode("PAPER")
    sig = _make_signal(direction="long", price=None)
    # _fetch_price will fail in test env (no network), so this should be None
    result = open_paper_position(sig)
    # If price is None and fetch fails, open is refused
    assert result is None
    print("✓ Missing entry price handled gracefully")


# ─── 9. Close position ────────────────────────────────────────────────────

def test_close_manual_close():
    _reset_db()
    set_trading_mode("PAPER")
    result = open_paper_position(_make_signal(direction="long", price=100.0))
    pid = result["position_id"]
    closed = close_paper_position(pid, status="MANUAL_CLOSE", close_price=100.0)
    assert closed is not None
    assert closed["status"] == "MANUAL_CLOSE"
    assert len(get_open_positions()) == 0
    print("✓ MANUAL_CLOSE closes position")


def test_close_invalid_status_rejected():
    _reset_db()
    set_trading_mode("PAPER")
    result = open_paper_position(_make_signal(direction="long", price=100.0))
    pid = result["position_id"]
    closed = close_paper_position(pid, status="INVALID")
    assert closed is None
    print("✓ Invalid close status rejected")


def test_close_nonexistent_position_returns_none():
    _reset_db()
    closed = close_paper_position(9999, status="MANUAL_CLOSE")
    assert closed is None
    print("✓ Closing nonexistent position returns None")


# ─── 10. PnL realization ─────────────────────────────────────────────────

def test_long_winning_pnl_positive():
    _reset_db()
    set_trading_mode("PAPER")
    result = open_paper_position(_make_signal(direction="long", price=100.0))
    pid = result["position_id"]
    # qty=1.0, entry=100, close=110 → +10%
    closed = close_paper_position(pid, status="TP_HIT", close_price=110.0)
    assert closed["realized_pnl"] > 0
    # 1.0 * 100 * 0.10 = 10.0
    assert abs(closed["realized_pnl"] - 10.0) < 0.01
    print(f"✓ LONG win pnl={closed['realized_pnl']}")


def test_short_winning_pnl_positive():
    _reset_db()
    set_trading_mode("PAPER")
    result = open_paper_position(_make_signal(symbol="ETHUSDT", direction="short", price=200.0))
    pid = result["position_id"]
    # qty=0.5, entry=200, close=190 (price down → SHORT wins)
    closed = close_paper_position(pid, status="TP_HIT", close_price=190.0)
    assert closed["realized_pnl"] > 0
    print(f"✓ SHORT win pnl={closed['realized_pnl']}")


def test_losing_pnl_negative():
    _reset_db()
    set_trading_mode("PAPER")
    result = open_paper_position(_make_signal(direction="long", price=100.0))
    pid = result["position_id"]
    closed = close_paper_position(pid, status="SL_HIT", close_price=90.0)
    assert closed["realized_pnl"] < 0
    print(f"✓ Losing position pnl={closed['realized_pnl']}")


def test_realized_pnl_updates_balance():
    _reset_db()
    set_trading_mode("PAPER")
    result = open_paper_position(_make_signal(direction="long", price=100.0))
    pid = result["position_id"]
    close_paper_position(pid, status="TP_HIT", close_price=110.0)
    acct = get_account()
    # balance was 10000, +10 pnl → 10010
    assert abs(acct["balance"] - 10010.0) < 0.01
    print(f"✓ Balance updated to {acct['balance']} after realized pnl")


# ─── 11. Equity calculation ──────────────────────────────────────────────

def test_equity_equals_balance_with_no_open():
    _reset_db()
    eq = calculate_equity()
    assert abs(eq["equity"] - STARTING_BALANCE) < 0.01
    assert abs(eq["unrealized_pnl"]) < 0.01
    print("✓ Equity == balance with no open positions")


def test_equity_reflects_unrealized_long_profit():
    _reset_db()
    set_trading_mode("PAPER")
    # Open LONG at 100, qty=1.0
    open_paper_position(_make_signal(direction="long", price=100.0))
    # Manually bump current_price to 110 to simulate unrealized profit
    conn = sqlite3.connect(str(_TEST_DB_PATH))
    conn.execute("UPDATE paper_positions SET current_price = 110.0 WHERE status = 'OPEN'")
    conn.commit()
    conn.close()
    eq = calculate_equity()
    # unrealized = 1.0 * 100 * 0.10 = 10
    assert abs(eq["unrealized_pnl"] - 10.0) < 0.01
    assert abs(eq["equity"] - 10010.0) < 0.01
    print(f"✓ Equity reflects unrealized LONG profit: {eq['equity']}")


def test_equity_reflects_unrealized_short_profit():
    _reset_db()
    set_trading_mode("PAPER")
    open_paper_position(_make_signal(symbol="ETHUSDT", direction="short", price=200.0))
    # SHORT at 200, qty=0.5; price drops to 190 → SHORT profit
    conn = sqlite3.connect(str(_TEST_DB_PATH))
    conn.execute("UPDATE paper_positions SET current_price = 190.0 WHERE status = 'OPEN'")
    conn.commit()
    conn.close()
    eq = calculate_equity()
    # unrealized = 0.5 * 200 * (-(190-200)/200) * -1 ... wait
    # SHORT: move = -(price-entry)/entry = -(-10/200) = 0.05
    # pnl = qty * entry * move = 0.5 * 200 * 0.05 = 5.0
    assert abs(eq["unrealized_pnl"] - 5.0) < 0.01
    print(f"✓ Equity reflects unrealized SHORT profit: {eq['unrealized_pnl']}")


# ─── 12. Lifecycle / update_open_positions ────────────────────────────────

def test_lifecycle_closes_tp_hit_long():
    _reset_db()
    set_trading_mode("PAPER")
    # LONG entry=100, tp=110; price service unavailable → use current_price
    _insert_open_position("BTCUSDT", "LONG", 100.0, qty=1.0,
                          current_price=115.0, tp=110.0, sl=90.0)
    summary = update_open_positions()
    assert summary["tp"] == 1
    assert len(get_open_positions()) == 0
    print("✓ Lifecycle closed LONG on TP hit")


def test_lifecycle_closes_sl_hit_long():
    _reset_db()
    set_trading_mode("PAPER")
    _insert_open_position("BTCUSDT", "LONG", 100.0, qty=1.0,
                          current_price=85.0, tp=110.0, sl=90.0)
    summary = update_open_positions()
    assert summary["sl"] == 1
    print("✓ Lifecycle closed LONG on SL hit")


def test_lifecycle_closes_tp_hit_short():
    _reset_db()
    set_trading_mode("PAPER")
    # SHORT: tp below entry. price 85 <= tp 90 → TP hit
    _insert_open_position("ETHUSDT", "SHORT", 100.0, qty=1.0,
                          current_price=85.0, tp=90.0, sl=110.0)
    summary = update_open_positions()
    assert summary["tp"] == 1
    print("✓ Lifecycle closed SHORT on TP hit")


def test_lifecycle_closes_sl_hit_short():
    _reset_db()
    set_trading_mode("PAPER")
    # SHORT: sl above entry. price 115 >= sl 110 → SL hit
    _insert_open_position("ETHUSDT", "SHORT", 100.0, qty=1.0,
                          current_price=115.0, tp=90.0, sl=110.0)
    summary = update_open_positions()
    assert summary["sl"] == 1
    print("✓ Lifecycle closed SHORT on SL hit")


def test_lifecycle_no_close_when_price_in_range():
    _reset_db()
    set_trading_mode("PAPER")
    _insert_open_position("BTCUSDT", "LONG", 100.0, qty=1.0,
                          current_price=105.0, tp=110.0, sl=90.0)
    summary = update_open_positions()
    assert summary["tp"] == 0 and summary["sl"] == 0 and summary["expired"] == 0
    assert len(get_open_positions()) == 1
    print("✓ Lifecycle keeps position open when in range")


def test_lifecycle_closes_expired():
    _reset_db()
    set_trading_mode("PAPER")
    # opened 8 days ago → expired
    old_ts = (datetime.utcnow() - timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S")
    _insert_open_position("BTCUSDT", "LONG", 100.0, qty=1.0,
                          current_price=100.0, tp=110.0, sl=90.0,
                          opened_at=old_ts)
    summary = update_open_positions()
    assert summary["expired"] == 1
    print("✓ Lifecycle closed expired position")


# ─── 13. Portfolio summary & win rate ────────────────────────────────────

def test_portfolio_summary_structure():
    _reset_db()
    set_trading_mode("PAPER")
    summary = get_portfolio_summary()
    assert "account" in summary
    assert "open_positions" in summary
    assert "closed_positions" in summary
    assert "stats" in summary
    assert summary["account"]["balance"] == STARTING_BALANCE
    print("✓ Portfolio summary has correct structure")


def test_win_rate_calculation():
    _reset_db()
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


def test_total_realized_pnl_in_summary():
    _reset_db()
    set_trading_mode("PAPER")
    r = open_paper_position(_make_signal(direction="long", price=100.0))
    close_paper_position(r["position_id"], status="TP_HIT", close_price=110.0)  # +10
    summary = get_portfolio_summary()
    assert abs(summary["stats"]["total_realized_pnl"] - 10.0) < 0.01
    print(f"✓ total_realized_pnl = {summary['stats']['total_realized_pnl']}")


# ─── Run all ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        # 1. Account
        test_account_default_balance,
        test_starting_balance_is_10000,
        # 2. Mode gating
        test_open_refused_when_mode_off,
        test_open_refused_when_mode_live,
        test_open_refused_when_mode_maintenance,
        # 3. Neutral
        test_neutral_signal_skipped,
        # 4. Successful open
        test_open_long_position,
        test_open_short_position,
        # 5. Sizing
        test_position_size_is_1pct_of_equity,
        test_qty_computed_from_size_and_price,
        # 6. Max positions
        test_max_open_positions_enforced,
        # 7. One per symbol
        test_one_position_per_symbol,
        # 8. Missing price
        test_open_without_price_returns_none,
        # 9. Close
        test_close_manual_close,
        test_close_invalid_status_rejected,
        test_close_nonexistent_position_returns_none,
        # 10. PnL
        test_long_winning_pnl_positive,
        test_short_winning_pnl_positive,
        test_losing_pnl_negative,
        test_realized_pnl_updates_balance,
        # 11. Equity
        test_equity_equals_balance_with_no_open,
        test_equity_reflects_unrealized_long_profit,
        test_equity_reflects_unrealized_short_profit,
        # 12. Lifecycle
        test_lifecycle_closes_tp_hit_long,
        test_lifecycle_closes_sl_hit_long,
        test_lifecycle_closes_tp_hit_short,
        test_lifecycle_closes_sl_hit_short,
        test_lifecycle_no_close_when_price_in_range,
        test_lifecycle_closes_expired,
        # 13. Summary
        test_portfolio_summary_structure,
        test_win_rate_calculation,
        test_total_realized_pnl_in_summary,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"✗ {t.__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Paper Broker: {passed} passed, {failed} failed out of {len(tests)}")
    if failed:
        sys.exit(1)

    # Cleanup
    if _TEST_DB_PATH.exists():
        _TEST_DB_PATH.unlink()
