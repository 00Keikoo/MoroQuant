"""Confidence-based performance analytics for live trading."""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml_service.data.database import get_database
from ml_service.utils.logger import get_logger

logger = get_logger()


CONFIDENCE_BUCKETS = [
    (50, 60, "50-60%"),
    (60, 70, "60-70%"),
    (70, 80, "70-80%"),
    (80, 90, "80-90%"),
    (90, 101, "90%+"),
]


def compute_confidence_performance(
    symbol: Optional[str] = None,
    days_back: Optional[int] = None
) -> Dict:
    """
    Compute performance metrics grouped by confidence buckets.

    Operates on CLOSED POSITIONS (aggregated fills), not raw fills, so
    that confidence buckets align with the equity curve granularity.

    Args:
        symbol: Filter by symbol (None = all symbols)
        days_back: Look back period in days (None = all time)

    Returns:
        Dictionary with confidence-based performance breakdown
    """
    from ml_service.analytics.live_metrics import aggregate_closed_positions, _fetch_fills
    db = get_database()

    with db.get_connection() as conn:
        fills = _fetch_fills(conn, symbol=symbol, days_back=days_back)

    positions = aggregate_closed_positions(fills) if fills else []
    matched_positions = [
        p for p in positions
        if p['matched_signal_id'] is not None and p['confidence_at_entry'] is not None
    ]

    if not matched_positions:
        return {
            "status": "no_data",
            "message": "No trades with confidence data found",
            "confidence_buckets": {}
        }

    bucket_data = {bucket[2]: [] for bucket in CONFIDENCE_BUCKETS}

    for pos in matched_positions:
        confidence = pos['confidence_at_entry']

        for min_conf, max_conf, label in CONFIDENCE_BUCKETS:
            if min_conf <= confidence < max_conf:
                bucket_data[label].append(pos['net_pnl'])
                break

    confidence_metrics = {}

    for label, pnls in bucket_data.items():
        if not pnls:
            confidence_metrics[label] = {
                "bucket": label,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_pnl": 0,
                "expectancy": 0,
            }
            continue

        pnls_arr = np.array(pnls)

        total_trades = len(pnls)
        winning_trades = int(np.sum(pnls_arr > 0))
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        total_pnl = float(np.sum(pnls_arr))
        avg_pnl = float(np.mean(pnls_arr))

        avg_win = float(np.mean(pnls_arr[pnls_arr > 0])) if np.any(pnls_arr > 0) else 0
        avg_loss = float(np.mean(pnls_arr[pnls_arr < 0])) if np.any(pnls_arr < 0) else 0
        win_rate_decimal = win_rate / 100
        expectancy = (win_rate_decimal * avg_win) - ((1 - win_rate_decimal) * abs(avg_loss))

        confidence_metrics[label] = {
            "bucket": label,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": total_trades - winning_trades,
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(avg_pnl, 2),
            "expectancy": round(expectancy, 2),
        }

    sorted_buckets = sorted(
        confidence_metrics.items(),
        key=lambda x: int(x[0].split('-')[0].replace('%', '').replace('+', ''))
    )

    return {
        "status": "success",
        "symbol": symbol or "all",
        "period_days": days_back or "all_time",
        "confidence_buckets": dict(sorted_buckets),
        "timestamp": datetime.now().isoformat()
    }


def analyze_confidence_correlation(
    symbol: Optional[str] = None,
    days_back: Optional[int] = None
) -> Dict:
    """
    Analyze correlation between signal confidence and trade outcomes.

    Operates on CLOSED POSITIONS (aggregated fills).

    Args:
        symbol: Filter by symbol
        days_back: Look back period in days

    Returns:
        Dictionary with correlation analysis
    """
    from ml_service.analytics.live_metrics import aggregate_closed_positions, _fetch_fills
    db = get_database()

    with db.get_connection() as conn:
        fills = _fetch_fills(conn, symbol=symbol, days_back=days_back)

    positions = aggregate_closed_positions(fills) if fills else []
    matched_positions = [
        p for p in positions
        if p['matched_signal_id'] is not None and p['confidence_at_entry'] is not None
    ]

    if len(matched_positions) < 2:
        return {
            "status": "insufficient_data",
            "message": "Need at least 2 closed positions for correlation analysis"
        }

    confidences = [p['confidence_at_entry'] for p in matched_positions]
    pnls = [p['net_pnl'] for p in matched_positions]

    confidences_arr = np.array(confidences)
    pnls_arr = np.array(pnls)

    correlation = float(np.corrcoef(confidences_arr, pnls_arr)[0, 1])

    high_conf_threshold = 75
    high_conf_mask = confidences_arr >= high_conf_threshold
    low_conf_mask = confidences_arr < high_conf_threshold

    high_conf_win_rate = (np.sum(pnls_arr[high_conf_mask] > 0) / np.sum(high_conf_mask) * 100) if np.any(high_conf_mask) else 0
    low_conf_win_rate = (np.sum(pnls_arr[low_conf_mask] > 0) / np.sum(low_conf_mask) * 100) if np.any(low_conf_mask) else 0

    high_conf_avg_pnl = float(np.mean(pnls_arr[high_conf_mask])) if np.any(high_conf_mask) else 0
    low_conf_avg_pnl = float(np.mean(pnls_arr[low_conf_mask])) if np.any(low_conf_mask) else 0

    return {
        "status": "success",
        "correlation": round(correlation, 3),
        "interpretation": _interpret_correlation(correlation),
        "high_confidence_threshold": high_conf_threshold,
        "high_confidence": {
            "trades": int(np.sum(high_conf_mask)),
            "win_rate": round(high_conf_win_rate, 2),
            "avg_pnl": round(high_conf_avg_pnl, 2),
        },
        "low_confidence": {
            "trades": int(np.sum(low_conf_mask)),
            "win_rate": round(low_conf_win_rate, 2),
            "avg_pnl": round(low_conf_avg_pnl, 2),
        },
        "timestamp": datetime.now().isoformat()
    }


def _interpret_correlation(corr: float) -> str:
    """Interpret correlation coefficient."""
    abs_corr = abs(corr)

    if abs_corr < 0.1:
        strength = "negligible"
    elif abs_corr < 0.3:
        strength = "weak"
    elif abs_corr < 0.5:
        strength = "moderate"
    elif abs_corr < 0.7:
        strength = "strong"
    else:
        strength = "very strong"

    direction = "positive" if corr > 0 else "negative"

    return f"{strength} {direction} correlation"


if __name__ == "__main__":
    metrics = compute_confidence_performance()
    print("\nConfidence Performance Metrics:")
    print("=" * 80)
    print(f"Status: {metrics['status']}")

    if metrics['status'] == 'success':
        for bucket, data in metrics['confidence_buckets'].items():
            print(f"\n{bucket}:")
            print(f"  Trades: {data['total_trades']}")
            print(f"  Win Rate: {data['win_rate']}%")
            print(f"  Expectancy: {data['expectancy']}")
            print(f"  Total PnL: {data['total_pnl']}")
    else:
        print(metrics['message'])
