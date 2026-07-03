"""Read-only confidence analytics utilities.

Thin query layer over the pre-computed `model_confidence_stats` table.
The table is auto-maintained by OutcomeEngine._refresh_confidence_stats()
on every final outcome save, so these functions are O(buckets) rather than
O(rows in signal_outcomes).

Two accessors are exposed:
  - get_confidence_stats(symbol?, timeframe?):            raw per-bucket rows
  - get_confidence_bucket_performance(symbol?, timeframe?): derived view
    with calibration gap analysis (confidence midpoint vs actual win rate)

Buckets use the platform-wide convention: '80-100', '60-79', '40-59', '0-39'.
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, List

from ml_service.utils.logger import get_logger

logger = get_logger()


# Midpoint confidence per bucket label, used for calibration-gap analysis.
# Represents the center of each bucket's confidence range (0-100 scale).
_BUCKET_MIDPOINT = {
    '80-100': 90.0,
    '60-79': 69.5,
    '40-59': 49.5,
    '0-39': 19.5,
}


def _default_db_path() -> Path:
    return Path(__file__).parent.parent / "storage" / "database.db"


def _get_connection(db_path: str = None):
    conn = sqlite3.connect(db_path or _default_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row) -> Optional[Dict]:
    if row is None:
        return None

    actual_win_rate = row['actual_win_rate']

    return {
        'symbol': row['symbol'],
        'timeframe': row['timeframe'],
        'confidence_bucket': row['confidence_bucket'],
        'signal_count': row['signal_count'],
        'wins': row['wins'],
        'losses': row['losses'],
        'timeouts': row['timeouts'],
        # actual_win_rate is stored as a 0..1 fraction; expose it rounded.
        'actual_win_rate': round(actual_win_rate, 4) if actual_win_rate is not None else None,
        'updated_at': row['updated_at'],
    }


def get_confidence_stats(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    db_path: str = None
) -> List[Dict]:
    """Get raw confidence-bucket statistics rows.

    Args:
        symbol: Optional filter (None = all symbols)
        timeframe: Optional filter (None = all timeframes)

    Returns:
        List of per-(symbol, timeframe, bucket) stat dicts, ordered by
        symbol, timeframe, then bucket descending (highest confidence first).
        Empty list if no data matches the filter.
    """
    conn = _get_connection(db_path)
    cursor = conn.cursor()

    where_clauses = []
    params = []

    if symbol:
        where_clauses.append("symbol = ?")
        params.append(symbol)
    if timeframe:
        where_clauses.append("timeframe = ?")
        params.append(timeframe)

    where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    # Order buckets highest-confidence first for natural reading.
    cursor.execute(f"""
        SELECT symbol, timeframe, confidence_bucket,
               signal_count, wins, losses, timeouts,
               actual_win_rate, updated_at
        FROM model_confidence_stats
        {where_clause}
        ORDER BY symbol ASC, timeframe ASC,
                 CASE confidence_bucket
                     WHEN '80-100' THEN 0
                     WHEN '60-79'  THEN 1
                     WHEN '40-59'  THEN 2
                     WHEN '0-39'   THEN 3
                     ELSE 4
                 END ASC
    """, params)

    rows = cursor.fetchall()
    conn.close()

    return [_row_to_dict(r) for r in rows]


def get_confidence_bucket_performance(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    db_path: str = None
) -> Dict:
    """Get a derived confidence-vs-accuracy view with calibration gap analysis.

    For each bucket present, derives:
      - confidence_midpoint: nominal confidence (0-100) the bucket represents
      - actual_win_rate_pct: actual win rate (0-100) observed
      - calibration_gap: confidence_midpoint - actual_win_rate_pct
        (positive => model is overconfident in this bucket;
         negative => model is under-confident)
      - share_of_signals: this bucket's signal_count / total across all buckets

    Also returns aggregate totals across all buckets.

    Args:
        symbol: Optional filter (None = all symbols)
        timeframe: Optional filter (None = all timeframes)

    Returns:
        Dict with keys:
          - buckets: list of per-bucket derived dicts (highest confidence first)
          - totals: aggregate counts across the returned buckets
          - filters: echo of the symbol/timeframe filters applied
    """
    rows = get_confidence_stats(symbol=symbol, timeframe=timeframe, db_path=db_path)

    total_signals = sum(r['signal_count'] for r in rows)
    total_wins = sum(r['wins'] for r in rows)
    total_losses = sum(r['losses'] for r in rows)
    total_timeouts = sum(r['timeouts'] for r in rows)

    decided_total = total_wins + total_losses
    overall_actual_win_rate = (total_wins / decided_total) if decided_total > 0 else None

    buckets = []
    for r in rows:
        bucket = r['confidence_bucket']
        midpoint = _BUCKET_MIDPOINT.get(bucket)
        actual_pct = (r['actual_win_rate'] * 100.0) if r['actual_win_rate'] is not None else None

        calibration_gap = None
        if midpoint is not None and actual_pct is not None:
            calibration_gap = round(midpoint - actual_pct, 2)

        share = (r['signal_count'] / total_signals) if total_signals > 0 else 0.0

        buckets.append({
            'symbol': r['symbol'],
            'timeframe': r['timeframe'],
            'confidence_bucket': bucket,
            'confidence_midpoint': midpoint,
            'signal_count': r['signal_count'],
            'wins': r['wins'],
            'losses': r['losses'],
            'timeouts': r['timeouts'],
            'actual_win_rate': r['actual_win_rate'],
            'actual_win_rate_pct': round(actual_pct, 2) if actual_pct is not None else None,
            'calibration_gap': calibration_gap,
            'share_of_signals': round(share, 4),
        })

    return {
        'buckets': buckets,
        'totals': {
            'signal_count': total_signals,
            'wins': total_wins,
            'losses': total_losses,
            'timeouts': total_timeouts,
            'actual_win_rate': round(overall_actual_win_rate, 4) if overall_actual_win_rate is not None else None,
        },
        'filters': {
            'symbol': symbol,
            'timeframe': timeframe,
        },
    }
