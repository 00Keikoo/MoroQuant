"""Technical indicators feature engineering for ML trading system."""

import pandas as pd
import numpy as np
import pandas_ta as ta

from ml_service.utils.logger import get_logger

logger = get_logger(__name__)


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
    """Add VWAP (Volume Weighted Average Price).

    Ensures the DataFrame has an ordered DatetimeIndex before computing
    VWAP — ``pandas_ta.vwap`` warns and produces incorrect results on a
    non-DatetimeIndex / unsorted index. If a convertible time column
    (``timestamp``, ``open_time``, or ``datetime``) is present it is
    promoted to the index and sorted. If conversion is impossible VWAP
    is skipped gracefully (never raises).

    Args:
        df: DataFrame with OHLCV data (and ideally a time column).

    Returns:
        DataFrame with ``vwap`` and ``price_to_vwap`` columns (when
        computable); otherwise the input unchanged.
    """
    df = df.copy()

    # ── Ensure an ordered DatetimeIndex ──────────────────────────
    ready = False
    if isinstance(df.index, pd.DatetimeIndex):
        if not df.index.is_monotonic_increasing:
            df = df.sort_index()
        ready = True
    else:
        # Look for a convertible time column.
        for col in ('timestamp', 'open_time', 'datetime'):
            if col in df.columns:
                try:
                    dt = pd.to_datetime(df[col], errors='coerce')
                    if dt.notna().any():
                        df = df.set_index(dt)
                        if df.index.duplicated().any():
                            df = df[~df.index.duplicated(keep='last')]
                        df = df.sort_index()
                        ready = True
                        break
                except Exception as e:
                    logger.warning(
                        f"add_vwap: could not convert column '{col}' to "
                        f"DatetimeIndex: {e}"
                    )

    if not ready:
        logger.warning(
            "add_vwap: no DatetimeIndex and no convertible time column "
            "(timestamp/open_time/datetime) found — skipping VWAP"
        )
        return df

    # Guarantee the invariant pandas_ta requires.
    if not df.index.is_monotonic_increasing:
        df = df.sort_index()

    try:
        df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        df['price_to_vwap'] = ((df['close'] - df['vwap']) / df['vwap']) * 100
    except Exception as e:
        logger.warning(f"add_vwap: pandas_ta.vwap failed: {e} — skipping VWAP")

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


def add_volume_profile(df: pd.DataFrame, window: int = 50, price_buckets: int = 20) -> pd.DataFrame:
    """
    Add volume profile features using rolling window.

    Calculates Point of Control (POC), Value Area High/Low (VAH/VAL),
    and other volume profile metrics.

    Args:
        df: DataFrame with OHLCV data
        window: Rolling window for volume profile calculation
        price_buckets: Number of price buckets to split range into

    Returns:
        DataFrame with volume profile features
    """
    df = df.copy()

    poc_list = []
    vah_list = []
    val_list = []
    in_va_list = []
    volume_nodes_list = []

    for i in range(len(df)):
        if i < window:
            poc_list.append(np.nan)
            vah_list.append(np.nan)
            val_list.append(np.nan)
            in_va_list.append(0)
            volume_nodes_list.append(0)
            continue

        window_df = df.iloc[i - window:i]

        price_min = window_df['low'].min()
        price_max = window_df['high'].max()
        price_range = price_max - price_min

        if price_range == 0:
            poc_list.append(0.0)
            vah_list.append(0.0)
            val_list.append(0.0)
            in_va_list.append(0)
            volume_nodes_list.append(0)
            continue

        bucket_size = price_range / price_buckets
        price_buckets_data = np.zeros(price_buckets)

        for _, row in window_df.iterrows():
            bucket_idx = int((row['close'] - price_min) / bucket_size)
            bucket_idx = min(bucket_idx, price_buckets - 1)
            price_buckets_data[bucket_idx] += row['volume']

        poc_idx = np.argmax(price_buckets_data)
        poc_price = price_min + (poc_idx + 0.5) * bucket_size

        sorted_indices = np.argsort(price_buckets_data)[::-1]
        total_volume = price_buckets_data.sum()
        value_area_volume = 0
        value_area_indices = []

        for idx in sorted_indices:
            value_area_indices.append(idx)
            value_area_volume += price_buckets_data[idx]
            if value_area_volume >= 0.7 * total_volume:
                break

        vah_idx = max(value_area_indices)
        val_idx = min(value_area_indices)

        vah_price = price_min + (vah_idx + 0.5) * bucket_size
        val_price = price_min + (val_idx + 0.5) * bucket_size

        current_price = df.iloc[i]['close']

        poc_distance = (current_price - poc_price) / current_price
        vah_distance = (current_price - vah_price) / current_price
        val_distance = (current_price - val_price) / current_price

        in_value_area = 1 if val_price <= current_price <= vah_price else 0

        price_tolerance = 0.02
        volume_nodes = 0
        for idx in range(price_buckets):
            bucket_price = price_min + (idx + 0.5) * bucket_size
            if abs(bucket_price - current_price) / current_price <= price_tolerance:
                if price_buckets_data[idx] > np.median(price_buckets_data):
                    volume_nodes += 1

        poc_list.append(poc_distance)
        vah_list.append(vah_distance)
        val_list.append(val_distance)
        in_va_list.append(in_value_area)
        volume_nodes_list.append(volume_nodes)

    df['poc_distance'] = poc_list
    df['vah_distance'] = vah_list
    df['val_distance'] = val_list
    df['price_in_value_area'] = in_va_list
    df['volume_nodes'] = volume_nodes_list

    return df


def add_order_flow_features(df: pd.DataFrame, delta_ma_period: int = 10, cumulative_delta_window: int = 20) -> pd.DataFrame:
    """
    Add order flow features based on estimated buy/sell volume.

    Args:
        df: DataFrame with OHLCV data
        delta_ma_period: Period for delta moving average
        cumulative_delta_window: Window for cumulative delta

    Returns:
        DataFrame with order flow features
    """
    df = df.copy()

    price_range = df['high'] - df['low']
    price_range = price_range.replace(0, np.nan)

    df['buy_volume'] = df['volume'] * (df['close'] - df['low']) / price_range
    df['sell_volume'] = df['volume'] * (df['high'] - df['close']) / price_range

    df['buy_volume'] = df['buy_volume'].fillna(0)
    df['sell_volume'] = df['sell_volume'].fillna(0)

    df['delta'] = df['buy_volume'] - df['sell_volume']

    df['delta_ma'] = df['delta'].rolling(window=delta_ma_period, min_periods=1).mean()

    df['cumulative_delta'] = df['delta'].rolling(window=cumulative_delta_window, min_periods=1).sum()

    df['delta_ratio'] = df['delta'] / df['volume'].replace(0, np.nan)
    df['delta_ratio'] = df['delta_ratio'].fillna(0).clip(-1, 1)

    price_change = df['close'].diff()
    df['delta_divergence'] = 0
    df.loc[(price_change > 0) & (df['delta'] < 0), 'delta_divergence'] = 1
    df.loc[(price_change < 0) & (df['delta'] > 0), 'delta_divergence'] = 1

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
    df = add_volume_profile(df, window=50, price_buckets=20)
    df = add_order_flow_features(df, delta_ma_period=10, cumulative_delta_window=20)

    return df
