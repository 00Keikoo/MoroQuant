"""Exchange integration for syncing trade history and monitoring open positions."""

import hmac
import hashlib
import time
import requests
from typing import Dict, List, Optional, Set
from datetime import datetime
import json

from utils.logger import get_logger
from utils.config import get_config
from data.database import get_database

logger = get_logger()

BINANCE_FUTURES_BASE_URL = "https://fapi.binance.com"

# Symbols known to have been traded — extended on every sync via
# open positions and /fapi/v2/account endpoint.
_KNOWN_SYMBOLS: Set[str] = set()


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


def _discover_traded_symbols(api_key: str, api_secret: str) -> List[str]:
    """Return the list of symbols that have any trade history.

    Pulls symbols from open positions AND from the account endpoint's
    position list (which includes positions with non-zero accumulated qty
    even if currently zero).
    """
    symbols: Set[str] = set()

    # 1. Open positions
    positions = fetch_open_positions(api_key, api_secret)
    if positions:
        for p in positions:
            symbols.add(p['symbol'])

    # 2. Account positions (includes recently closed)
    acct = _signed_request('/fapi/v2/account', {}, api_key, api_secret)
    if acct and isinstance(acct, dict) and 'positions' in acct:
        for p in acct['positions']:
            amt = abs(float(p.get('positionAmt', 0)))
            entry = float(p.get('entryPrice', 0))
            # Include any symbol that has ever held a position
            if amt > 0 or entry > 0:
                symbols.add(p['symbol'])

    # 3. Merge with config symbols (covers symbols traded before account
    #    positions were opened under this API key)
    try:
        config = get_config()
        for sym in config.data_sources.binance.symbols:
            symbols.add(sym)
    except Exception:
        pass

    result = sorted(symbols)
    logger.info(f"Trade-sync symbol list: {result}")
    return result


def _get_watermark(symbol: Optional[str] = None) -> int:
    """Return max trade_time from DB as the startTime watermark.

    If symbol is given, use only that symbol's max; otherwise use the
    global max across all symbols.
    """
    db = get_database()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        if symbol:
            cursor.execute(
                "SELECT MAX(trade_time) FROM user_trade_history WHERE symbol = ?",
                (symbol,)
            )
        else:
            cursor.execute("SELECT MAX(trade_time) FROM user_trade_history")
        row = cursor.fetchone()
        return int(row[0]) if row and row[0] else 0


def fetch_user_trades_for_symbol(
    api_key: str,
    api_secret: str,
    symbol: str,
    start_time: Optional[int] = None,
    limit: int = 1000
) -> Optional[List[Dict]]:
    """
    Fetch user trade history from Binance Futures for a SINGLE symbol.

    The /fapi/v1/userTrades endpoint requires `symbol` as a mandatory
    parameter for USD-M Futures.  `limit` is per-symbol (max 1000).

    Returns a list of raw Binance trade dicts, or None on error.
    """
    params = {'symbol': symbol, 'limit': limit}
    if start_time:
        params['startTime'] = start_time

    trades = _signed_request('/fapi/v1/userTrades', params, api_key, api_secret)

    if trades and isinstance(trades, list):
        logger.info(
            f"Fetched {len(trades)} trades for {symbol} "
            f"(startTime={start_time})"
        )
        return trades

    # Binance returns {"code": -1102, ...} on error
    if trades and isinstance(trades, dict) and 'code' in trades:
        logger.error(
            f"Binance API error for {symbol}: "
            f"{trades.get('code')} {trades.get('msg')}"
        )

    return None


# Legacy name kept for backward compatibility with CLI / tests.
# Now delegates to sync_all_trades.
def fetch_user_trades(
    api_key: str,
    api_secret: str,
    symbol: Optional[str] = None,
    start_time: Optional[int] = None,
    limit: int = 1000
) -> Optional[List[Dict]]:
    """Fetch trades from Binance Futures.

    If *symbol* is given, fetches that symbol only (for backward compat).
    Otherwise, discovers all traded symbols and fetches each.
    """
    if symbol:
        result = fetch_user_trades_for_symbol(
            api_key, api_secret, symbol, start_time, limit
        )
        return result

    # No symbol provided — do a full multi-symbol sync.
    all_trades = sync_all_trades(api_key, api_secret)
    return all_trades


def sync_all_trades(
    api_key: str,
    api_secret: str,
) -> List[Dict]:
    """Sync trades across all known symbols, paginating with startTime.

    Returns the combined list of all fetched trade dicts.
    """
    global _KNOWN_SYMBOLS
    if _KNOWN_SYMBOLS:
        symbols = sorted(_KNOWN_SYMBOLS)
    else:
        symbols = _discover_traded_symbols(api_key, api_secret)
        _KNOWN_SYMBOLS = set(symbols)

    all_trades: List[Dict] = []

    for symbol in symbols:
        # Per-symbol watermark: fetch only fills newer than what we have.
        watermark = _get_watermark(symbol)

        # Safety: subtract a small overlap window (1 min) to catch fills
        # that arrived in the same millisecond as the watermark.
        effective_start = max(0, watermark - 60_000) if watermark else None

        page = fetch_user_trades_for_symbol(
            api_key, api_secret, symbol,
            start_time=effective_start,
            limit=1000,
        )
        if page:
            all_trades.extend(page)

            # Binance returns newest-first; if we got a full page (1000)
            # we may need to paginate backwards.  Check the oldest fill.
            if len(page) == 1000:
                oldest_time = min(int(t['time']) for t in page)
                if effective_start is None or oldest_time > effective_start:
                    logger.info(
                        f"  {symbol}: full page received, paginating further back"
                    )
                    earlier = fetch_user_trades_for_symbol(
                        api_key, api_secret, symbol,
                        start_time=max(0, oldest_time - 60_000),
                        limit=1000,
                    )
                    if earlier:
                        all_trades.extend(earlier)

    logger.info(f"Total fetched across all symbols: {len(all_trades)} fills")
    return all_trades


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

    Uses INSERT OR IGNORE on order_id for deduplication.

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
            SELECT id, symbol, side, realized_pnl, trade_time
            FROM user_trade_history
            WHERE matched_signal_id IS NULL
            """
        )

        unmatched_trades = cursor.fetchall()
        matched = 0

        for trade_id, symbol, side, realized_pnl, trade_time in unmatched_trades:
            best_signal = None
            best_confidence = -1

            # 1. Try parent entry match for exit trades (realized_pnl != 0)
            if realized_pnl != 0:
                cursor.execute(
                    """
                    SELECT matched_signal_id, market_regime, confidence_at_entry
                    FROM user_trade_history
                    WHERE symbol = ?
                      AND trade_time < ?
                      AND matched_signal_id IS NOT NULL
                    ORDER BY trade_time DESC
                    LIMIT 1
                    """,
                    (symbol, trade_time)
                )
                parent = cursor.fetchone()
                if parent and parent[0] is not None:
                    parent_signal_id, parent_regime, parent_confidence = parent
                    cursor.execute(
                        """
                        UPDATE user_trade_history
                        SET matched_signal_id = ?,
                            market_regime = ?,
                            confidence_at_entry = ?
                        WHERE id = ?
                        """,
                        (parent_signal_id, parent_regime, parent_confidence, trade_id)
                    )
                    matched += 1
                    continue

            # 2. Try strict match (same symbol, same direction, within window)
            trade_direction = 'long' if side == 'BUY' else 'short'
            for timeframe, window_ms in timeframe_windows.items():
                time_window_start = trade_time - window_ms
                time_window_end = trade_time + window_ms

                cursor.execute(
                    """
                    SELECT id, direction, confidence, features_json, timeframe, regime
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
                    signal_id, direction, confidence, features_json, sig_timeframe, signal_regime = signal
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_signal = signal

            # 3. Try relaxed match (same symbol, ignoring direction, within window)
            if not best_signal:
                for timeframe, window_ms in timeframe_windows.items():
                    time_window_start = trade_time - window_ms
                    time_window_end = trade_time + window_ms

                    cursor.execute(
                        """
                        SELECT id, direction, confidence, features_json, timeframe, regime
                        FROM signals
                        WHERE symbol = ?
                          AND timeframe = ?
                          AND direction != 'neutral'
                          AND timestamp >= ?
                          AND timestamp <= ?
                        ORDER BY ABS(timestamp - ?) ASC
                        LIMIT 1
                        """,
                        (symbol, timeframe, time_window_start, time_window_end, trade_time)
                    )
                    signal = cursor.fetchone()
                    if signal:
                        signal_id, direction, confidence, features_json, sig_timeframe, signal_regime = signal
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_signal = signal

            if best_signal:
                signal_id, direction, confidence, features_json, sig_timeframe, signal_regime = best_signal

                # Use the signals.regime column (authoritative), falling back
                # to features_json only if column is NULL.
                market_regime = signal_regime if signal_regime else 'unknown'

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


def backfill_regimes():
    """Backfill market_regime for all trades that already have a matched_signal_id.

    Reads the authoritative regime from the ``signals.regime`` column and
    writes it to ``user_trade_history.market_regime`` for every row where
    ``matched_signal_id IS NOT NULL`` but ``market_regime`` is still NULL or
    ``'unknown'``.  This is a one-shot repair — safe to re-run idempotently.
    """
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # 1. Count how many rows need backfill.
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM user_trade_history
            WHERE matched_signal_id IS NOT NULL
              AND (market_regime IS NULL OR market_regime = 'unknown')
            """
        )
        need_backfill = cursor.fetchone()[0]

        if need_backfill == 0:
            logger.info("Regime backfill: all matched trades already have regimes")
            return 0

        logger.info(f"Regime backfill: {need_backfill} trades need regime update")

        # 2. Mass-update via a single UPDATE…FROM query (SQLite supported).
        cursor.execute(
            """
            UPDATE user_trade_history
            SET market_regime = (
                SELECT COALESCE(s.regime, 'unknown')
                FROM signals s
                WHERE s.id = user_trade_history.matched_signal_id
            )
            WHERE matched_signal_id IS NOT NULL
              AND (market_regime IS NULL OR market_regime = 'unknown')
              AND EXISTS (
                SELECT 1 FROM signals s
                WHERE s.id = user_trade_history.matched_signal_id
                  AND s.regime IS NOT NULL
                  AND s.regime != ''
              )
            """
        )
        updated = cursor.rowcount

        # 3. For trades whose signal has NO regime column value either,
        #    explicitly set 'unknown' so they are not retried endlessly.
        cursor.execute(
            """
            UPDATE user_trade_history
            SET market_regime = 'unknown'
            WHERE matched_signal_id IS NOT NULL
              AND (market_regime IS NULL OR market_regime = 'unknown')
            """
        )
        finalized = cursor.rowcount

        conn.commit()

    logger.info(
        f"Regime backfill complete: {updated} updated from signals, "
        f"{finalized} finalized as 'unknown'"
    )
    return updated + finalized


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


def get_account_equity() -> Dict:
    """Fetch real account equity from Binance Futures.

    Calls ``GET /fapi/v2/account`` and extracts wallet-level balances.
    Returns a dict with ``source: 'binance'`` on success, or
    ``source: 'unavailable'`` with null balances on any failure (never raises).

    Field mapping (Binance → our schema):
        totalWalletBalance  → wallet_balance
        totalUnrealizedProfit → unrealized_pnl
        totalMarginBalance  → margin_balance
        availableBalance     → available_balance
    """
    api_key, api_secret = _load_exchange_credentials()
    if not api_key or not api_secret:
        logger.warning("get_account_equity: Binance credentials not configured")
        return {
            "wallet_balance": None,
            "unrealized_pnl": None,
            "margin_balance": None,
            "available_balance": None,
            "source": "unavailable",
            "reason": "credentials_missing",
        }

    try:
        account = _signed_request('/fapi/v2/account', {}, api_key, api_secret)
    except Exception as e:
        logger.error(f"get_account_equity: request failed: {e}")
        return {
            "wallet_balance": None,
            "unrealized_pnl": None,
            "margin_balance": None,
            "available_balance": None,
            "source": "unavailable",
            "reason": "request_error",
        }

    if not account or not isinstance(account, dict):
        logger.warning("get_account_equity: Binance returned empty or non-dict response")
        return {
            "wallet_balance": None,
            "unrealized_pnl": None,
            "margin_balance": None,
            "available_balance": None,
            "source": "unavailable",
            "reason": "empty_response",
        }

    # Binance error responses contain a "code" field.
    if 'code' in account:
        logger.error(
            f"get_account_equity: Binance API error: "
            f"{account.get('code')} {account.get('msg')}"
        )
        return {
            "wallet_balance": None,
            "unrealized_pnl": None,
            "margin_balance": None,
            "available_balance": None,
            "source": "unavailable",
            "reason": "api_error",
        }

    try:
        wallet_balance = float(account.get('totalWalletBalance', 0))
        unrealized_pnl = float(account.get('totalUnrealizedProfit', 0))
        margin_balance = float(account.get('totalMarginBalance', 0))
        available_balance = float(account.get('availableBalance', 0))

        logger.info(
            f"get_account_equity: wallet={wallet_balance:.2f} "
            f"unrealized={unrealized_pnl:.2f} margin={margin_balance:.2f} "
            f"available={available_balance:.2f}"
        )

        return {
            "wallet_balance": round(wallet_balance, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "margin_balance": round(margin_balance, 2),
            "available_balance": round(available_balance, 2),
            "source": "binance",
        }
    except (ValueError, TypeError) as e:
        logger.error(f"get_account_equity: failed to parse balances: {e}")
        return {
            "wallet_balance": None,
            "unrealized_pnl": None,
            "margin_balance": None,
            "available_balance": None,
            "source": "unavailable",
            "reason": "parse_error",
        }


def _load_exchange_credentials() -> tuple:
    """Load Binance API credentials from config.

    Returns (api_key, api_secret) tuple — either may be None.
    """
    try:
        config = get_config()
        # Try exchange_sync section first (preferred for signed endpoints).
        if hasattr(config, 'exchange_sync'):
            key = getattr(config.exchange_sync, 'binance_api_key', None)
            secret = getattr(config.exchange_sync, 'binance_api_secret', None)
            if key and secret:
                return key, secret
        # Fallback to data_sources.binance.
        if hasattr(config, 'data_sources'):
            key = getattr(config.data_sources.binance, 'api_key', None)
            secret = getattr(config.data_sources.binance, 'api_secret', None)
            if key and secret:
                return key, secret
    except Exception as e:
        logger.debug(f"Could not load exchange credentials from config: {e}")
    return None, None


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
