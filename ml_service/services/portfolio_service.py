"""Portfolio Service - Single Source of Truth for Account Metrics.

Computes all portfolio-level financial metrics (equity, margin, return %,
account health) in one place. No frontend calculations.

Architecture:
    Repository → PortfolioService → API → Frontend (render only)
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from ml_service.utils.logger import get_logger

logger = get_logger()

_DB_PATH: Path = Path(__file__).parent.parent / "storage" / "database.db"


def _get_connection():
    """Get database connection with Row factory."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def get_initial_balance() -> float:
    """Get the starting balance for return calculations.

    Resolution order:
        1. Database initial_balance column (if exists)
        2. STARTING_BALANCE constant
        3. 10000.0 fallback

    Returns:
        Starting capital before any trading activity.
    """
    from ml_service.trading.paper_broker import STARTING_BALANCE

    conn = _get_connection()
    try:
        # Try to get initial_balance from database
        result = conn.execute(
            "SELECT initial_balance FROM paper_account WHERE id = 1"
        ).fetchone()

        if result and result["initial_balance"] is not None:
            return float(result["initial_balance"])
    except sqlite3.OperationalError:
        # Column doesn't exist yet
        pass
    finally:
        conn.close()

    # Fallback to constant
    return STARTING_BALANCE


def compute_paper_account_metrics() -> Dict:
    """Compute complete paper account metrics with all derived fields.

    Returns normalized account object with:
        - Core balances (initial, wallet, equity, available)
        - PnL metrics (unrealized, realized, daily)
        - Derived metrics (margin_ratio, account_health, total_return_pct)
        - Exposure and metadata

    This is the SINGLE SOURCE OF TRUTH for paper account state.
    Frontend must not compute any of these metrics.
    """
    conn = _get_connection()
    try:
        # Get account snapshot
        account = conn.execute(
            "SELECT balance, equity, unrealized_pnl, updated_at FROM paper_account WHERE id = 1"
        ).fetchone()

        if not account:
            # No account exists yet
            initial = get_initial_balance()
            return {
                "initial_balance": initial,
                "wallet_balance": initial,
                "equity": initial,
                "available_balance": initial,
                "margin_used": 0.0,
                "free_margin": initial,
                "unrealized_pnl": 0.0,
                "realized_pnl": 0.0,
                "daily_pnl": 0.0,
                "margin_ratio": 0.0,
                "account_health": 100.0,
                "total_return_pct": 0.0,
                "exposure": 0.0,
                "last_updated": datetime.now().isoformat(),
            }

        # Core balances
        initial_balance = get_initial_balance()
        wallet_balance = float(account["balance"])
        equity = float(account["equity"])
        unrealized_pnl = float(account["unrealized_pnl"])

        # Paper trading simplified: no margin system
        # Available balance = wallet balance (all funds available)
        available_balance = wallet_balance

        # Margin used = position notional values
        open_positions = conn.execute(
            "SELECT size_usdt FROM paper_positions WHERE status = 'OPEN'"
        ).fetchall()
        margin_used = sum(float(p["size_usdt"]) for p in open_positions)

        free_margin = available_balance

        # Realized PnL = wallet - initial
        realized_pnl = wallet_balance - initial_balance

        # Daily PnL (stub - requires daily snapshot tracking)
        daily_pnl = 0.0

        # Derived metrics
        margin_ratio = (margin_used / equity * 100) if equity > 0 else 0.0
        account_health = min(100.0, (free_margin / equity * 100)) if equity > 0 else 0.0
        total_return_pct = ((equity - initial_balance) / initial_balance * 100) if initial_balance > 0 else 0.0

        # Exposure = total unrealized PnL magnitude
        exposure = abs(unrealized_pnl)

        return {
            "initial_balance": round(initial_balance, 2),
            "wallet_balance": round(wallet_balance, 2),
            "equity": round(equity, 2),
            "available_balance": round(available_balance, 2),
            "margin_used": round(margin_used, 2),
            "free_margin": round(free_margin, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "realized_pnl": round(realized_pnl, 2),
            "daily_pnl": round(daily_pnl, 2),
            "margin_ratio": round(margin_ratio, 2),
            "account_health": round(account_health, 2),
            "total_return_pct": round(total_return_pct, 2),
            "exposure": round(exposure, 2),
            "last_updated": account["updated_at"] or datetime.now().isoformat(),
        }
    finally:
        conn.close()


def compute_live_account_metrics(binance_account: Dict) -> Dict:
    """Compute complete live account metrics from Binance account data.

    Args:
        binance_account: Raw account data from exchange_sync.get_account_equity()

    Returns:
        Normalized account object with all derived metrics.
    """
    # Check if Binance data is available
    if binance_account.get("source") != "binance":
        return {
            "initial_balance": None,
            "wallet_balance": None,
            "equity": None,
            "available_balance": None,
            "margin_used": None,
            "free_margin": None,
            "unrealized_pnl": None,
            "realized_pnl": None,
            "daily_pnl": None,
            "margin_ratio": None,
            "account_health": None,
            "total_return_pct": None,
            "exposure": None,
            "last_updated": datetime.now().isoformat(),
            "source": "unavailable",
        }

    # Get initial balance for LIVE mode
    from ml_service.analytics.live_metrics import get_starting_balance
    initial_balance = get_starting_balance()

    # Core balances from Binance
    wallet_balance = binance_account.get("wallet_balance", 0.0)
    unrealized_pnl = binance_account.get("unrealized_pnl", 0.0)
    equity = binance_account.get("margin_balance", 0.0)  # margin_balance = equity
    available_balance = binance_account.get("available_balance", 0.0)

    # Margin calculations
    margin_used = equity - available_balance if equity and available_balance else 0.0
    free_margin = available_balance

    # Realized PnL (requires querying trade history - stub for now)
    realized_pnl = wallet_balance - initial_balance if initial_balance else 0.0

    # Daily PnL (stub - requires daily snapshot)
    daily_pnl = 0.0

    # Derived metrics
    margin_ratio = (margin_used / equity * 100) if equity > 0 else 0.0
    account_health = min(100.0, (free_margin / equity * 100)) if equity > 0 else 0.0
    total_return_pct = ((equity - initial_balance) / initial_balance * 100) if initial_balance > 0 else 0.0

    exposure = abs(unrealized_pnl)

    return {
        "initial_balance": round(initial_balance, 2),
        "wallet_balance": round(wallet_balance, 2),
        "equity": round(equity, 2),
        "available_balance": round(available_balance, 2),
        "margin_used": round(margin_used, 2),
        "free_margin": round(free_margin, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "realized_pnl": round(realized_pnl, 2),
        "daily_pnl": round(daily_pnl, 2),
        "margin_ratio": round(margin_ratio, 2),
        "account_health": round(account_health, 2),
        "total_return_pct": round(total_return_pct, 2),
        "exposure": round(exposure, 2),
        "last_updated": datetime.now().isoformat(),
        "source": "binance",
    }


def compute_position_risk_reward(
    entry_price: float,
    stop_loss: Optional[float],
    take_profit: Optional[float],
    direction: str
) -> Dict:
    """Compute risk/reward metrics for a position.

    Args:
        entry_price: Entry price
        stop_loss: Stop loss price (None if not set)
        take_profit: Take profit price (None if not set)
        direction: LONG or SHORT

    Returns:
        Dict with risk, reward, risk_reward fields (None if not computable)
    """
    null_result = {
        "risk": None,
        "reward": None,
        "risk_reward": None,
    }

    if not stop_loss or not take_profit:
        return null_result

    try:
        entry = float(entry_price)
        sl = float(stop_loss)
        tp = float(take_profit)

        if entry <= 0 or sl <= 0 or tp <= 0:
            return null_result

        if not all(map(lambda x: x == x, [entry, sl, tp])):
            return null_result

        if direction == "LONG":
            risk = entry - sl
            reward = tp - entry
        elif direction == "SHORT":
            risk = sl - entry
            reward = entry - tp
        else:
            return null_result

        if risk <= 0 or reward <= 0:
            return null_result

        risk_reward = reward / risk

        return {
            "risk": round(risk, 8),
            "reward": round(reward, 8),
            "risk_reward": round(risk_reward, 2),
        }
    except (ValueError, ZeroDivisionError, TypeError, AttributeError):
        return null_result
