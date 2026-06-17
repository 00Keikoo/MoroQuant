"""Live performance metrics computation from real Binance trades."""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml_service.data.database import get_database
from ml_service.utils.logger import get_logger

logger = get_logger()


def compute_live_metrics(
    symbol: Optional[str] = None,
    days_back: Optional[int] = None
) -> Dict:
    """
    Compute live trading performance metrics from synced Binance trades.

    Args:
        symbol: Filter by symbol (None = all symbols)
        days_back: Look back period in days (None = all time)

    Returns:
        Dictionary with performance metrics
    """
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Build query with optional filters
        query = """
            SELECT
                symbol,
                side,
                realized_pnl,
                commission,
                trade_time,
                matched_signal_id,
                market_regime,
                confidence_at_entry
            FROM user_trade_history
            WHERE 1=1
        """
        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        if days_back:
            cutoff_ts = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)
            query += " AND trade_time >= ?"
            params.append(cutoff_ts)

        query += " ORDER BY trade_time ASC"

        cursor.execute(query, params)
        trades = cursor.fetchall()

    if not trades:
        return {
            "status": "no_data",
            "message": "No trades found matching criteria",
            "metrics": {}
        }

    # Extract data
    pnls = []
    trade_times = []
    sides = []

    for trade in trades:
        symbol_val, side, realized_pnl, commission, trade_time, signal_id, regime, confidence = trade
        net_pnl = realized_pnl - commission
        pnls.append(net_pnl)
        trade_times.append(trade_time)
        sides.append(side)

    pnls_arr = np.array(pnls)

    # Basic metrics
    total_trades = len(pnls)
    winning_trades = np.sum(pnls_arr > 0)
    losing_trades = np.sum(pnls_arr < 0)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    total_pnl = float(np.sum(pnls_arr))
    avg_pnl = float(np.mean(pnls_arr))

    # Profit factor
    gross_profit = float(np.sum(pnls_arr[pnls_arr > 0])) if np.any(pnls_arr > 0) else 0
    gross_loss = abs(float(np.sum(pnls_arr[pnls_arr < 0]))) if np.any(pnls_arr < 0) else 0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

    # Expectancy
    avg_win = float(np.mean(pnls_arr[pnls_arr > 0])) if np.any(pnls_arr > 0) else 0
    avg_loss = float(np.mean(pnls_arr[pnls_arr < 0])) if np.any(pnls_arr < 0) else 0
    win_rate_decimal = win_rate / 100
    expectancy = (win_rate_decimal * avg_win) - ((1 - win_rate_decimal) * abs(avg_loss))

    # Hold time analysis (approximate from trade timestamps)
    hold_times_hours = []
    if len(trade_times) > 1:
        for i in range(1, len(trade_times)):
            if sides[i] != sides[i-1]:  # Opposite side = position close
                hold_duration_ms = trade_times[i] - trade_times[i-1]
                hold_duration_hours = hold_duration_ms / (1000 * 3600)
                hold_times_hours.append(hold_duration_hours)

    avg_hold_time_hours = float(np.mean(hold_times_hours)) if hold_times_hours else None

    # Sharpe ratio (approximate using PnL returns)
    if len(pnls_arr) > 1:
        returns_std = float(np.std(pnls_arr))
        if returns_std > 0:
            sharpe_ratio = (avg_pnl / returns_std) * np.sqrt(252)  # Annualized
        else:
            sharpe_ratio = 0.0
    else:
        sharpe_ratio = None

    # Max drawdown (based on cumulative PnL)
    cumulative_pnl = np.cumsum(pnls_arr)
    running_max = np.maximum.accumulate(cumulative_pnl)
    drawdowns = running_max - cumulative_pnl
    max_drawdown = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0

    # Peak drawdown percentage
    max_drawdown_pct = (max_drawdown / running_max[np.argmax(drawdowns)] * 100) if np.max(running_max) > 0 else 0

    metrics = {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": round(win_rate, 2),
        "total_pnl": round(total_pnl, 2),
        "avg_pnl": round(avg_pnl, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else "inf",
        "expectancy": round(expectancy, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "sharpe_ratio": round(sharpe_ratio, 2) if sharpe_ratio is not None else None,
        "max_drawdown": round(max_drawdown, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "avg_hold_time_hours": round(avg_hold_time_hours, 2) if avg_hold_time_hours else None,
    }

    return {
        "status": "success",
        "symbol": symbol or "all",
        "period_days": days_back or "all_time",
        "metrics": metrics,
        "timestamp": datetime.now().isoformat()
    }


def get_equity_curve(
    symbol: Optional[str] = None,
    days_back: Optional[int] = None
) -> List[Dict]:
    """
    Generate equity curve from trade history.

    Args:
        symbol: Filter by symbol
        days_back: Look back period in days

    Returns:
        List of equity curve points [{timestamp, cumulative_pnl, trade_count}]
    """
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()

        query = """
            SELECT trade_time, realized_pnl, commission
            FROM user_trade_history
            WHERE 1=1
        """
        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        if days_back:
            cutoff_ts = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)
            query += " AND trade_time >= ?"
            params.append(cutoff_ts)

        query += " ORDER BY trade_time ASC"

        cursor.execute(query, params)
        trades = cursor.fetchall()

    if not trades:
        return []

    equity_curve = []
    cumulative_pnl = 0
    trade_count = 0

    for trade in trades:
        trade_time, realized_pnl, commission = trade
        net_pnl = realized_pnl - commission
        cumulative_pnl += net_pnl
        trade_count += 1

        equity_curve.append({
            "timestamp": trade_time,
            "cumulative_pnl": round(cumulative_pnl, 2),
            "trade_count": trade_count,
            "trade_pnl": round(net_pnl, 2)
        })

    return equity_curve


if __name__ == "__main__":
    # Test with sample data
    metrics = compute_live_metrics()
    print("\nLive Trading Metrics:")
    print("=" * 60)
    print(f"Status: {metrics['status']}")
    if metrics['status'] == 'success':
        for key, value in metrics['metrics'].items():
            print(f"{key}: {value}")
    else:
        print(metrics['message'])
