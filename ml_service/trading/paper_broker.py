"""Paper Broker Engine for MoroQuant autonomous paper trading.

Executes simulated trades against ML signals.  Persists a paper portfolio
(account balance, equity, open/closed positions) in SQLite.  The broker
honors the Trading Mode Manager and refuses to trade when the mode is not
PAPER.

Risk Rules
----------
* max_open_positions = 3
* risk_per_trade_pct = 1%  (position size = equity * 0.01)

Lifecycle
---------
Each scheduler cycle (when mode == PAPER):
    1. Refresh market prices for open positions.
    2. Check take-profit / stop-loss hits.
    3. Check expiration (7 days from open).
    4. Close positions that hit TP / SL / expiry.
    5. Re-evaluate equity.

This module is infrastructure only.  No live Binance execution happens here.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from utils.logger import get_logger

logger = get_logger()

# ── Configuration ────────────────────────────────────────────────────────

STARTING_BALANCE = 10000.0
MAX_OPEN_POSITIONS = 3
RISK_PER_TRADE_PCT = 0.01  # 1%
POSITION_EXPIRY_HOURS = 24 * 7  # 7 days

# DB path shared with the rest of ml_service
_DB_PATH: Path = Path(__file__).parent.parent / "storage" / "database.db"


# ── Connection helpers ───────────────────────────────────────────────────

def _get_connection():
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_account(conn: sqlite3.Connection):
    """Make sure the singleton account row exists (also created by migration)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS paper_account (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            balance REAL NOT NULL DEFAULT 10000.0,
            equity REAL NOT NULL DEFAULT 10000.0,
            unrealized_pnl REAL NOT NULL DEFAULT 0.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute(
        "INSERT OR IGNORE INTO paper_account (id, balance, equity, unrealized_pnl) "
        "VALUES (1, ?, ?, 0.0)",
        (STARTING_BALANCE, STARTING_BALANCE),
    )
    conn.commit()


# ── Price fetching ───────────────────────────────────────────────────────

def _fetch_price(symbol: str) -> Optional[float]:
    """Fetch the latest market price for *symbol*.

    Falls back through the crypto price service and the proxy price
    service.  Returns None if no price can be resolved.
    """
    # Crypto symbols
    try:
        from services.crypto_price_service import get_crypto_service
        svc = get_crypto_service()
        data = svc.get_price(symbol)
        if data and data.get("price") is not None:
            return float(data["price"])
    except Exception as e:
        logger.debug(f"crypto price fetch failed for {symbol}: {e}")

    # Proxy / traditional-market symbols (e.g. ES_proxy)
    try:
        from services.proxy_price_service import get_proxy_service
        svc = get_proxy_service()
        data = svc.get_price(symbol)
        if data and data.get("price") is not None:
            return float(data["price"])
    except Exception as e:
        logger.debug(f"proxy price fetch failed for {symbol}: {e}")

    return None


# ── Account ──────────────────────────────────────────────────────────────

def _get_account(conn: sqlite3.Connection) -> sqlite3.Row:
    _ensure_account(conn)
    return conn.execute(
        "SELECT balance, equity, unrealized_pnl, updated_at FROM paper_account WHERE id = 1"
    ).fetchone()


def _save_account(conn: sqlite3.Connection, balance: float, equity: float, unrealized: float):
    conn.execute(
        "UPDATE paper_account SET balance = ?, equity = ?, unrealized_pnl = ?, "
        "updated_at = CURRENT_TIMESTAMP WHERE id = 1",
        (balance, equity, unrealized),
    )
    conn.commit()


def calculate_equity() -> Dict:
    """Recompute equity = balance + sum(unrealized PnL of open positions).

    Returns a dict with ``balance``, ``equity``, ``unrealized_pnl``.
    """
    conn = _get_connection()
    try:
        _ensure_account(conn)
        account = _get_account(conn)
        balance = account["balance"]

        rows = conn.execute(
            "SELECT qty, entry_price, current_price, direction FROM paper_positions WHERE status = 'OPEN'"
        ).fetchall()

        unrealized = 0.0
        for r in rows:
            price = r["current_price"]
            if price is None or price <= 0 or r["entry_price"] <= 0:
                continue
            qty = r["qty"]
            move = (price - r["entry_price"]) / r["entry_price"]
            if r["direction"] == "SHORT":
                move = -move
            unrealized += qty * r["entry_price"] * move

        equity = balance + unrealized
        _save_account(conn, balance, equity, unrealized)
        return {
            "balance": balance,
            "equity": equity,
            "unrealized_pnl": unrealized,
        }
    finally:
        conn.close()


# ── Position lifecycle ───────────────────────────────────────────────────

def open_paper_position(signal: Dict) -> Optional[Dict]:
    """Open a paper position from an ML signal dict.

    Honors:
      * Trading mode == PAPER (refuses otherwise).
      * Direction != neutral (skips neutral signals).
      * max_open_positions.
      * Existing open position on the same symbol (one-trade-per-symbol).

    Returns the opened position dict, or None if skipped.
    """
    # ── Mode gate ──────────────────────────────────────────────────────
    from trading.mode_manager import get_trading_mode
    if get_trading_mode() != "PAPER":
        logger.info("Paper broker: mode != PAPER, skipping open")
        return None

    direction_raw = (signal.get("direction") or "").upper()
    if direction_raw == "NEUTRAL":
        logger.info("Paper broker: skipping neutral signal")
        return None
    if direction_raw not in ("LONG", "SHORT"):
        logger.info(f"Paper broker: unknown direction {direction_raw!r}, skipping")
        return None

    symbol = signal.get("symbol")
    if not symbol:
        logger.warning("Paper broker: signal has no symbol")
        return None

    entry_price = signal.get("price")
    if entry_price is None or entry_price <= 0:
        entry_price = _fetch_price(symbol)
    if entry_price is None or entry_price <= 0:
        logger.warning(f"Paper broker: no entry price for {symbol}")
        return None

    conn = _get_connection()
    try:
        _ensure_account(conn)

        # ── Max open positions ─────────────────────────────────────────
        open_count = conn.execute(
            "SELECT COUNT(*) AS c FROM paper_positions WHERE status = 'OPEN'"
        ).fetchone()["c"]
        if open_count >= MAX_OPEN_POSITIONS:
            logger.info(
                f"Paper broker: max open positions ({MAX_OPEN_POSITIONS}) reached"
            )
            return None

        # ── One open position per symbol ───────────────────────────────
        existing = conn.execute(
            "SELECT id FROM paper_positions WHERE symbol = ? AND status = 'OPEN'",
            (symbol,),
        ).fetchone()
        if existing:
            logger.info(f"Paper broker: open position already exists for {symbol}")
            return None

        # ── Position sizing ────────────────────────────────────────────
        account = _get_account(conn)
        equity = account["equity"]
        size_usdt = round(equity * RISK_PER_TRADE_PCT, 2)
        qty = round(size_usdt / entry_price, 8) if entry_price > 0 else 0.0

        if qty <= 0:
            logger.warning("Paper broker: computed qty <= 0, skipping")
            return None

        # ── Resolve signal_id (look up most recent persisted signal) ──
        signal_id = None
        try:
            row = conn.execute(
                "SELECT id FROM signals WHERE symbol = ? ORDER BY created_at DESC LIMIT 1",
                (symbol,),
            ).fetchone()
            if row:
                signal_id = row["id"]
        except Exception:
            pass

        stop_loss = signal.get("stop_loss")
        take_profit = signal.get("take_profit")

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO paper_positions
                (symbol, direction, entry_price, current_price, size_usdt, qty,
                 stop_loss, take_profit, signal_id, status, realized_pnl, opened_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', 0.0, CURRENT_TIMESTAMP)
            """,
            (symbol, direction_raw, float(entry_price), float(entry_price),
             size_usdt, qty, stop_loss, take_profit, signal_id),
        )
        conn.commit()
        position_id = cursor.lastrowid

        logger.info(
            f"Paper position OPENED: id={position_id} {symbol} {direction_raw} "
            f"qty={qty} entry={entry_price} size=${size_usdt}"
        )
        return {
            "position_id": position_id,
            "symbol": symbol,
            "direction": direction_raw,
            "entry_price": float(entry_price),
            "size_usdt": size_usdt,
            "qty": qty,
            "signal_id": signal_id,
        }
    finally:
        conn.close()


def close_paper_position(position_id: int, status: str = "MANUAL_CLOSE",
                         close_price: Optional[float] = None) -> Optional[Dict]:
    """Close a paper position and realize PnL.

    status must be one of: TP_HIT, SL_HIT, EXPIRED, MANUAL_CLOSE.
    Returns the closed-position summary dict, or None on failure.
    """
    if status not in ("TP_HIT", "SL_HIT", "EXPIRED", "MANUAL_CLOSE"):
        logger.warning(f"Paper broker: invalid close status {status!r}")
        return None

    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM paper_positions WHERE id = ? AND status = 'OPEN'",
            (position_id,),
        ).fetchone()
        if not row:
            logger.warning(f"Paper broker: no open position id={position_id}")
            return None

        entry = row["entry_price"]
        qty = row["qty"]
        direction = row["direction"]

        price = close_price if (close_price and close_price > 0) else row["current_price"]
        if price is None or price <= 0:
            price = entry  # fallback: no realized move

        move = (price - entry) / entry if entry > 0 else 0.0
        if direction == "SHORT":
            move = -move
        realized_pnl = qty * entry * move

        conn.execute(
            """
            UPDATE paper_positions
            SET status = ?, realized_pnl = ?, current_price = ?, closed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, realized_pnl, price, position_id),
        )

        # Realize PnL into balance
        account = _get_account(conn)
        new_balance = account["balance"] + realized_pnl
        conn.execute(
            "UPDATE paper_account SET balance = ? WHERE id = 1",
            (new_balance,),
        )
        conn.commit()

        logger.info(
            f"Paper position CLOSED: id={position_id} {row['symbol']} "
            f"{direction} status={status} pnl=${realized_pnl:.2f}"
        )

        return {
            "position_id": position_id,
            "symbol": row["symbol"],
            "direction": direction,
            "status": status,
            "realized_pnl": realized_pnl,
            "close_price": price,
        }
    finally:
        conn.close()


def update_open_positions() -> Dict:
    """Lifecycle pass: refresh prices, check TP/SL/expiry, close as needed.

    Returns a summary dict with counts of closed positions by reason.
    """
    conn = _get_connection()
    closed_summary = {"tp": 0, "sl": 0, "expired": 0, "checked": 0}

    try:
        rows = conn.execute(
            "SELECT * FROM paper_positions WHERE status = 'OPEN'"
        ).fetchall()
        position_ids = [r["id"] for r in rows]
    finally:
        conn.close()

    now = datetime.utcnow()

    for pid in position_ids:
        # Need to re-open a connection per close to avoid overlap with close logic
        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM paper_positions WHERE id = ?", (pid,)
            ).fetchone()
        finally:
            conn.close()

        if not row or row["status"] != "OPEN":
            continue

        closed_summary["checked"] += 1
        symbol = row["symbol"]
        direction = row["direction"]
        entry = row["entry_price"]

        # ── Refresh price ──────────────────────────────────────────────
        price = _fetch_price(symbol)
        if price and price > 0:
            conn = _get_connection()
            try:
                conn.execute(
                    "UPDATE paper_positions SET current_price = ? WHERE id = ?",
                    (price, pid),
                )
                conn.commit()
            finally:
                conn.close()
        else:
            price = row["current_price"] or entry

        # ── TP / SL evaluation ─────────────────────────────────────────
        tp = row["take_profit"]
        sl = row["stop_loss"]

        hit = None
        if direction == "LONG":
            if tp and price >= tp:
                hit = ("TP_HIT", tp)
            elif sl and price <= sl:
                hit = ("SL_HIT", sl)
        else:  # SHORT
            if tp and price <= tp:
                hit = ("TP_HIT", tp)
            elif sl and price >= sl:
                hit = ("SL_HIT", sl)

        if hit:
            status, close_price = hit
            close_paper_position(pid, status=status, close_price=close_price)
            closed_summary["tp" if status == "TP_HIT" else "sl"] += 1
            continue

        # ── Expiration ─────────────────────────────────────────────────
        opened_at_str = row["opened_at"]
        try:
            opened_at = datetime.strptime(opened_at_str.replace("Z", ""), "%Y-%m-%d %H:%M:%S")
        except Exception:
            opened_at = None

        if opened_at and (now - opened_at) > timedelta(hours=POSITION_EXPIRY_HOURS):
            close_paper_position(pid, status="EXPIRED", close_price=price)
            closed_summary["expired"] += 1

    # Recompute equity after the pass
    calculate_equity()
    return closed_summary


# ── Reporting ────────────────────────────────────────────────────────────

def _row_to_dict(row: sqlite3.Row) -> Dict:
    return {k: row[k] for k in row.keys()} if row else {}


def get_portfolio_summary() -> Dict:
    """Return a full portfolio summary for the API + dashboard."""
    conn = _get_connection()
    try:
        _ensure_account(conn)
        account = _get_account(conn)

        open_rows = conn.execute(
            "SELECT * FROM paper_positions WHERE status = 'OPEN' ORDER BY opened_at DESC"
        ).fetchall()
        closed_rows = conn.execute(
            "SELECT * FROM paper_positions WHERE status != 'OPEN' ORDER BY closed_at DESC"
        ).fetchall()

        # Win rate over closed positions
        wins = sum(1 for r in closed_rows if r["realized_pnl"] > 0)
        total_closed = len(closed_rows)
        win_rate = (wins / total_closed * 100.0) if total_closed else 0.0
        total_pnl = sum(r["realized_pnl"] for r in closed_rows)

        return {
            "account": {
                "balance": account["balance"],
                "equity": account["equity"],
                "unrealized_pnl": account["unrealized_pnl"],
                "updated_at": account["updated_at"],
            },
            "open_positions": [_row_to_dict(r) for r in open_rows],
            "closed_positions": [_row_to_dict(r) for r in closed_rows],
            "stats": {
                "open_count": len(open_rows),
                "closed_count": total_closed,
                "wins": wins,
                "losses": total_closed - wins,
                "win_rate": round(win_rate, 2),
                "total_realized_pnl": round(total_pnl, 2),
                "starting_balance": STARTING_BALANCE,
                "max_open_positions": MAX_OPEN_POSITIONS,
                "risk_per_trade_pct": RISK_PER_TRADE_PCT,
            },
        }
    finally:
        conn.close()


def get_open_positions() -> List[Dict]:
    """Return all currently-open paper positions."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM paper_positions WHERE status = 'OPEN' ORDER BY opened_at DESC"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_closed_positions(limit: int = 100) -> List[Dict]:
    """Return recently closed paper positions."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM paper_positions WHERE status != 'OPEN' "
            "ORDER BY closed_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_account() -> Dict:
    """Return the singleton account snapshot."""
    conn = _get_connection()
    try:
        _ensure_account(conn)
        account = _get_account(conn)
        return _row_to_dict(account)
    finally:
        conn.close()
