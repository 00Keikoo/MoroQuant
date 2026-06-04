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


def add_cross_pair_correlation(
    df: pd.DataFrame,
    btc_df: pd.DataFrame = None,
    spy_df: pd.DataFrame = None,
    window: int = 20,
) -> pd.DataFrame:
    """
    Calculate rolling correlation with BTC and ES_proxy (SPY).

    Correlation interpretation:
    - High correlation with SPY (>0.5): Risk-on regime
    - Low correlation with SPY (<0.2): Decorrelated/crypto-specific moves
    - BTC correlation shows broader crypto market influence

    Args:
        df: Primary symbol DataFrame with close prices
        btc_df: BTCUSDT DataFrame for BTC correlation
        spy_df: ES_proxy (SPY) DataFrame for risk-on/off correlation
        window: Rolling correlation window

    Returns:
        DataFrame with btc_correlation, spy_correlation, and correlation_regime
    """
    df = df.copy()
    df['returns'] = df['close'].pct_change()

    # BTC correlation
    if btc_df is not None and len(btc_df) > 0:
        btc_df = btc_df.copy()
        btc_df['returns'] = btc_df['close'].pct_change()

        if 'timestamp' in df.columns and 'timestamp' in btc_df.columns:
            df_aligned = df.set_index('timestamp')
            btc_aligned = btc_df.set_index('timestamp')

            merged = df_aligned[['returns']].join(
                btc_aligned[['returns']],
                how='left',
                rsuffix='_btc'
            )

            df['btc_correlation'] = merged['returns'].rolling(window=window).corr(
                merged['returns_btc']
            ).values
        else:
            if len(df) == len(btc_df):
                df['btc_correlation'] = df['returns'].rolling(window=window).corr(
                    btc_df['returns']
                )
            else:
                df['btc_correlation'] = 0.0
    else:
        df['btc_correlation'] = 0.0

    # SPY correlation (risk-on/off indicator)
    if spy_df is not None and len(spy_df) > 0:
        spy_df = spy_df.copy()
        spy_df['returns'] = spy_df['close'].pct_change()

        if 'timestamp' in df.columns and 'timestamp' in spy_df.columns:
            df_aligned = df.set_index('timestamp')
            spy_aligned = spy_df.set_index('timestamp')

            merged = df_aligned[['returns']].join(
                spy_aligned[['returns']],
                how='left',
                rsuffix='_spy'
            )

            df['spy_correlation'] = merged['returns'].rolling(window=window).corr(
                merged['returns_spy']
            ).values
        else:
            if len(df) == len(spy_df):
                df['spy_correlation'] = df['returns'].rolling(window=window).corr(
                    spy_df['returns']
                )
            else:
                df['spy_correlation'] = 0.0
    else:
        df['spy_correlation'] = 0.0

    # Fill NaN with 0 (neutral correlation)
    df['btc_correlation'] = df['btc_correlation'].fillna(0.0)
    df['spy_correlation'] = df['spy_correlation'].fillna(0.0)

    # Correlation regime classification
    df['correlation_regime'] = 'mixed'
    df.loc[df['spy_correlation'] > 0.5, 'correlation_regime'] = 'risk_on'
    df.loc[df['spy_correlation'].abs() < 0.2, 'correlation_regime'] = 'decorrelated'

    df = df.drop(columns=['returns'], errors='ignore')

    return df


def add_regime_features(
    df: pd.DataFrame,
    btc_df: pd.DataFrame = None,
    spy_df: pd.DataFrame = None,
    atr_window: int = 50,
    adx_period: int = 14,
    correlation_window: int = 20,
) -> pd.DataFrame:
    """
    Add all regime classification features.

    Args:
        df: DataFrame with OHLCV and ATR already calculated
        btc_df: Optional BTCUSDT DataFrame for BTC correlation
        spy_df: Optional ES_proxy DataFrame for risk-on/off correlation
        atr_window: Window for ATR rolling mean
        adx_period: ADX period
        correlation_window: Rolling correlation window

    Returns:
        DataFrame with all regime features added
    """
    df = classify_volatility_regime(df, atr_window=atr_window)
    df = classify_trend_regime(df, adx_period=adx_period)
    df = create_market_phase(df)
    df = add_cross_pair_correlation(df, btc_df=btc_df, spy_df=spy_df, window=correlation_window)

    return df
