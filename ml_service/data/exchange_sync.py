"""Exchange integration for syncing trade history and monitoring open positions."""

import hmac
import hashlib
import time
import requests
from typing import Dict, List, Optional
from datetime import datetime
import json

from ..utils.logger import get_logger
from ..utils.config import get_config
from .database import get_database

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
    Links trades to signals within 1 hour window for analysis.
    """
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, symbol, trade_time
            FROM user_trade_history
            WHERE matched_signal_id IS NULL
            """
        )

        unmatched_trades = cursor.fetchall()
        matched = 0

        for trade_id, symbol, trade_time in unmatched_trades:
            time_window_start = trade_time - (3600 * 1000)
            time_window_end = trade_time + (3600 * 1000)

            cursor.execute(
                """
                SELECT id, direction, confidence, features_json
                FROM signals
                WHERE symbol = ?
                  AND timestamp >= ?
                  AND timestamp <= ?
                ORDER BY ABS(timestamp - ?) ASC
                LIMIT 1
                """,
                (symbol, time_window_start, time_window_end, trade_time)
            )

            signal = cursor.fetchone()

            if signal:
                signal_id, direction, confidence, features_json = signal

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
    from ..models.predictor import generate_signal

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
