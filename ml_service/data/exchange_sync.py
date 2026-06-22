"""Exchange integration for syncing trade history and monitoring open positions."""

import hmac
import hashlib
import time
import requests
from typing import Dict, List, Optional
from datetime import datetime
import json

from utils.logger import get_logger
from utils.config import get_config
from data.database import get_database

logger = get_logger()

BINANCE_FUTURES_BASE_URL = "https://fapi.binance.com"


def _create_signature(query_string: str, api_secret: str) -> str:
    """Create HMAC SHA256 signature for Binance API."""
    return hmac.new(
        api_secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def _signed_request(endpoint: str, params: Dict, api_key: str, api_secret: str) -> Optional[Dict]:
    """Make a signed request to Binance Futures API."""
    params['timestamp'] = int(time.time() * 1000)
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = _create_signature(query_string, api_secret)
    query_string += f"&signature={signature}"

    url = f"{BINANCE_FUTURES_BASE_URL}{endpoint}?{query_string}"
    headers = {'X-MBX-APIKEY': api_key}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Binance API request failed: {e}")
        return None


def fetch_user_trades(
    api_key: str,
    api_secret: str,
    symbol: Optional[str] = None,
    start_time: Optional[int] = None,
    limit: int = 1000
) -> Optional[List[Dict]]:
    """
    Fetch user trade history from Binance Futures.

    Args:
        api_key: Binance API key (read-only)
        api_secret: Binance API secret
        symbol: Trading symbol (optional, fetches all if None)
        start_time: Start timestamp in milliseconds
        limit: Number of trades to fetch (max 1000)

    Returns:
        List of trade dicts or None on error
    """
    params = {'limit': limit}
    if symbol:
        params['symbol'] = symbol
    if start_time:
        params['startTime'] = start_time

    trades = _signed_request('/fapi/v1/userTrades', params, api_key, api_secret)

    if trades:
        logger.info(f"Fetched {len(trades)} trades from Binance Futures")

    return trades


def fetch_open_positions(api_key: str, api_secret: str) -> Optional[List[Dict]]:
    """
    Fetch open positions from Binance Futures.

    Args:
        api_key: Binance API key (read-only)
        api_secret: Binance API secret

    Returns:
        List of position dicts or None on error
    """
    positions = _signed_request('/fapi/v2/positionRisk', {}, api_key, api_secret)

    if positions:
        open_positions = [p for p in positions if float(p['positionAmt']) != 0]
        logger.info(f"Fetched {len(open_positions)} open positions from Binance Futures")
        return open_positions

    return None


def save_trades_to_db(trades: List[Dict]) -> int:
    """
    Save user trades to database.

    Args:
        trades: List of trade dicts from Binance API

    Returns:
        Number of new trades inserted
    """
    db = get_database()
    inserted = 0

    with db.get_connection() as conn:
        cursor = conn.cursor()

        for trade in trades:
            try:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO user_trade_history (
                        symbol, side, price, qty, realized_pnl, commission,
                        trade_time, order_id, synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trade['symbol'],
                        trade['side'],
                        float(trade['price']),
                        float(trade['qty']),
                        float(trade['realizedPnl']),
                        float(trade['commission']),
                        int(trade['time']),
                        str(trade['orderId']),
                        datetime.now().isoformat(),
                    )
                )
                if cursor.rowcount > 0:
                    inserted += 1
            except Exception as e:
                logger.error(f"Error inserting trade {trade.get('orderId')}: {e}")

        conn.commit()

    logger.info(f"Inserted {inserted} new trades into database")
    return inserted


def enrich_trades_with_signals():
    """
    Match user trades with ML signals from the signals table.

    Matching criteria:
    - Symbol must match
    - Direction must match (BUY=long, SELL=short)
    - Neutral signals are ignored
    - Timeframe-aware windows: 1h = ±90min, 4h = ±4h
    - Highest confidence signal selected when multiple candidates exist
    """
    db = get_database()

    timeframe_windows = {
        '1h': 90 * 60 * 1000,   # ±90 minutes in milliseconds
        '4h': 4 * 60 * 60 * 1000,  # ±4 hours in milliseconds
    }

    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, symbol, side, trade_time
            FROM user_trade_history
            WHERE matched_signal_id IS NULL
            """
        )

        unmatched_trades = cursor.fetchall()
        matched = 0

        for trade_id, symbol, side, trade_time in unmatched_trades:
            # Convert trade side to signal direction
            trade_direction = 'long' if side == 'BUY' else 'short'

            best_signal = None
            best_confidence = -1

            # Check each timeframe with its specific window
            for timeframe, window_ms in timeframe_windows.items():
                time_window_start = trade_time - window_ms
                time_window_end = trade_time + window_ms

                cursor.execute(
                    """
                    SELECT id, direction, confidence, features_json, timeframe
                    FROM signals
                    WHERE symbol = ?
                      AND timeframe = ?
                      AND direction = ?
                      AND direction != 'neutral'
                      AND timestamp >= ?
                      AND timestamp <= ?
                    ORDER BY confidence DESC, ABS(timestamp - ?) ASC
                    LIMIT 1
                    """,
                    (symbol, timeframe, trade_direction, time_window_start, time_window_end, trade_time)
                )

                signal = cursor.fetchone()

                if signal:
                    signal_id, direction, confidence, features_json, sig_timeframe = signal

                    # Keep the highest confidence signal across all timeframes
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_signal = signal

            if best_signal:
                signal_id, direction, confidence, features_json, sig_timeframe = best_signal

                try:
                    features = json.loads(features_json)
                    market_regime = features.get('market_phase', 'unknown')
                except:
                    market_regime = 'unknown'

                cursor.execute(
                    """
                    UPDATE user_trade_history
                    SET matched_signal_id = ?,
                        market_regime = ?,
                        confidence_at_entry = ?
                    WHERE id = ?
                    """,
                    (signal_id, market_regime, confidence, trade_id)
                )
                matched += 1

        conn.commit()

    logger.info(f"Enriched {matched} trades with signal data")
    return matched


def generate_attribution_report() -> Dict:
    """
    Generate comprehensive signal attribution quality report.

    Returns:
        Detailed attribution statistics including:
        - Match rate by symbol
        - Confidence distribution
        - Timeframe breakdown
        - Direction alignment
        - Performance comparison
    """
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Overall statistics
        cursor.execute("SELECT COUNT(*) FROM user_trade_history")
        total_trades = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM user_trade_history WHERE matched_signal_id IS NOT NULL")
        matched_count = cursor.fetchone()[0]

        match_rate = (matched_count / total_trades * 100) if total_trades > 0 else 0

        # Match rate by symbol
        cursor.execute(
            """
            SELECT
                symbol,
                COUNT(*) as total,
                SUM(CASE WHEN matched_signal_id IS NOT NULL THEN 1 ELSE 0 END) as matched,
                AVG(CASE WHEN matched_signal_id IS NOT NULL THEN confidence_at_entry ELSE NULL END) as avg_confidence
            FROM user_trade_history
            GROUP BY symbol
            ORDER BY total DESC
            """
        )
        symbol_stats = []
        for row in cursor.fetchall():
            symbol, total, matched, avg_conf = row
            symbol_stats.append({
                'symbol': symbol,
                'total_trades': total,
                'matched_trades': matched,
                'match_rate_pct': round((matched / total * 100) if total > 0 else 0, 1),
                'avg_confidence': round(avg_conf, 1) if avg_conf else None
            })

        # Confidence distribution
        cursor.execute(
            """
            SELECT
                CASE
                    WHEN confidence_at_entry >= 80 THEN '80-100'
                    WHEN confidence_at_entry >= 60 THEN '60-79'
                    WHEN confidence_at_entry >= 40 THEN '40-59'
                    ELSE '0-39'
                END as confidence_bucket,
                COUNT(*) as count,
                AVG(realized_pnl) as avg_pnl,
                SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins
            FROM user_trade_history
            WHERE matched_signal_id IS NOT NULL
            GROUP BY confidence_bucket
            ORDER BY confidence_bucket DESC
            """
        )
        confidence_dist = []
        for row in cursor.fetchall():
            bucket, count, avg_pnl, wins = row
            win_rate = (wins / count * 100) if count > 0 else 0
            confidence_dist.append({
                'confidence_range': bucket,
                'trade_count': count,
                'avg_pnl': round(avg_pnl, 2),
                'win_rate_pct': round(win_rate, 1)
            })

        # Performance comparison
        cursor.execute(
            """
            SELECT
                COUNT(*) as count,
                AVG(realized_pnl) as avg_pnl,
                SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(realized_pnl) as total_pnl
            FROM user_trade_history
            WHERE matched_signal_id IS NOT NULL
            """
        )
        matched_result = cursor.fetchone()
        matched_count, matched_avg_pnl, matched_wins, matched_total_pnl = matched_result
        matched_win_rate = (matched_wins / matched_count * 100) if matched_count > 0 else 0

        cursor.execute(
            """
            SELECT
                COUNT(*) as count,
                AVG(realized_pnl) as avg_pnl,
                SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(realized_pnl) as total_pnl
            FROM user_trade_history
            WHERE matched_signal_id IS NULL
            """
        )
        unmatched_result = cursor.fetchone()
        unmatched_count, unmatched_avg_pnl, unmatched_wins, unmatched_total_pnl = unmatched_result
        unmatched_win_rate = (unmatched_wins / unmatched_count * 100) if unmatched_count > 0 else 0

        cursor.execute("SELECT SUM(realized_pnl) FROM user_trade_history")
        total_pnl = cursor.fetchone()[0] or 0

    return {
        'summary': {
            'total_trades': total_trades,
            'matched_trades': matched_count,
            'unmatched_trades': total_trades - matched_count,
            'match_rate_pct': round(match_rate, 1),
            'total_pnl': round(total_pnl, 2)
        },
        'by_symbol': symbol_stats,
        'by_confidence': confidence_dist,
        'performance': {
            'matched': {
                'count': matched_count,
                'avg_pnl': round(matched_avg_pnl or 0, 2),
                'total_pnl': round(matched_total_pnl or 0, 2),
                'win_rate_pct': round(matched_win_rate, 2),
            },
            'unmatched': {
                'count': unmatched_count,
                'avg_pnl': round(unmatched_avg_pnl or 0, 2),
                'total_pnl': round(unmatched_total_pnl or 0, 2),
                'win_rate_pct': round(unmatched_win_rate, 2),
            }
        }
    }


def analyze_signal_performance() -> Dict:
    """
    Analyze performance of trades that matched vs didn't match signals.

    Returns:
        Performance statistics dict
    """
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM user_trade_history")
        total_trades = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT
                COUNT(*) as count,
                AVG(realized_pnl) as avg_pnl,
                SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins
            FROM user_trade_history
            WHERE matched_signal_id IS NOT NULL
            """
        )
        matched_result = cursor.fetchone()
        matched_count, matched_avg_pnl, matched_wins = matched_result
        matched_win_rate = (matched_wins / matched_count * 100) if matched_count > 0 else 0

        cursor.execute(
            """
            SELECT
                COUNT(*) as count,
                AVG(realized_pnl) as avg_pnl,
                SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins
            FROM user_trade_history
            WHERE matched_signal_id IS NULL
            """
        )
        unmatched_result = cursor.fetchone()
        unmatched_count, unmatched_avg_pnl, unmatched_wins = unmatched_result
        unmatched_win_rate = (unmatched_wins / unmatched_count * 100) if unmatched_count > 0 else 0

        cursor.execute("SELECT SUM(realized_pnl) FROM user_trade_history")
        total_pnl = cursor.fetchone()[0] or 0

    return {
        'total_trades': total_trades,
        'total_pnl': round(total_pnl, 2),
        'matched_signal': {
            'count': matched_count,
            'avg_pnl': round(matched_avg_pnl or 0, 2),
            'win_rate_pct': round(matched_win_rate, 2),
        },
        'unmatched_signal': {
            'count': unmatched_count,
            'avg_pnl': round(unmatched_avg_pnl or 0, 2),
            'win_rate_pct': round(unmatched_win_rate, 2),
        }
    }


def get_position_signal_comparison(positions: List[Dict]) -> List[Dict]:
    """
    Compare open positions with current ML signals.

    Args:
        positions: List of open positions from Binance

    Returns:
        List of positions with signal comparison data
    """
    from models.predictor import generate_signal

    enriched_positions = []

    for pos in positions:
        symbol = pos['symbol']
        position_amt = float(pos['positionAmt'])

        if position_amt == 0:
            continue

        position_side = 'long' if position_amt > 0 else 'short'

        signal = generate_signal(symbol=symbol, timeframe='1h')

        agreement = 'unknown'
        if signal:
            if signal['direction'] == position_side:
                agreement = 'match'
            elif signal['direction'] == 'neutral':
                agreement = 'neutral'
            else:
                agreement = 'conflict'

        enriched_positions.append({
            'symbol': symbol,
            'side': position_side,
            'entry_price': float(pos['entryPrice']),
            'mark_price': float(pos['markPrice']),
            'unrealized_pnl': float(pos['unRealizedProfit']),
            'leverage': int(pos['leverage']),
            'position_amt': abs(position_amt),
            'signal': signal,
            'agreement': agreement,
        })

    return enriched_positions
