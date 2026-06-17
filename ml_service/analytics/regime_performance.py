"""Regime-based performance analytics for live trading."""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml_service.data.database import get_database
from ml_service.utils.logger import get_logger

logger = get_logger()


REGIME_LABELS = {
    'trending': 'Trending',
    'ranging': 'Ranging',
    'choppy_low_vol': 'Choppy Low Vol',
    'high_volatility': 'High Volatility',
    'unknown': 'Unknown'
}


def compute_regime_performance(
    symbol: Optional[str] = None,
    days_back: Optional[int] = None
) -> Dict:
    """
    Compute performance metrics grouped by market regime.

    Args:
        symbol: Filter by symbol (None = all symbols)
        days_back: Look back period in days (None = all time)

    Returns:
        Dictionary with regime-based performance breakdown
    """
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()

        query = """
            SELECT
                market_regime,
                realized_pnl,
                commission,
                matched_signal_id,
                confidence_at_entry
            FROM user_trade_history
            WHERE matched_signal_id IS NOT NULL
        """
        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        if days_back:
            cutoff_ts = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)
            query += " AND trade_time >= ?"
            params.append(cutoff_ts)

        cursor.execute(query, params)
        trades = cursor.fetchall()

    if not trades:
        return {
            "status": "no_data",
            "message": "No trades with matched signals found",
            "regimes": {}
        }

    regime_data = {}

    for trade in trades:
        market_regime, realized_pnl, commission, signal_id, confidence = trade
        regime = market_regime or 'unknown'

        if regime not in regime_data:
            regime_data[regime] = []

        net_pnl = realized_pnl - commission
        regime_data[regime].append(net_pnl)

    regime_metrics = {}

    for regime, pnls in regime_data.items():
        pnls_arr = np.array(pnls)

        total_trades = len(pnls)
        winning_trades = int(np.sum(pnls_arr > 0))
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        total_pnl = float(np.sum(pnls_arr))
        avg_pnl = float(np.mean(pnls_arr))

        gross_profit = float(np.sum(pnls_arr[pnls_arr > 0])) if np.any(pnls_arr > 0) else 0
        gross_loss = abs(float(np.sum(pnls_arr[pnls_arr < 0]))) if np.any(pnls_arr < 0) else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

        avg_win = float(np.mean(pnls_arr[pnls_arr > 0])) if np.any(pnls_arr > 0) else 0
        avg_loss = float(np.mean(pnls_arr[pnls_arr < 0])) if np.any(pnls_arr < 0) else 0
        win_rate_decimal = win_rate / 100
        expectancy = (win_rate_decimal * avg_win) - ((1 - win_rate_decimal) * abs(avg_loss))

        regime_metrics[regime] = {
            "regime_label": REGIME_LABELS.get(regime, regime),
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": total_trades - winning_trades,
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(avg_pnl, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else "inf",
            "expectancy": round(expectancy, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
        }

    sorted_regimes = sorted(
        regime_metrics.items(),
        key=lambda x: x[1]['total_trades'],
        reverse=True
    )

    return {
        "status": "success",
        "symbol": symbol or "all",
        "period_days": days_back or "all_time",
        "regimes": dict(sorted_regimes),
        "timestamp": datetime.now().isoformat()
    }


def get_regime_distribution(
    symbol: Optional[str] = None,
    days_back: Optional[int] = None
) -> Dict:
    """
    Get distribution of trades across market regimes.

    Args:
        symbol: Filter by symbol
        days_back: Look back period in days

    Returns:
        Dictionary with regime distribution
    """
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()

        query = """
            SELECT market_regime, COUNT(*) as count
            FROM user_trade_history
            WHERE matched_signal_id IS NOT NULL
        """
        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        if days_back:
            cutoff_ts = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)
            query += " AND trade_time >= ?"
            params.append(cutoff_ts)

        query += " GROUP BY market_regime"

        cursor.execute(query, params)
        results = cursor.fetchall()

    distribution = {}
    total = 0

    for regime, count in results:
        regime_key = regime or 'unknown'
        distribution[regime_key] = {
            "regime_label": REGIME_LABELS.get(regime_key, regime_key),
            "count": count
        }
        total += count

    for regime_key in distribution:
        distribution[regime_key]["percentage"] = round(
            (distribution[regime_key]["count"] / total * 100) if total > 0 else 0,
            2
        )

    return {
        "status": "success",
        "total_trades": total,
        "distribution": distribution,
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    metrics = compute_regime_performance()
    print("\nRegime Performance Metrics:")
    print("=" * 80)
    print(f"Status: {metrics['status']}")

    if metrics['status'] == 'success':
        for regime, data in metrics['regimes'].items():
            print(f"\n{data['regime_label']} ({regime}):")
            print(f"  Trades: {data['total_trades']}")
            print(f"  Win Rate: {data['win_rate']}%")
            print(f"  Profit Factor: {data['profit_factor']}")
            print(f"  Expectancy: {data['expectancy']}")
    else:
        print(metrics['message'])
