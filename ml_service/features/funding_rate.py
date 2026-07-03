"""Funding rate features for crypto trading (Binance Futures specific)."""

import pandas as pd
import numpy as np
import requests
from typing import Optional

from ml_service.utils.logger import get_logger

logger = get_logger()


def fetch_funding_rate_history(symbol: str, limit: int = 1000) -> Optional[pd.DataFrame]:
    """
    Fetch funding rate history from Binance Futures API.

    Args:
        symbol: Trading symbol (e.g., BTCUSDT)
        limit: Number of records to fetch (max 1000)

    Returns:
        DataFrame with timestamp and fundingRate columns, or None if failed
    """
    try:
        url = "https://fapi.binance.com/fapi/v1/fundingRate"
        params = {"symbol": symbol, "limit": limit}

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()

            if len(data) > 0:
                df = pd.DataFrame(data)
                df['fundingTime'] = pd.to_datetime(df['fundingTime'], unit='ms')
                df['fundingRate'] = df['fundingRate'].astype(float)

                logger.info(f"Fetched {len(df)} funding rate records for {symbol}")
                return df[['fundingTime', 'fundingRate']]

        logger.warning(f"Failed to fetch funding rates for {symbol}: HTTP {response.status_code}")
        return None

    except Exception as e:
        logger.warning(f"Error fetching funding rates for {symbol}: {e}")
        return None


def add_funding_rate_features(
    df: pd.DataFrame,
    symbol: str,
    ma_period: int = 8,
    extreme_threshold: float = 0.0001,
) -> pd.DataFrame:
    """
    Add funding rate features to DataFrame.

    Funding rate interpretation:
    - Positive rate: Longs pay shorts (bearish pressure, too many longs)
    - Negative rate: Shorts pay longs (bullish pressure, too many shorts)
    - Extreme values (>0.01% or <-0.01%) indicate overcrowding

    Args:
        df: DataFrame with OHLCV data and timestamp
        symbol: Trading symbol
        ma_period: Moving average period for funding rate
        extreme_threshold: Threshold for extreme funding rate (0.0001 = 0.01%)

    Returns:
        DataFrame with funding rate features added
    """
    df = df.copy()

    # Try to fetch funding rate data
    funding_df = fetch_funding_rate_history(symbol, limit=1000)

    if funding_df is None or len(funding_df) == 0:
        # Fallback: use neutral values (0.0) so pipeline doesn't break
        logger.warning(f"Using neutral funding rate values for {symbol}")
        df['funding_rate'] = 0.0
        df['funding_rate_ma'] = 0.0
        df['funding_extreme'] = 0
        df['funding_sentiment'] = 0
        return df

    # Merge funding rate data with OHLCV data based on timestamp
    if 'timestamp' in df.columns:
        df['timestamp_dt'] = pd.to_datetime(df['timestamp'], unit='ms')

        # Merge on nearest timestamp (funding rates are published every 8 hours)
        df = pd.merge_asof(
            df.sort_values('timestamp_dt'),
            funding_df.rename(columns={'fundingTime': 'timestamp_dt'}),
            on='timestamp_dt',
            direction='backward'
        )

        df = df.drop(columns=['timestamp_dt'])

        # Fill any remaining NaN with 0.0 (neutral)
        df['fundingRate'] = df['fundingRate'].fillna(0.0)
        df = df.rename(columns={'fundingRate': 'funding_rate'})
    else:
        # No timestamp column, use neutral values
        df['funding_rate'] = 0.0

    # Calculate moving average of funding rate
    df['funding_rate_ma'] = df['funding_rate'].rolling(window=ma_period, min_periods=1).mean()

    # Identify extreme funding rates (potential reversals)
    df['funding_extreme'] = 0
    df.loc[df['funding_rate'].abs() > extreme_threshold, 'funding_extreme'] = 1

    # Funding sentiment: -1 (bearish), 0 (neutral), 1 (bullish)
    df['funding_sentiment'] = 0
    df.loc[df['funding_rate'] > extreme_threshold / 2, 'funding_sentiment'] = -1  # Positive rate = bearish
    df.loc[df['funding_rate'] < -extreme_threshold / 2, 'funding_sentiment'] = 1  # Negative rate = bullish

    return df
