"""Read-only performance summary utilities.

Thin query layer over the pre-computed `model_performance_summary` table.
The summary is auto-maintained by OutcomeEngine._refresh_performance_summary()
on every final outcome save, so these functions are O(rows in summary) rather
than O(rows in signal_outcomes).

Three scopes are exposed:
  - get_model_performance(symbol, timeframe): one (symbol, timeframe) pair
  - get_symbol_performance(symbol):           all timeframes for a symbol
  - get_global_performance():                 all (symbol, timeframe) pairs aggregated
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, List

from ml_service.utils.logger import get_logger

logger = get_logger()


def _default_db_path() -> Path:
    return Path(__file__).parent.parent / "storage" / "database.db"


def _get_connection(db_path: str = None):
    conn = sqlite3.connect(db_path or _default_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row) -> Optional[Dict]:
    if row is None:
        return None

    win_rate = row['win_rate']
    profit_factor_proxy = row['profit_factor_proxy']
    avg_holding_hours = row['avg_holding_hours']

    return {
        'symbol': row['symbol'],
        'timeframe': row['timeframe'],
        'wins': row['wins'],
        'losses': row['losses'],
        'timeouts': row['timeouts'],
        'total_signals': row['total_signals'],
        'win_rate': round(win_rate, 4) if win_rate is not None else None,
        'profit_factor_proxy': round(profit_factor_proxy, 4) if profit_factor_proxy is not None else None,
        'avg_holding_hours': round(avg_holding_hours, 2) if avg_holding_hours is not None else None,
        'updated_at': row['updated_at'],
    }


def get_model_performance(
    symbol: str,
    timeframe: str,
    db_path: str = None
) -> Optional[Dict]:
    """Get the performance summary for a single (symbol, timeframe) pair.

    Args:
        symbol: Trading symbol (e.g. 'BTCUSDT')
        timeframe: Timeframe string (e.g. '1h', '4h')

    Returns:
        Dict with summary fields, or None if no summary row exists.
    """
    conn = _get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT symbol, timeframe, wins, losses, timeouts, total_signals,
               win_rate, profit_factor_proxy, avg_holding_hours, updated_at
        FROM model_performance_summary
        WHERE symbol = ? AND timeframe = ?
    """, (symbol, timeframe))

    row = cursor.fetchone()
    conn.close()

    return _row_to_dict(row)


def get_symbol_performance(
    symbol: str,
    db_path: str = None
) -> List[Dict]:
    """Get performance summaries for every timeframe of a given symbol.

    Args:
        symbol: Trading symbol

    Returns:
        List of per-timeframe summary dicts (empty if none exist).
    """
    conn = _get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT symbol, timeframe, wins, losses, timeouts, total_signals,
               win_rate, profit_factor_proxy, avg_holding_hours, updated_at
        FROM model_performance_summary
        WHERE symbol = ?
        ORDER BY timeframe ASC
    """, (symbol,))

    rows = cursor.fetchall()
    conn.close()

    return [_row_to_dict(r) for r in rows]


def get_global_performance(db_path: str = None) -> Dict:
    """Aggregate all (symbol, timeframe) summaries into one global view.

    Aggregation rules:
      - wins/losses/timeouts/total: simple sums
      - win_rate: sum(wins) / sum(wins + losses) over all pairs
      - profit_factor_proxy: sum(gross_win_distance) / sum(gross_loss_distance),
        recomputed from signal_outcomes because the per-row proxies can't be
        meaningfully summed directly (different price scales across symbols).
      - avg_holding_hours: average of per-pair avg_holding_hours, weighted
        by each pair's resolved-signal count.

    Returns:
        Dict with the same field shape as a single pair summary, plus a
        `pairs` list of per-(symbol, timeframe) breakdowns.
    """
    conn = _get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            SUM(wins)        AS wins,
            SUM(losses)      AS losses,
            SUM(timeouts)    AS timeouts,
            SUM(total_signals) AS total_signals
        FROM model_performance_summary
    """)

    agg = cursor.fetchone()
    wins = agg['wins'] or 0
    losses = agg['losses'] or 0
    timeouts = agg['timeouts'] or 0
    total = agg['total_signals'] or 0

    decided = wins + losses
    win_rate = (wins / decided) if decided > 0 else None

    # Recompute the global profit-factor proxy from raw signal_outcomes
    # so cross-symbol price scales are handled correctly.
    cursor.execute("""
        SELECT
            SUM(CASE WHEN outcome = 'win'
                     THEN ABS(take_profit - entry_price)
                     ELSE 0 END) AS gross_win_distance,
            SUM(CASE WHEN outcome = 'loss'
                     THEN ABS(entry_price - stop_loss)
                     ELSE 0 END) AS gross_loss_distance
        FROM signal_outcomes
        WHERE outcome IN ('win', 'loss')
    """)

    pf_row = cursor.fetchone()
    gross_win = pf_row['gross_win_distance'] or 0.0
    gross_loss = pf_row['gross_loss_distance'] or 0.0
    profit_factor_proxy = (gross_win / gross_loss) if gross_loss > 0 else None

    # Weighted average holding hours across pairs.
    cursor.execute("""
        SELECT
            SUM(avg_holding_hours * (wins + losses)) AS weighted_sum,
            SUM(wins + losses) AS weight_total
        FROM model_performance_summary
        WHERE avg_holding_hours IS NOT NULL
    """)

    hold_row = cursor.fetchone()
    if hold_row['weight_total'] and hold_row['weight_total'] > 0:
        avg_holding_hours = hold_row['weighted_sum'] / hold_row['weight_total']
    else:
        avg_holding_hours = None

    # Per-pair breakdown for context.
    cursor.execute("""
        SELECT symbol, timeframe, wins, losses, timeouts, total_signals,
               win_rate, profit_factor_proxy, avg_holding_hours, updated_at
        FROM model_performance_summary
        ORDER BY symbol ASC, timeframe ASC
    """)

    pairs = [_row_to_dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        'symbol': 'ALL',
        'timeframe': 'ALL',
        'wins': wins,
        'losses': losses,
        'timeouts': timeouts,
        'total_signals': total,
        'win_rate': round(win_rate, 4) if win_rate is not None else None,
        'profit_factor_proxy': round(profit_factor_proxy, 4) if profit_factor_proxy is not None else None,
        'avg_holding_hours': round(avg_holding_hours, 2) if avg_holding_hours is not None else None,
        'pairs': pairs,
    }
