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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from ml_service.utils.logger import get_logger

logger = get_logger()

# ── Configuration ────────────────────────────────────────────────────────

STARTING_BALANCE = 10000.0
MAX_OPEN_POSITIONS = None
RISK_PER_TRADE_PCT = 0.01  # 1%
POSITION_EXPIRY_HOURS = 24 * 7  # 7 days

MIN_EXECUTION_CONFIDENCE = 55
BLOCKED_REGIMES = [
    "choppy_low_vol",
    "choppy_normal_vol",
]
MIN_PROBABILITY_EDGE = 0.20
COOLDOWN_AFTER_SL_HOURS = 6

# Execution Policy Configuration
# Allows comparing different execution strategies in paper trading
EXECUTION_POLICY = "TRAILING"  # OFF | FIXED_SL | BREAK_EVEN | TRAILING

# Trailing Stop Parameters (used when policy = BREAK_EVEN or TRAILING)
BREAK_EVEN_AT_R = 1.0  # Move SL to break-even at +1R
TRAIL_AT_R = 2.0  # Start trailing at +2R (only for TRAILING policy)
TRAIL_DISTANCE_R = 0.5  # Trail distance in R multiples

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
        from ml_service.services.crypto_price_service import get_crypto_service
        svc = get_crypto_service()
        data = svc.get_price(symbol)
        if data and data.get("price") is not None:
            return float(data["price"])
    except Exception as e:
        logger.debug(f"crypto price fetch failed for {symbol}: {e}")

    # Proxy / traditional-market symbols (e.g. ES_proxy)
    try:
        from ml_service.services.proxy_price_service import get_proxy_service
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
      * confidence filter.
      * regime filter.
      * edge filter.
      * cooldown after stop loss.
      * max_open_positions.
      * Existing open position on the same symbol (one-trade-per-symbol).

    Returns the opened position dict, or None if skipped.
    """
    # ── Mode gate ──────────────────────────────────────────────────────
    from ml_service.trading.mode_manager import get_trading_mode
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

    # ── 1. Confidence Filter ───────────────────────────────────────────
    confidence = signal.get("confidence")
    if confidence is not None:
        try:
            conf_val = int(confidence)
            if conf_val < MIN_EXECUTION_CONFIDENCE:
                logger.info(
                    f"Paper broker skipped {symbol}: "
                    f"confidence {conf_val} < required {MIN_EXECUTION_CONFIDENCE}"
                )
                return None
        except (ValueError, TypeError):
            pass

    # ── 2. Regime Filter ───────────────────────────────────────────────
    regime = signal.get("regime")
    if regime in BLOCKED_REGIMES:
        logger.info(
            f"Paper broker skipped {symbol}: regime {regime} is blocked"
        )
        return None

    # ── 3. Edge Filter ─────────────────────────────────────────────────
    prob_short = signal.get("prob_short")
    prob_neutral = signal.get("prob_neutral")
    prob_long = signal.get("prob_long")
    probs_list = [prob_short, prob_neutral, prob_long]
    if all(p is not None for p in probs_list):
        try:
            prob_vals = [float(p) for p in probs_list]
            prob_vals.sort(reverse=True)
            edge = prob_vals[0] - prob_vals[1]
            if edge < MIN_PROBABILITY_EDGE:
                logger.info(
                    f"Paper broker skipped {symbol}: probability edge {edge:.2f} < required {MIN_PROBABILITY_EDGE:.2f}"
                )
                return None
        except (ValueError, TypeError):
            pass

    entry_price = signal.get("price")
    if entry_price is None or entry_price <= 0:
        entry_price = _fetch_price(symbol)
    if entry_price is None or entry_price <= 0:
        logger.warning(f"Paper broker: no entry price for {symbol}")
        return None

    conn = _get_connection()
    try:
        _ensure_account(conn)

        # ── 4. Cooldown After Stop Loss ──────────────────────────────────
        cooldown_row = conn.execute(
            """
            SELECT (julianday('now') - julianday(closed_at)) * 24 AS hours_ago
            FROM paper_positions
            WHERE symbol = ? AND direction = ? AND status = 'SL_HIT'
            ORDER BY closed_at DESC LIMIT 1
            """,
            (symbol, direction_raw),
        ).fetchone()
        if cooldown_row:
            hours_ago = cooldown_row["hours_ago"]
            if hours_ago is not None and hours_ago < COOLDOWN_AFTER_SL_HOURS:
                logger.info(
                    f"{symbol} {direction_raw} skipped: "
                    f"cooldown active (last SL {hours_ago:.1f}h ago)"
                )
                return None

        # ── 5. Max open positions ─────────────────────────────────────────
        if MAX_OPEN_POSITIONS is not None:
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
        timeframe = signal.get("timeframe")

        execution_edge = None
        if all(p is not None for p in probs_list):
            try:
                prob_vals = [float(p) for p in probs_list]
                prob_vals.sort(reverse=True)
                execution_edge = prob_vals[0] - prob_vals[1]
            except (ValueError, TypeError):
                pass

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO paper_positions
                (symbol, direction, entry_price, current_price, size_usdt, qty,
                 stop_loss, take_profit, signal_id, status, realized_pnl, opened_at,
                 confidence, regime, timeframe, prob_short, prob_neutral, prob_long,
                 execution_edge, skip_reason, execution_policy)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', 0.0, CURRENT_TIMESTAMP,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (symbol, direction_raw, float(entry_price), float(entry_price),
             size_usdt, qty, stop_loss, take_profit, signal_id,
             confidence, regime, timeframe,
             prob_short, prob_neutral, prob_long,
             execution_edge, None, EXECUTION_POLICY),
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
        size_usdt = row["size_usdt"]
        mae = row["mae"] or 0.0
        mfe = row["mfe"] or 0.0

        price = close_price if (close_price and close_price > 0) else row["current_price"]
        if price is None or price <= 0:
            price = entry  # fallback: no realized move

        move = (price - entry) / entry if entry > 0 else 0.0
        if direction == "SHORT":
            move = -move
        realized_pnl = qty * entry * move

        # Compute raw execution metrics (EQS derived later from these)
        profit_capture_ratio = None
        if mfe > 0.01 and size_usdt > 0:
            profit_capture_ratio = (realized_pnl / size_usdt) / mfe
            profit_capture_ratio = max(0.0, min(1.0, profit_capture_ratio))

        final_exit_reason = status

        conn.execute(
            """
            UPDATE paper_positions
            SET status = ?, realized_pnl = ?, current_price = ?, closed_at = CURRENT_TIMESTAMP,
                profit_capture_ratio = ?, final_exit_reason = ?
            WHERE id = ?
            """,
            (status, realized_pnl, price, profit_capture_ratio, final_exit_reason, position_id),
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

    now = datetime.now(tz=None)  # naive UTC, matches SQLite timestamps

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

        # ── MAE / MFE Tracking ─────────────────────────────────────────
        if price and price > 0 and entry > 0:
            move_pct = (price - entry) / entry
            if direction == "SHORT":
                move_pct = -move_pct

            current_mae = row["mae"] or 0.0
            current_mfe = row["mfe"] or 0.0

            updates = {}
            if move_pct < current_mae:
                updates["mae"] = move_pct
                updates["mae_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if move_pct > current_mfe:
                updates["mfe"] = move_pct
                updates["mfe_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if updates:
                conn = _get_connection()
                try:
                    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
                    values = list(updates.values()) + [pid]
                    conn.execute(
                        f"UPDATE paper_positions SET {set_clause} WHERE id = ?",
                        values,
                    )
                    conn.commit()
                finally:
                    conn.close()

        # ── Execution Policy Logic ────────────────────────────────────
        tp = row["take_profit"]
        sl = row["stop_loss"]
        execution_policy = row.get("execution_policy", "FIXED_SL")

        # Apply dynamic SL logic based on policy
        if execution_policy in ("BREAK_EVEN", "TRAILING") and sl and entry > 0 and price > 0:
            initial_risk = abs(entry - sl)
            if initial_risk > 0:
                current_profit_r = 0.0
                if direction == "LONG":
                    current_profit_r = (price - entry) / initial_risk
                else:  # SHORT
                    current_profit_r = (entry - price) / initial_risk

                sl_updates = {}
                sl_move_count = row.get("sl_move_count", 0)
                break_even_triggered = row.get("break_even_triggered", 0)

                # Break-even logic (for BREAK_EVEN and TRAILING policies)
                if not break_even_triggered and current_profit_r >= BREAK_EVEN_AT_R:
                    sl = entry
                    sl_updates["stop_loss"] = sl
                    sl_updates["break_even_triggered"] = 1
                    sl_updates["sl_move_count"] = sl_move_count + 1
                    logger.info(f"Position {pid} [{execution_policy}] moved to break-even at +{current_profit_r:.1f}R")

                # Trailing logic (only for TRAILING policy)
                elif execution_policy == "TRAILING" and current_profit_r >= TRAIL_AT_R:
                    if direction == "LONG":
                        new_sl = price - (initial_risk * TRAIL_DISTANCE_R)
                        if new_sl > sl:
                            sl = new_sl
                            sl_updates["stop_loss"] = sl
                            sl_updates["trailing_stop_activated"] = 1
                            sl_updates["sl_move_count"] = sl_move_count + 1
                    else:  # SHORT
                        new_sl = price + (initial_risk * TRAIL_DISTANCE_R)
                        if new_sl < sl:
                            sl = new_sl
                            sl_updates["stop_loss"] = sl
                            sl_updates["trailing_stop_activated"] = 1
                            sl_updates["sl_move_count"] = sl_move_count + 1

                if sl_updates:
                    conn = _get_connection()
                    try:
                        set_clause = ", ".join(f"{k} = ?" for k in sl_updates.keys())
                        values = list(sl_updates.values()) + [pid]
                        conn.execute(
                            f"UPDATE paper_positions SET {set_clause} WHERE id = ?",
                            values,
                        )
                        conn.commit()
                    finally:
                        conn.close()

        # ── TP / SL evaluation ─────────────────────────────────────────
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
            "ORDER BY closed_at DESC, id DESC LIMIT ?",
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


# ── Equity History ──────────────────────────────────────────────────────

def _ensure_equity_history_table(conn: sqlite3.Connection):
    """Create paper_equity_history table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS paper_equity_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equity REAL NOT NULL,
            balance REAL NOT NULL,
            unrealized_pnl REAL NOT NULL,
            snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_paper_equity_snapshot_time "
        "ON paper_equity_history(snapshot_time)"
    )
    conn.commit()


def capture_equity_snapshot() -> bool:
    """Capture a paper equity snapshot.

    Recomputes equity first, then inserts a row into
    ``paper_equity_history``.  Called by the scheduler every 5 minutes
    when mode == PAPER.

    Returns True on success.
    """
    equity_data = calculate_equity()
    conn = _get_connection()
    try:
        _ensure_equity_history_table(conn)
        conn.execute(
            "INSERT INTO paper_equity_history (equity, balance, unrealized_pnl) "
            "VALUES (?, ?, ?)",
            (equity_data["equity"], equity_data["balance"], equity_data["unrealized_pnl"]),
        )
        conn.commit()
        logger.debug(
            f"Paper equity snapshot: equity={equity_data['equity']:.2f}"
        )
        return True
    except Exception as e:
        logger.error(f"Paper equity snapshot failed: {e}")
        return False
    finally:
        conn.close()


def get_equity_history(range_hours: Optional[int] = None) -> List[Dict]:
    """Return paper equity history, optionally filtered by time range.

    Args:
        range_hours: If provided, limit to last N hours. Otherwise all.

    Returns a list of ``{timestamp, equity}`` dicts.
    """
    conn = _get_connection()
    try:
        _ensure_equity_history_table(conn)

        if range_hours is not None:
            rows = conn.execute(
                "SELECT snapshot_time, equity, balance, unrealized_pnl "
                "FROM paper_equity_history "
                "WHERE snapshot_time >= datetime('now', ? || ' hours') "
                "ORDER BY snapshot_time ASC",
                (f"-{range_hours}",),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT snapshot_time, equity, balance, unrealized_pnl "
                "FROM paper_equity_history ORDER BY snapshot_time ASC"
            ).fetchall()

        return [
            {
                "timestamp": r[0],
                "equity": r[1],
                "balance": r[2],
                "unrealized_pnl": r[3],
            }
            for r in rows
        ]
    finally:
        conn.close()


# ── Analytics ───────────────────────────────────────────────────────────

def compute_paper_analytics() -> Dict:
    """Compute trading analytics from closed paper positions.

    Returns a dict with the same shape as the live analytics endpoint so
    the dashboard can reuse the same widgets.
    """
    from ml_service.services.paper_analytics_service import compute_sharpe_ratio

    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT symbol, direction, entry_price, realized_pnl, opened_at, closed_at "
            "FROM paper_positions WHERE status != 'OPEN'"
        ).fetchall()
        open_count = conn.execute(
            "SELECT COUNT(*) AS c FROM paper_positions WHERE status = 'OPEN'"
        ).fetchone()["c"]
    finally:
        conn.close()

    total_trades = len(rows)
    if total_trades == 0:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "total_realized_pnl": 0.0,
            "avg_trade_pnl": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "avg_hold_hours": 0.0,
            "open_positions": open_count,
            "closed_positions": 0,
            "sharpe_ratio": None,
        }

    wins = [r for r in rows if r["realized_pnl"] > 0]
    losses = [r for r in rows if r["realized_pnl"] <= 0]
    win_rate = len(wins) / total_trades * 100.0
    total_pnl = sum(r["realized_pnl"] for r in rows)
    avg_pnl = total_pnl / total_trades
    gross_profit = sum(r["realized_pnl"] for r in wins) if wins else 0.0
    gross_loss = abs(sum(r["realized_pnl"] for r in losses)) if losses else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    expectancy = avg_pnl  # per-trade expectancy in USDT

    # Average hold time
    hold_hours_list = []
    for r in rows:
        try:
            opened = datetime.strptime(
                r["opened_at"].replace("Z", ""), "%Y-%m-%d %H:%M:%S"
            )
            closed_str = r["closed_at"] or r["opened_at"]
            closed = datetime.strptime(
                closed_str.replace("Z", ""), "%Y-%m-%d %H:%M:%S"
            )
            hold_hours_list.append((closed - opened).total_seconds() / 3600.0)
        except Exception:
            pass
    avg_hold = sum(hold_hours_list) / len(hold_hours_list) if hold_hours_list else 0.0

    sharpe = compute_sharpe_ratio()

    return {
        "total_trades": total_trades,
        "win_rate": round(win_rate, 2),
        "total_realized_pnl": round(total_pnl, 2),
        "avg_trade_pnl": round(avg_pnl, 2),
        "profit_factor": round(profit_factor, 2),
        "expectancy": round(expectancy, 2),
        "avg_hold_hours": round(avg_hold, 1),
        "open_positions": open_count,
        "closed_positions": total_trades,
        "sharpe_ratio": sharpe,
    }


# ── Trades endpoint helper ───────────────────────────────────────────────

def get_paper_trades(limit: int = 100) -> List[Dict]:
    """Return closed paper positions as a flat trade list.

    Maps ``paper_positions WHERE status != 'OPEN'`` into the trade
    shape expected by the dashboard.
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT symbol, direction, entry_price, current_price AS exit_price, "
            "realized_pnl, opened_at, closed_at, status "
            "FROM paper_positions WHERE status != 'OPEN' "
            "ORDER BY closed_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()

        return [
            {
                "symbol": r[0],
                "direction": r[1],
                "entry_price": r[2],
                "exit_price": r[3],
                "realized_pnl": r[4],
                "opened_at": r[5],
                "closed_at": r[6],
                "status": r[7],
            }
            for r in rows
        ]
    finally:
        conn.close()
