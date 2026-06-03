"""Price action feature engineering for ML trading system."""

import pandas as pd
import numpy as np
from typing import Tuple, List


def identify_swing_points(
    df: pd.DataFrame,
    lookback: int = 10,
) -> pd.DataFrame:
    """
    Identify swing highs and lows using local extrema.

    Args:
        df: DataFrame with OHLCV data
        lookback: Number of candles to look back/forward for pivot detection

    Returns:
        DataFrame with swing_high and swing_low columns (1/0)
    """
    df = df.copy()
    df['swing_high'] = 0
    df['swing_low'] = 0

    for i in range(lookback, len(df) - lookback):
        # Swing high: current high is highest in lookback window
        window_highs = df['high'].iloc[i-lookback:i+lookback+1]
        if df['high'].iloc[i] == window_highs.max():
            df.loc[df.index[i], 'swing_high'] = 1

        # Swing low: current low is lowest in lookback window
        window_lows = df['low'].iloc[i-lookback:i+lookback+1]
        if df['low'].iloc[i] == window_lows.min():
            df.loc[df.index[i], 'swing_low'] = 1

    return df


def detect_trend_structure(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect trend structure using swing points (HH/HL for uptrend, LH/LL for downtrend).

    Args:
        df: DataFrame with swing_high and swing_low columns

    Returns:
        DataFrame with trend column (1=uptrend, -1=downtrend, 0=neutral)
    """
    df = df.copy()
    df['trend'] = 0

    # Get swing high and low prices
    swing_highs = df[df['swing_high'] == 1]['high'].values
    swing_lows = df[df['swing_low'] == 1]['low'].values

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return df

    # Check last 2 swing highs and lows for trend
    for i in range(len(df)):
        # Get swing points up to current index
        past_highs = df[df['swing_high'] == 1]['high'].iloc[:i]
        past_lows = df[df['swing_low'] == 1]['low'].iloc[:i]

        if len(past_highs) >= 2 and len(past_lows) >= 2:
            # Higher highs and higher lows = uptrend
            if past_highs.iloc[-1] > past_highs.iloc[-2] and past_lows.iloc[-1] > past_lows.iloc[-2]:
                df.loc[df.index[i], 'trend'] = 1
            # Lower highs and lower lows = downtrend
            elif past_highs.iloc[-1] < past_highs.iloc[-2] and past_lows.iloc[-1] < past_lows.iloc[-2]:
                df.loc[df.index[i], 'trend'] = -1

    return df


def find_support_resistance(
    df: pd.DataFrame,
    window: int = 50,
    tolerance: float = 0.02,
) -> pd.DataFrame:
    """
    Find support and resistance zones based on price reversals.

    Args:
        df: DataFrame with OHLCV data
        window: Lookback window for finding levels
        tolerance: Price tolerance for grouping levels (2% default)

    Returns:
        DataFrame with nearest_support and nearest_resistance columns
    """
    df = df.copy()
    df['nearest_support'] = np.nan
    df['nearest_resistance'] = np.nan

    for i in range(window, len(df)):
        window_data = df.iloc[i-window:i]
        current_price = df['close'].iloc[i]

        # Find swing points in window
        swing_highs = window_data[window_data['swing_high'] == 1]['high'].values
        swing_lows = window_data[window_data['swing_low'] == 1]['low'].values

        # Find nearest support (swing low below current price)
        supports = swing_lows[swing_lows < current_price]
        if len(supports) > 0:
            df.loc[df.index[i], 'nearest_support'] = supports[-1]

        # Find nearest resistance (swing high above current price)
        resistances = swing_highs[swing_highs > current_price]
        if len(resistances) > 0:
            df.loc[df.index[i], 'nearest_resistance'] = resistances[0]

    return df


def detect_engulfing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect bullish and bearish engulfing patterns.

    Args:
        df: DataFrame with OHLCV data

    Returns:
        DataFrame with bullish_engulfing and bearish_engulfing columns (1/0)
    """
    df = df.copy()
    df['bullish_engulfing'] = 0
    df['bearish_engulfing'] = 0

    for i in range(1, len(df)):
        prev_open = df['open'].iloc[i-1]
        prev_close = df['close'].iloc[i-1]
        curr_open = df['open'].iloc[i]
        curr_close = df['close'].iloc[i]

        # Bullish engulfing: prev red, curr green, curr body engulfs prev
        if prev_close < prev_open and curr_close > curr_open:
            if curr_open <= prev_close and curr_close >= prev_open:
                df.loc[df.index[i], 'bullish_engulfing'] = 1

        # Bearish engulfing: prev green, curr red, curr body engulfs prev
        if prev_close > prev_open and curr_close < curr_open:
            if curr_open >= prev_close and curr_close <= prev_open:
                df.loc[df.index[i], 'bearish_engulfing'] = 1

    return df


def detect_doji(df: pd.DataFrame, threshold: float = 0.001) -> pd.DataFrame:
    """
    Detect doji candles (open ≈ close).

    Args:
        df: DataFrame with OHLCV data
        threshold: Max body size as fraction of range (0.1% default)

    Returns:
        DataFrame with doji column (1/0)
    """
    df = df.copy()
    body_size = abs(df['close'] - df['open'])
    candle_range = df['high'] - df['low']

    # Avoid division by zero
    candle_range = candle_range.replace(0, np.nan)

    df['doji'] = ((body_size / candle_range) < threshold).astype(int)
    df['doji'] = df['doji'].fillna(0).astype(int)

    return df


def detect_hammer(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect hammer pattern (long lower wick, small body at top).

    Args:
        df: DataFrame with OHLCV data

    Returns:
        DataFrame with hammer column (1/0)
    """
    df = df.copy()
    df['hammer'] = 0

    for i in range(len(df)):
        open_price = df['open'].iloc[i]
        close_price = df['close'].iloc[i]
        high_price = df['high'].iloc[i]
        low_price = df['low'].iloc[i]

        body_size = abs(close_price - open_price)
        lower_wick = min(open_price, close_price) - low_price
        upper_wick = high_price - max(open_price, close_price)
        candle_range = high_price - low_price

        if candle_range == 0:
            continue

        # Hammer: lower wick > 2x body, upper wick small
        if lower_wick > 2 * body_size and upper_wick < body_size:
            df.loc[df.index[i], 'hammer'] = 1

    return df


def detect_shooting_star(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect shooting star pattern (long upper wick, small body at bottom).

    Args:
        df: DataFrame with OHLCV data

    Returns:
        DataFrame with shooting_star column (1/0)
    """
    df = df.copy()
    df['shooting_star'] = 0

    for i in range(len(df)):
        open_price = df['open'].iloc[i]
        close_price = df['close'].iloc[i]
        high_price = df['high'].iloc[i]
        low_price = df['low'].iloc[i]

        body_size = abs(close_price - open_price)
        lower_wick = min(open_price, close_price) - low_price
        upper_wick = high_price - max(open_price, close_price)
        candle_range = high_price - low_price

        if candle_range == 0:
            continue

        # Shooting star: upper wick > 2x body, lower wick small
        if upper_wick > 2 * body_size and lower_wick < body_size:
            df.loc[df.index[i], 'shooting_star'] = 1

    return df


def add_price_action_features(
    df: pd.DataFrame,
    swing_lookback: int = 10,
    sr_window: int = 50,
) -> pd.DataFrame:
    """
    Add all price action features to DataFrame.

    Args:
        df: DataFrame with OHLCV data
        swing_lookback: Lookback for swing point detection
        sr_window: Window for support/resistance detection

    Returns:
        DataFrame with all price action features added
    """
    df = identify_swing_points(df, lookback=swing_lookback)
    df = detect_trend_structure(df)
    df = find_support_resistance(df, window=sr_window)
    df = detect_engulfing(df)
    df = detect_doji(df)
    df = detect_hammer(df)
    df = detect_shooting_star(df)

    return df
