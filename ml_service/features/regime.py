"""Market regime classification for ML trading system."""

import pandas as pd
import numpy as np
import pandas_ta as ta


def classify_volatility_regime(df: pd.DataFrame, atr_window: int = 50) -> pd.DataFrame:
    """
    Classify volatility regime based on ATR relative to its rolling mean.

    Args:
        df: DataFrame with ATR column already calculated
        atr_window: Window for ATR rolling mean

    Returns:
        DataFrame with volatility_regime column (low/normal/high)
    """
    df = df.copy()

    if 'atr' not in df.columns:
        raise ValueError("ATR column must be calculated before volatility regime classification")

    atr_mean = df['atr'].rolling(window=atr_window).mean()

    df['volatility_regime'] = 'normal'
    df.loc[df['atr'] < 0.7 * atr_mean, 'volatility_regime'] = 'low'
    df.loc[df['atr'] > 1.3 * atr_mean, 'volatility_regime'] = 'high'

    return df


def classify_trend_regime(df: pd.DataFrame, adx_period: int = 14) -> pd.DataFrame:
    """
    Classify trend vs chop using ADX indicator.

    Args:
        df: DataFrame with OHLCV data
        adx_period: ADX period

    Returns:
        DataFrame with adx and trend_regime columns
    """
    df = df.copy()

    adx_result = ta.adx(df['high'], df['low'], df['close'], length=adx_period)

    if adx_result is not None:
        df['adx'] = adx_result[f'ADX_{adx_period}']

        df['trend_regime'] = 'transitioning'
        df.loc[df['adx'] > 25, 'trend_regime'] = 'trending'
        df.loc[df['adx'] < 20, 'trend_regime'] = 'choppy'
    else:
        df['adx'] = np.nan
        df['trend_regime'] = 'unknown'

    return df


def create_market_phase(df: pd.DataFrame) -> pd.DataFrame:
    """
    Combine volatility and trend regimes into market phase labels.

    Possible phases:
    - trending_high_vol
    - trending_normal_vol
    - trending_low_vol
    - choppy_high_vol
    - choppy_normal_vol
    - choppy_low_vol
    - transitioning_high_vol
    - transitioning_normal_vol
    - transitioning_low_vol

    Args:
        df: DataFrame with volatility_regime and trend_regime columns

    Returns:
        DataFrame with market_phase column
    """
    df = df.copy()

    if 'volatility_regime' not in df.columns or 'trend_regime' not in df.columns:
        raise ValueError("Both volatility_regime and trend_regime must be calculated first")

    df['market_phase'] = df['trend_regime'] + '_' + df['volatility_regime'] + '_vol'

    return df


def add_rolling_correlation(
    df: pd.DataFrame,
    symbol2_df: pd.DataFrame = None,
    window: int = 20,
) -> pd.DataFrame:
    """
    Calculate rolling correlation between two symbols' returns.

    Args:
        df: Primary symbol DataFrame with close prices
        symbol2_df: Secondary symbol DataFrame (e.g., ES_proxy)
        window: Rolling correlation window

    Returns:
        DataFrame with btc_es_correlation column (or NaN if symbol2 not available)
    """
    df = df.copy()

    if symbol2_df is None or len(symbol2_df) == 0:
        df['btc_es_correlation'] = np.nan
        return df

    df['returns'] = df['close'].pct_change()

    symbol2_df = symbol2_df.copy()
    symbol2_df['returns'] = symbol2_df['close'].pct_change()

    if 'timestamp' in df.columns and 'timestamp' in symbol2_df.columns:
        df_aligned = df.set_index('timestamp')
        symbol2_aligned = symbol2_df.set_index('timestamp')

        merged = df_aligned[['returns']].join(
            symbol2_aligned[['returns']],
            how='left',
            rsuffix='_symbol2'
        )

        df['btc_es_correlation'] = merged['returns'].rolling(window=window).corr(
            merged['returns_symbol2']
        ).values
    else:
        if len(df) == len(symbol2_df):
            df['btc_es_correlation'] = df['returns'].rolling(window=window).corr(
                symbol2_df['returns']
            )
        else:
            df['btc_es_correlation'] = np.nan

    df = df.drop(columns=['returns'], errors='ignore')

    return df


def add_regime_features(
    df: pd.DataFrame,
    symbol2_df: pd.DataFrame = None,
    atr_window: int = 50,
    adx_period: int = 14,
    correlation_window: int = 20,
) -> pd.DataFrame:
    """
    Add all regime classification features.

    Args:
        df: DataFrame with OHLCV and ATR already calculated
        symbol2_df: Optional second symbol for correlation (e.g., ES_proxy)
        atr_window: Window for ATR rolling mean
        adx_period: ADX period
        correlation_window: Rolling correlation window

    Returns:
        DataFrame with all regime features added
    """
    df = classify_volatility_regime(df, atr_window=atr_window)
    df = classify_trend_regime(df, adx_period=adx_period)
    df = create_market_phase(df)
    df = add_rolling_correlation(df, symbol2_df=symbol2_df, window=correlation_window)

    return df
