"""Market State Service for real-time price updates.

Provides live market prices for paper trading positions.
Abstracts price fetching so dashboard doesn't care about the source.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ml_service.utils.logger import get_logger

logger = get_logger()

_DB_PATH: Path = Path(__file__).parent.parent / "storage" / "database.db"


def _get_connection():
    """Get a database connection with Row factory."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _fetch_price(symbol: str) -> Optional[float]:
    """Fetch live market price for a symbol."""
    try:
        from ml_service.services.crypto_price_service import get_crypto_service
        svc = get_crypto_service()
        data = svc.get_price(symbol)
        if data and data.get("price") is not None:
            return float(data["price"])
    except Exception as e:
        logger.debug(f"crypto price fetch failed for {symbol}: {e}")

    try:
        from ml_service.services.proxy_price_service import get_proxy_service
        svc = get_proxy_service()
        data = svc.get_price(symbol)
        if data and data.get("price") is not None:
            return float(data["price"])
    except Exception as e:
        logger.debug(f"proxy price fetch failed for {symbol}: {e}")

    return None


def _compute_floating_pnl(entry_price: float, current_price: float,
                          qty: float, direction: str) -> float:
    """Compute floating PnL for an open position."""
    if direction == "LONG":
        pnl = (current_price - entry_price) * qty
    else:  # SHORT
        pnl = (entry_price - current_price) * qty
    return pnl


def get_live_open_positions() -> List[Dict]:
    """Get open positions with live mark prices and floating PnL."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT id, symbol, direction, entry_price, qty, size_usdt, opened_at, "
            "confidence, regime, stop_loss, take_profit "
            "FROM paper_positions WHERE status = 'OPEN'"
        ).fetchall()
    finally:
        conn.close()

    positions = []
    for row in rows:
        symbol = row["symbol"]
        direction = row["direction"]
        entry_price = row["entry_price"]
        qty = row["qty"]

        mark_price = _fetch_price(symbol)
        if mark_price is None:
            mark_price = entry_price

        floating_pnl = _compute_floating_pnl(entry_price, mark_price, qty, direction)
        roi_pct = (floating_pnl / row["size_usdt"] * 100) if row["size_usdt"] > 0 else 0.0

        opened_at = datetime.strptime(row["opened_at"].replace("Z", ""), "%Y-%m-%d %H:%M:%S")
        duration_hours = (datetime.now() - opened_at).total_seconds() / 3600.0

        positions.append({
            "id": row["id"],
            "symbol": symbol,
            "direction": direction,
            "entry_price": round(entry_price, 8),
            "mark_price": round(mark_price, 8),
            "qty": qty,
            "size_usdt": row["size_usdt"],
            "floating_pnl": round(floating_pnl, 2),
            "roi_pct": round(roi_pct, 2),
            "duration_hours": round(duration_hours, 1),
            "confidence": row["confidence"],
            "regime": row["regime"],
            "stop_loss": row["stop_loss"],
            "take_profit": row["take_profit"],
            "opened_at": row["opened_at"],
        })

    return positions


def get_live_account_equity() -> Dict:
    """Get paper account with live unrealized PnL from mark prices."""
    conn = _get_connection()
    try:
        account = conn.execute(
            "SELECT balance, equity, unrealized_pnl FROM paper_account WHERE id = 1"
        ).fetchone()

        if not account:
            return {
                "balance": 10000.0,
                "equity": 10000.0,
                "unrealized_pnl": 0.0,
                "available_balance": 10000.0,
            }

        positions = get_live_open_positions()
        live_unrealized_pnl = sum(p["floating_pnl"] for p in positions)

        balance = account["balance"]
        equity = balance + live_unrealized_pnl
        available_balance = balance

        return {
            "balance": round(balance, 2),
            "equity": round(equity, 2),
            "unrealized_pnl": round(live_unrealized_pnl, 2),
            "available_balance": round(available_balance, 2),
        }
    finally:
        conn.close()
