"""Technical indicators feature engineering for ML trading system."""

import pandas as pd
import numpy as np
import pandas_ta as ta


def add_ema_indicators(df: pd.DataFrame, periods: list = [9, 21, 50, 200]) -> pd.DataFrame:
    """
    Add EMA indicators and their slopes.

    Args:
        df: DataFrame with OHLCV data
        periods: List of EMA periods

    Returns:
        DataFrame with EMA columns and slope columns
    """
    df = df.copy()

    for period in periods:
        col_name = f'ema_{period}'
        ema_series = ta.ema(df['close'], length=period)
        df[col_name] = ema_series if ema_series is not None else np.nan

        # Calculate slope (change over last 5 periods), handling NaN values
        df[f'{col_name}_slope'] = df[col_name].diff(5)

        # Classify slope as rising (1), flat (0), falling (-1)
        slope_threshold = df['close'].std() * 0.001  # 0.1% of price std
        df[f'{col_name}_direction'] = 0
        slope_col = df[f'{col_name}_slope']
        df.loc[slope_col > slope_threshold, f'{col_name}_direction'] = 1
        df.loc[slope_col < -slope_threshold, f'{col_name}_direction'] = -1

    return df


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Add RSI indicator.

    Args:
        df: DataFrame with OHLCV data
        period: RSI period

    Returns:
        DataFrame with RSI column
    """
    df = df.copy()
    df['rsi'] = ta.rsi(df['close'], length=period)
    return df


def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Add MACD indicator with signal and histogram.

    Args:
        df: DataFrame with OHLCV data
        fast: Fast EMA period
        slow: Slow EMA period
        signal: Signal line period

    Returns:
        DataFrame with MACD, signal, and histogram columns
    """
    df = df.copy()
    macd = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)

    if macd is not None:
        df['macd'] = macd[f'MACD_{fast}_{slow}_{signal}']
        df['macd_signal'] = macd[f'MACDs_{fast}_{slow}_{signal}']
        df['macd_histogram'] = macd[f'MACDh_{fast}_{slow}_{signal}']

    return df


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Add ATR (Average True Range) indicator.

    Args:
        df: DataFrame with OHLCV data
        period: ATR period

    Returns:
        DataFrame with ATR column
    """
    df = df.copy()
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=period)
    return df


def add_bollinger_bands(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> pd.DataFrame:
    """
    Add Bollinger Bands with %B and bandwidth.

    Args:
        df: DataFrame with OHLCV data
        period: BB period
        std: Standard deviation multiplier

    Returns:
        DataFrame with BB upper, middle, lower, %B, and bandwidth columns
    """
    df = df.copy()
    bbands = ta.bbands(df['close'], length=period, std=std)

    if bbands is not None:
        df['bb_upper'] = bbands[f'BBU_{period}_{std}_{std}']
        df['bb_middle'] = bbands[f'BBM_{period}_{std}_{std}']
        df['bb_lower'] = bbands[f'BBL_{period}_{std}_{std}']
        df['bb_bandwidth'] = bbands[f'BBB_{period}_{std}_{std}']
        df['bb_percent'] = bbands[f'BBP_{period}_{std}_{std}']

    return df


def add_vwap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add VWAP (Volume Weighted Average Price).

    Note: For intraday data, VWAP should reset daily. For daily data, it's cumulative.

    Args:
        df: DataFrame with OHLCV data and timestamp

    Returns:
        DataFrame with VWAP column
    """
    df = df.copy()

    # Calculate VWAP using pandas-ta
    df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])

    # Calculate price position relative to VWAP (percentage)
    df['price_to_vwap'] = ((df['close'] - df['vwap']) / df['vwap']) * 100

    return df


def add_volume_ratio(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """
    Add volume ratio (current volume / average volume).

    Args:
        df: DataFrame with OHLCV data
        period: Period for average volume calculation

    Returns:
        DataFrame with volume ratio column
    """
    df = df.copy()

    avg_volume = df['volume'].rolling(window=period).mean()
    df['volume_ratio'] = df['volume'] / avg_volume

    return df


def add_ema_alignment_score(df: pd.DataFrame, periods: list = [9, 21, 50, 200]) -> pd.DataFrame:
    """
    Calculate EMA alignment score (how many EMAs are stacked bullishly).

    Bullish alignment: EMA9 > EMA21 > EMA50 > EMA200
    Score ranges from 0 (no alignment) to 3 (perfect bullish alignment)

    Args:
        df: DataFrame with EMA columns already calculated
        periods: List of EMA periods (must match existing EMA columns)

    Returns:
        DataFrame with ema_alignment_score column
    """
    df = df.copy()
    df['ema_alignment_score'] = 0

    # Check each pair of consecutive EMAs
    for i in range(len(periods) - 1):
        fast_ema = f'ema_{periods[i]}'
        slow_ema = f'ema_{periods[i+1]}'

        if fast_ema in df.columns and slow_ema in df.columns:
            df['ema_alignment_score'] += (df[fast_ema] > df[slow_ema]).astype(int)

    return df


def add_all_indicators(
    df: pd.DataFrame,
    ema_periods: list = [9, 21, 50, 200],
    rsi_period: int = 14,
    macd_params: tuple = (12, 26, 9),
    atr_period: int = 14,
    bb_period: int = 20,
    bb_std: float = 2.0,
    volume_period: int = 20,
) -> pd.DataFrame:
    """
    Add all technical indicators to DataFrame.

    Args:
        df: DataFrame with OHLCV data
        ema_periods: List of EMA periods
        rsi_period: RSI period
        macd_params: MACD (fast, slow, signal) parameters
        atr_period: ATR period
        bb_period: Bollinger Bands period
        bb_std: Bollinger Bands standard deviation
        volume_period: Volume ratio period

    Returns:
        DataFrame with all indicator columns added
    """
    df = add_ema_indicators(df, periods=ema_periods)
    df = add_rsi(df, period=rsi_period)
    df = add_macd(df, fast=macd_params[0], slow=macd_params[1], signal=macd_params[2])
    df = add_atr(df, period=atr_period)
    df = add_bollinger_bands(df, period=bb_period, std=bb_std)
    df = add_vwap(df)
    df = add_volume_ratio(df, period=volume_period)
    df = add_ema_alignment_score(df, periods=ema_periods)

    return df
