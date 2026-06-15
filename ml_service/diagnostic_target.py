#!/usr/bin/env python3
"""Diagnostic script to analyze target variable and feature quality."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from ml_service.data.database import get_database
from ml_service.features.price_action import add_price_action_features
from ml_service.features.indicators import add_all_indicators
from ml_service.features.regime import add_regime_features
from ml_service.features.funding_rate import add_funding_rate_features
from ml_service.features.time_features import add_time_features
from ml_service.models.trainer import get_feature_columns
from ml_service.utils.config import get_forward_periods
from ml_service.utils.logger import setup_logger, get_logger

setup_logger()
logger = get_logger()


def load_data(symbol: str, timeframe: str, limit: int = 2000):
    """Load OHLCV data from database."""
    db = get_database()
    with db.get_connection() as conn:
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM ohlcv
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(symbol, timeframe, limit))

    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def analyze_target_distribution(df, forward_periods=None):
    if forward_periods is None:
        forward_periods = get_forward_periods()
    """Analyze target distribution with different thresholds."""

    print("\n" + "="*80)
    print("TARGET DISTRIBUTION ANALYSIS - BTCUSDT 1h")
    print("="*80)

    # Calculate forward return
    future_close = df['close'].shift(-forward_periods)
    forward_return = (future_close - df['close']) / df['close']

    # OLD TARGET: Simple percentage threshold (0.5%)
    print("\n1. OLD TARGET (0.5% threshold):")
    old_target = pd.Series(1, index=df.index)  # neutral
    old_target.loc[forward_return > 0.005] = 2  # long
    old_target.loc[forward_return < -0.005] = 0  # short

    old_counts = old_target.value_counts()
    total = len(old_target.dropna())
    print(f"   Short (0):   {old_counts.get(0, 0):4d} ({old_counts.get(0, 0)/total*100:5.1f}%)")
    print(f"   Neutral (1): {old_counts.get(1, 0):4d} ({old_counts.get(1, 0)/total*100:5.1f}%)")
    print(f"   Long (2):    {old_counts.get(2, 0):4d} ({old_counts.get(2, 0)/total*100:5.1f}%)")
    print(f"   Total: {total}")

    # NEW TARGET: ATR-normalized with different thresholds
    print("\n2. NEW TARGET (ATR-normalized):")

    if 'atr' not in df.columns:
        print("   ERROR: ATR not in dataframe, cannot compute ATR-normalized target")
        return

    atr_signal = forward_return / (df['atr'] / df['close'])

    thresholds = [0.3, 0.4, 0.5, 0.7]

    for thresh in thresholds:
        new_target = pd.Series(1, index=df.index)  # neutral
        new_target.loc[atr_signal > thresh] = 2  # long
        new_target.loc[atr_signal < -thresh] = 0  # short

        new_counts = new_target.value_counts()
        total_new = len(new_target.dropna())

        print(f"\n   Threshold ±{thresh}:")
        print(f"   Short (0):   {new_counts.get(0, 0):4d} ({new_counts.get(0, 0)/total_new*100:5.1f}%)")
        print(f"   Neutral (1): {new_counts.get(1, 0):4d} ({new_counts.get(1, 0)/total_new*100:5.1f}%)")
        print(f"   Long (2):    {new_counts.get(2, 0):4d} ({new_counts.get(2, 0)/total_new*100:5.1f}%)")

        neutral_pct = new_counts.get(1, 0) / total_new * 100
        if neutral_pct > 60:
            print(f"   ⚠️  WARNING: {neutral_pct:.1f}% neutral - threshold too strict!")


def check_nan_impact(symbol='BTCUSDT', timeframe='1h'):
    """Check how many samples are lost due to NaN in new features."""

    print("\n" + "="*80)
    print("NaN IMPACT ANALYSIS")
    print("="*80)

    df = load_data(symbol, timeframe)
    print(f"\nInitial data: {len(df)} rows")

    # Add features WITHOUT new improvements
    print("\n3. Training samples WITHOUT new features:")
    df_old = df.copy()
    df_old = add_price_action_features(df_old, swing_lookback=10, sr_window=50)

    # Basic indicators only (no order flow, no time features)
    from ml_service.features.indicators import (
        add_ema_indicators, add_rsi, add_macd, add_atr,
        add_bollinger_bands, add_vwap, add_volume_ratio,
        add_ema_alignment_score, add_volume_profile
    )
    df_old = add_ema_indicators(df_old)
    df_old = add_rsi(df_old)
    df_old = add_macd(df_old)
    df_old = add_atr(df_old)
    df_old = add_bollinger_bands(df_old)
    df_old = add_vwap(df_old)
    df_old = add_volume_ratio(df_old)
    df_old = add_ema_alignment_score(df_old)
    df_old = add_volume_profile(df_old)

    df_old = add_regime_features(df_old)
    df_old = add_funding_rate_features(df_old, symbol=symbol)

    # Get old feature columns (without order flow and time features)
    old_features = [
        'swing_high', 'swing_low', 'trend',
        'bullish_engulfing', 'bearish_engulfing', 'doji', 'hammer', 'shooting_star',
        'ema_9', 'ema_9_slope', 'ema_9_direction',
        'ema_21', 'ema_21_slope', 'ema_21_direction',
        'ema_50', 'ema_50_slope', 'ema_50_direction',
        'ema_200', 'ema_200_slope', 'ema_200_direction',
        'rsi', 'macd', 'macd_signal', 'macd_histogram',
        'atr', 'bb_upper', 'bb_middle', 'bb_lower', 'bb_bandwidth', 'bb_percent',
        'volume_ratio',
        'poc_distance', 'vah_distance', 'val_distance', 'price_in_value_area', 'volume_nodes',
        'adx', 'ema_alignment_score',
        'btc_correlation', 'spy_correlation',
        'funding_rate', 'funding_rate_ma', 'funding_extreme', 'funding_sentiment',
    ]

    df_old_clean = df_old[old_features].dropna()
    print(f"   Before new features: {len(df_old_clean)} samples")

    # Add features WITH new improvements
    print("\n   Training samples WITH new features:")
    df_new = df.copy()
    df_new = add_price_action_features(df_new, swing_lookback=10, sr_window=50)
    df_new = add_all_indicators(df_new)  # Includes order flow
    df_new = add_regime_features(df_new)
    df_new = add_funding_rate_features(df_new, symbol=symbol)
    df_new = add_time_features(df_new)  # New time features

    new_features = get_feature_columns(df_new)
    df_new_clean = df_new[new_features].dropna()
    print(f"   After new features: {len(df_new_clean)} samples")

    samples_lost = len(df_old_clean) - len(df_new_clean)
    print(f"\n   Samples lost: {samples_lost} ({samples_lost/len(df_old_clean)*100:.1f}%)")

    if samples_lost > 0:
        print("\n   Checking which new features cause NaN:")
        new_feature_set = set(new_features) - set(old_features)
        for feat in new_feature_set:
            if feat in df_new.columns:
                nan_count = df_new[feat].isna().sum()
                if nan_count > 0:
                    print(f"      {feat}: {nan_count} NaN values")

    # Analyze target with ATR
    analyze_target_distribution(df_new)


if __name__ == "__main__":
    check_nan_impact('BTCUSDT', '1h')
