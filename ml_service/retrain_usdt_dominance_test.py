#!/usr/bin/env python3
"""Test USDT dominance features by retraining BTCUSDT 1h model."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from ml_service.data.database import get_database
from ml_service.data.coingecko import get_coingecko_fetcher
from ml_service.models.trainer import train_model
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

    if df.empty:
        return None

    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def main():
    logger.info("="*80)
    logger.info("USDT Dominance Feature Test - BTCUSDT 1h")
    logger.info("="*80)

    # Fetch fresh market dominance data
    logger.info("\nStep 1: Fetching market dominance from CoinGecko...")
    fetcher = get_coingecko_fetcher()
    success = fetcher.fetch_and_store()

    if success:
        logger.info("✓ Market dominance data fetched successfully")
    else:
        logger.warning("⚠ Failed to fetch market dominance data - continuing with existing data")

    # Load data
    logger.info("\nStep 2: Loading OHLCV data...")
    btc_df = load_data('BTCUSDT', '1h', limit=2000)
    eth_df = load_data('ETHUSDT', '1h', limit=2000)
    spy_df = load_data('ES_proxy', '1h', limit=2000)

    if btc_df is None or len(btc_df) < 100:
        logger.error("Insufficient BTCUSDT data")
        return

    logger.info(f"✓ Loaded {len(btc_df)} BTCUSDT candles")
    logger.info(f"✓ Loaded {len(eth_df) if eth_df is not None else 0} ETHUSDT candles")
    logger.info(f"✓ Loaded {len(spy_df) if spy_df is not None else 0} ES_proxy candles")

    # Load dominance data
    logger.info("\nStep 3: Loading market dominance data...")
    dominance_df = fetcher.get_dominance_dataframe()
    logger.info(f"✓ Loaded {len(dominance_df)} dominance records")

    if len(dominance_df) > 0:
        logger.info(f"  - BTC Dominance range: {dominance_df['btc_dominance'].min():.2f}% - {dominance_df['btc_dominance'].max():.2f}%")
        logger.info(f"  - USDT Dominance range: {dominance_df['usdt_dominance'].min():.2f}% - {dominance_df['usdt_dominance'].max():.2f}%")
    else:
        logger.warning("⚠ No dominance data available - features will use proxy only")

    # Train model
    logger.info("\nStep 4: Training BTCUSDT 1h model with USDT dominance features...")

    train_results = train_model(
        df=btc_df,
        symbol='BTCUSDT',
        timeframe='1h',
        btc_df=None,  # Self-reference not needed
        eth_df=eth_df,
        spy_df=spy_df,
        dominance_df=dominance_df if len(dominance_df) > 0 else None,
    )

    # Display results
    logger.info("\n" + "="*80)
    logger.info("TRAINING RESULTS")
    logger.info("="*80)
    logger.info(f"Model Type: {train_results['model_type']}")
    logger.info(f"Number of Folds: {train_results['n_folds']}")
    logger.info(f"\nF1 Scores:")
    logger.info(f"  - Short:   {train_results['avg_f1_short']:.4f}")
    logger.info(f"  - Neutral: {train_results['avg_f1_neutral']:.4f}")
    logger.info(f"  - Long:    {train_results['avg_f1_long']:.4f}")
    logger.info(f"  - Weighted: {train_results['avg_f1_weighted']:.4f}")

    # Feature importance analysis
    logger.info("\n" + "="*80)
    logger.info("TOP 20 FEATURE IMPORTANCE")
    logger.info("="*80)

    feature_importance = train_results['feature_importance']
    top_20 = feature_importance.head(20)

    usdt_features = ['btc_dominance_proxy', 'usdt_flight_signal', 'risk_off_regime',
                     'usdt_dominance', 'usdt_dominance_1h_change']

    for idx, row in top_20.iterrows():
        feature_name = row['feature']
        importance = row['importance']
        marker = " ← USDT DOMINANCE" if feature_name in usdt_features else ""
        logger.info(f"{idx+1:2d}. {feature_name:30s} {importance:8.4f}{marker}")

    # Check if USDT dominance features are in top 10
    top_10 = feature_importance.head(10)
    usdt_in_top_10 = [f for f in top_10['feature'].values if f in usdt_features]

    logger.info("\n" + "="*80)
    logger.info("USDT DOMINANCE FEATURE ANALYSIS")
    logger.info("="*80)

    if usdt_in_top_10:
        logger.info(f"✓ {len(usdt_in_top_10)} USDT dominance feature(s) in TOP 10:")
        for feature in usdt_in_top_10:
            rank = top_10[top_10['feature'] == feature].index[0] + 1
            logger.info(f"  - {feature} (rank #{rank})")
    else:
        logger.info("✗ No USDT dominance features in TOP 10")
        logger.info("\nRanks of USDT dominance features:")
        for feature in usdt_features:
            if feature in feature_importance['feature'].values:
                rank = feature_importance[feature_importance['feature'] == feature].index[0] + 1
                logger.info(f"  - {feature}: rank #{rank}")

    logger.info("\n" + "="*80)
    logger.info(f"Model saved to: {train_results['model_path']}")
    logger.info("="*80)


if __name__ == '__main__':
    main()
