#!/usr/bin/env python3
"""Threshold sweep to find optimal long/short classification threshold."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from ml_service.data.database import get_database
from ml_service.models.trainer import train_model, create_target_variable, prepare_features


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

    if df.empty:
        return None

    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def get_class_distribution(df, symbol, btc_df, spy_df, threshold_pct):
    """Get class distribution for a given threshold."""
    long_thresh = threshold_pct / 100.0
    short_thresh = -threshold_pct / 100.0

    df_prep = prepare_features(df.copy(), symbol=symbol, btc_df=btc_df, spy_df=spy_df)
    df_target = create_target_variable(
        df_prep,
        forward_periods=12,
        long_threshold=long_thresh,
        short_threshold=short_thresh
    )

    df_clean = df_target.dropna()
    value_counts = df_clean['target'].value_counts(normalize=True) * 100

    return {
        'short_pct': value_counts.get(0, 0),
        'neutral_pct': value_counts.get(1, 0),
        'long_pct': value_counts.get(2, 0),
    }


def main():
    symbol = "BTCUSDT"
    timeframe = "1h"

    print(f"Running threshold sweep for {symbol} {timeframe}...\n")

    # Load data
    df = load_data(symbol, timeframe, limit=1000)
    if df is None or len(df) == 0:
        print("Failed to fetch data from database")
        return

    print(f"Loaded {len(df)} candles from database")

    # Load reference data
    btc_df = None  # BTCUSDT doesn't need BTC correlation
    spy_df = load_data('ES_proxy', timeframe, limit=1000)

    # Sweep thresholds
    thresholds = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    results = []

    for thresh in thresholds:
        print(f"\nTesting threshold ±{thresh}%...")

        long_thresh = thresh / 100.0
        short_thresh = -thresh / 100.0

        try:
            # Get class distribution
            dist = get_class_distribution(df, symbol, btc_df, spy_df, thresh)

            # Train model
            result = train_model(
                df.copy(),
                symbol,
                timeframe,
                btc_df=btc_df,
                spy_df=spy_df,
                forward_periods=12,
                long_threshold=long_thresh,
                short_threshold=short_thresh
            )

            results.append({
                'threshold': thresh,
                'f1_weighted': result['avg_f1_weighted'],
                'short_pct': dist['short_pct'],
                'neutral_pct': dist['neutral_pct'],
                'long_pct': dist['long_pct'],
            })

            print(f"✓ F1={result['avg_f1_weighted']:.3f} | "
                  f"Short {dist['short_pct']:.1f}% | "
                  f"Neutral {dist['neutral_pct']:.1f}% | "
                  f"Long {dist['long_pct']:.1f}%")

        except Exception as e:
            print(f"✗ FAILED: {e}")

    # Results table
    print("\n" + "="*80)
    print("THRESHOLD SWEEP RESULTS")
    print("="*80)
    print(f"{'Threshold':<12} {'F1':<8} {'Short %':<10} {'Neutral %':<12} {'Long %':<10}")
    print("-"*80)

    for r in results:
        print(f"±{r['threshold']:.1f}%       {r['f1_weighted']:.3f}    "
              f"{r['short_pct']:>5.1f}%      {r['neutral_pct']:>7.1f}%       "
              f"{r['long_pct']:>5.1f}%")

    print("="*80)

    # Find best
    if results:
        best = max(results, key=lambda x: x['f1_weighted'])
        print(f"\nBest threshold: ±{best['threshold']:.1f}% (F1={best['f1_weighted']:.3f})")
        print(f"Class distribution: Short {best['short_pct']:.1f}% | "
              f"Neutral {best['neutral_pct']:.1f}% | Long {best['long_pct']:.1f}%")


if __name__ == "__main__":
    main()
