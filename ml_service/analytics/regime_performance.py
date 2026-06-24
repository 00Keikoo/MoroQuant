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
    'trending_normal_vol': 'Trending Normal Vol',
    'trending_high_vol': 'Trending High Vol',
    'transitioning_normal_vol': 'Transitioning',
    'transitioning_high_vol': 'Transitioning High Vol',
    'ranging_normal_vol': 'Ranging',
    'ranging_low_vol': 'Ranging Low Vol',
    'choppy_normal_vol': 'Choppy Normal Vol',
    'choppy_low_vol': 'Choppy Low Vol',
    'high_volatility': 'High Volatility',
    'trending': 'Trending',
    'ranging': 'Ranging',
    'unknown': 'Unknown',
}


def compute_regime_performance(
    symbol: Optional[str] = None,
    days_back: Optional[int] = None
) -> Dict:
    """
    Compute performance metrics grouped by market regime.

    Operates on CLOSED POSITIONS (aggregated fills), not raw fills, so
    that regime buckets align with the equity curve granularity.

    Args:
        symbol: Filter by symbol (None = all symbols)
        days_back: Look back period in days (None = all time)

    Returns:
        Dictionary with regime-based performance breakdown
    """
    from ml_service.analytics.live_metrics import aggregate_closed_positions, _fetch_fills
    db = get_database()

    with db.get_connection() as conn:
        fills = _fetch_fills(conn, symbol=symbol, days_back=days_back)

    if not fills:
        return {
            "status": "no_data",
            "message": "No trades with matched signals found",
            "regimes": {}
        }

    positions = aggregate_closed_positions(fills)
    # Only count positions with a matched signal for attribution accuracy.
    matched_positions = [p for p in positions if p['matched_signal_id'] is not None]

    if not matched_positions:
        return {
            "status": "no_data",
            "message": "No closed positions with matched signals found",
            "regimes": {}
        }

    regime_data = {}

    for pos in matched_positions:
        regime = pos['market_regime'] or 'unknown'
        regime_data.setdefault(regime, []).append(pos['net_pnl'])

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
    Get distribution of CLOSED POSITIONS across market regimes.

    Args:
        symbol: Filter by symbol
        days_back: Look back period in days

    Returns:
        Dictionary with regime distribution
    """
    from ml_service.analytics.live_metrics import aggregate_closed_positions, _fetch_fills
    db = get_database()

    with db.get_connection() as conn:
        fills = _fetch_fills(conn, symbol=symbol, days_back=days_back)

    positions = aggregate_closed_positions(fills) if fills else []
    matched_positions = [p for p in positions if p['matched_signal_id'] is not None]

    distribution = {}
    total = 0

    for pos in matched_positions:
        regime_key = pos['market_regime'] or 'unknown'
        if regime_key not in distribution:
            distribution[regime_key] = {
                "regime_label": REGIME_LABELS.get(regime_key, regime_key),
                "count": 0
            }
        distribution[regime_key]["count"] += 1
        total += 1

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
