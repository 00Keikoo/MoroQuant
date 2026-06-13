"""Data ingestion from Binance Futures and Yahoo Finance."""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import requests
import yfinance as yf
import pandas as pd

from ..utils.logger import get_logger
from ..utils.config import get_config
from .database import get_database

logger = get_logger()


BINANCE_FUTURES_BASE = "https://fapi.binance.com"
TIMEFRAME_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}

YFINANCE_INTERVAL_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}

ETF_TO_FUTURES_MAP = {
    "SPY": "ES_proxy",
    "QQQ": "NQ_proxy",
    "GLD": "GC_proxy",
    "USO": "CL_proxy",
    "TLT": "ZB_proxy",
}


def fetch_binance_klines(
    symbol: str,
    timeframe: str,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    limit: int = 1500,
) -> List[Dict]:
    """
    Fetch OHLCV data from Binance Futures public API.

    Args:
        symbol: Trading pair (e.g., BTCUSDT)
        timeframe: Candle interval (1m, 5m, 15m, 1h, 4h, 1d)
        start_time: Start timestamp in milliseconds
        end_time: End timestamp in milliseconds
        limit: Max candles per request (max 1500)

    Returns:
        List of OHLCV dictionaries
    """
    url = f"{BINANCE_FUTURES_BASE}/fapi/v1/klines"
    params = {
        "symbol": symbol,
        "interval": TIMEFRAME_MAP[timeframe],
        "limit": limit,
    }

    if start_time:
        params["startTime"] = start_time
    if end_time:
        params["endTime"] = end_time

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        candles = []
        for candle in data:
            candles.append({
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": candle[0],
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "volume": float(candle[5]),
            })

        return candles

    except Exception as e:
        logger.error(f"Error fetching Binance data for {symbol}: {e}")
        return []


def fetch_yfinance_data(
    symbol: str,
    timeframe: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[Dict]:
    """
    Fetch OHLCV data from Yahoo Finance.

    Args:
        symbol: Ticker symbol (e.g., SPY)
        timeframe: Candle interval
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        List of OHLCV dictionaries with mapped symbol names
    """
    try:
        ticker = yf.Ticker(symbol)
        interval = YFINANCE_INTERVAL_MAP.get(timeframe, "1d")

        df = ticker.history(
            start=start_date,
            end=end_date,
            interval=interval,
        )

        if df.empty:
            logger.warning(f"No data returned from yfinance for {symbol}")
            return []

        mapped_symbol = ETF_TO_FUTURES_MAP.get(symbol, f"{symbol}_proxy")

        candles = []
        for idx, row in df.iterrows():
            timestamp = int(idx.timestamp() * 1000)
            candles.append({
                "symbol": mapped_symbol,
                "timeframe": timeframe,
                "timestamp": timestamp,
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": float(row["Volume"]),
            })

        return candles

    except Exception as e:
        logger.error(f"Error fetching yfinance data for {symbol}: {e}")
        return []


def get_last_timestamp(symbol: str, timeframe: str) -> Optional[int]:
    """Get the most recent timestamp for a symbol/timeframe from DB."""
    db = get_database()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MAX(timestamp) FROM ohlcv WHERE symbol = ? AND timeframe = ?",
            (symbol, timeframe),
        )
        result = cursor.fetchone()
        return result[0] if result[0] else None


def insert_candles(candles: List[Dict]) -> Tuple[int, int]:
    """
    Insert candles into database, skipping duplicates.

    Returns:
        Tuple of (inserted_count, skipped_count)
    """
    if not candles:
        return 0, 0

    db = get_database()
    inserted = 0
    skipped = 0

    with db.get_connection() as conn:
        cursor = conn.cursor()

        for candle in candles:
            try:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO ohlcv (symbol, timeframe, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        candle["symbol"],
                        candle["timeframe"],
                        candle["timestamp"],
                        candle["open"],
                        candle["high"],
                        candle["low"],
                        candle["close"],
                        candle["volume"],
                    ),
                )
                if cursor.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1
            except Exception:
                skipped += 1

    return inserted, skipped


def ingest_binance_symbol(
    symbol: str,
    timeframe: str,
    days_back: int = 30,
    fetch_from_beginning: bool = False,
) -> Tuple[int, int]:
    """
    Ingest historical data for a Binance symbol.

    Args:
        symbol: Trading pair (e.g., BTCUSDT)
        timeframe: Candle interval
        days_back: How many days of history to fetch
        fetch_from_beginning: If True, fetch from (current_time - days_back) regardless of DB state

    Returns:
        Tuple of (inserted_count, skipped_count)
    """
    logger.info(f"Ingesting Binance {symbol} {timeframe} (last {days_back} days)")

    if fetch_from_beginning:
        start_time = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)
        logger.info(f"Fetching full history from {days_back} days ago (timestamp {start_time})")
    else:
        last_ts = get_last_timestamp(symbol, timeframe)
        if last_ts:
            start_time = last_ts + 1
            logger.info(f"Resuming from timestamp {start_time}")
        else:
            start_time = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)

    end_time = int(datetime.now().timestamp() * 1000)

    all_candles = []
    current_start = start_time

    while current_start < end_time:
        candles = fetch_binance_klines(
            symbol=symbol,
            timeframe=timeframe,
            start_time=current_start,
            end_time=end_time,
            limit=1500,
        )

        if not candles:
            break

        all_candles.extend(candles)
        current_start = candles[-1]["timestamp"] + 1

        if len(candles) < 1500:
            break

        time.sleep(0.1)

    inserted, skipped = insert_candles(all_candles)
    logger.info(f"Binance {symbol} {timeframe}: {inserted} inserted, {skipped} skipped")

    return inserted, skipped


def ingest_yfinance_symbol(
    symbol: str,
    timeframe: str,
    days_back: int = 30,
) -> Tuple[int, int]:
    """
    Ingest historical data for a Yahoo Finance symbol.

    Args:
        symbol: Ticker symbol (e.g., SPY)
        timeframe: Candle interval
        days_back: How many days of history to fetch

    Returns:
        Tuple of (inserted_count, skipped_count)
    """
    mapped_symbol = ETF_TO_FUTURES_MAP.get(symbol, f"{symbol}_proxy")
    logger.info(f"Ingesting yfinance {symbol} -> {mapped_symbol} {timeframe} (last {days_back} days)")

    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    candles = fetch_yfinance_data(
        symbol=symbol,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
    )

    inserted, skipped = insert_candles(candles)
    logger.info(f"yfinance {symbol} {timeframe}: {inserted} inserted, {skipped} skipped")

    return inserted, skipped


def fetch_all(days_back: int = 30) -> Dict[str, Dict]:
    """
    Fetch data for all configured symbols and timeframes.

    Args:
        days_back: How many days of history to fetch

    Returns:
        Dictionary with ingestion statistics
    """
    config = get_config()
    stats = {"binance": {}, "yfinance": {}}

    if config.data_sources.binance.enabled:
        logger.info("Starting Binance ingestion")
        for symbol in config.data_sources.binance.symbols:
            stats["binance"][symbol] = {}
            for timeframe in config.timeframes:
                try:
                    inserted, skipped = ingest_binance_symbol(
                        symbol=symbol,
                        timeframe=timeframe,
                        days_back=days_back,
                    )
                    stats["binance"][symbol][timeframe] = {
                        "inserted": inserted,
                        "skipped": skipped,
                    }
                except Exception as e:
                    logger.error(f"Failed to ingest Binance {symbol} {timeframe}: {e}")
                    stats["binance"][symbol][timeframe] = {"error": str(e)}

    if config.data_sources.yfinance.enabled:
        logger.info("Starting yfinance ingestion")
        for symbol in config.data_sources.yfinance.symbols:
            stats["yfinance"][symbol] = {}
            for timeframe in config.timeframes:
                try:
                    inserted, skipped = ingest_yfinance_symbol(
                        symbol=symbol,
                        timeframe=timeframe,
                        days_back=days_back,
                    )
                    stats["yfinance"][symbol][timeframe] = {
                        "inserted": inserted,
                        "skipped": skipped,
                    }
                except Exception as e:
                    logger.error(f"Failed to ingest yfinance {symbol} {timeframe}: {e}")
                    stats["yfinance"][symbol][timeframe] = {"error": str(e)}

    return stats
