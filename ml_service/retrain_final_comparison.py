#!/usr/bin/env python3
"""Retrain all crypto models with ±0.3 threshold and generate comparison table."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from ml_service.data.database import get_database
from ml_service.models.trainer import train_model
from ml_service.utils.logger import setup_logger, get_logger

setup_logger()
logger = get_logger()

# Original F1 scores (before improvements)
ORIGINAL_SCORES = {
    ('BTCUSDT', '1h'): 0.3133,
    ('BTCUSDT', '4h'): 0.5482,
    ('ETHUSDT', '1h'): 0.2160,
    ('ETHUSDT', '4h'): 0.7976,
    ('BNBUSDT', '1h'): 0.5075,
    ('BNBUSDT', '4h'): 0.8102,
    ('SOLUSDT', '1h'): 0.2123,
    ('SOLUSDT', '4h'): 0.7948,
    ('HYPEUSDT', '1h'): 0.4409,
    ('HYPEUSDT', '4h'): 0.4249,
}

# After improvements with ±0.5 threshold
AFTER_05_SCORES = {
    ('BTCUSDT', '1h'): 0.1302,
    ('BTCUSDT', '4h'): 0.3634,
    ('ETHUSDT', '1h'): 0.1418,
    ('ETHUSDT', '4h'): 0.6894,
    ('BNBUSDT', '1h'): 0.5178,
    ('BNBUSDT', '4h'): 0.6018,
    ('SOLUSDT', '1h'): 0.1910,
    ('SOLUSDT', '4h'): 0.5861,
    ('HYPEUSDT', '1h'): 0.3710,
    ('HYPEUSDT', '4h'): 0.3385,
}


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
    """Retrain all crypto models with ±0.3 threshold."""
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'HYPEUSDT']
    timeframes = ['1h', '4h']

    logger.info("Loading reference data for correlations...")
    btc_1h = load_data('BTCUSDT', '1h')
    btc_4h = load_data('BTCUSDT', '4h')
    spy_1h = load_data('ES_proxy', '1h')
    spy_4h = load_data('ES_proxy', '4h')

    results = []

    for symbol in symbols:
        for timeframe in timeframes:
            logger.info(f"\n{'='*80}")
            logger.info(f"Training {symbol} {timeframe}")
            logger.info(f"{'='*80}")

            df = load_data(symbol, timeframe)

            if df is None or len(df) < 100:
                logger.warning(f"Insufficient data for {symbol} {timeframe}")
                continue

            btc_df = None if symbol == 'BTCUSDT' else (btc_1h if timeframe == '1h' else btc_4h)
            spy_df = spy_1h if timeframe == '1h' else spy_4h

            try:
                train_results = train_model(
                    df=df,
                    symbol=symbol,
                    timeframe=timeframe,
                    btc_df=btc_df,
                    spy_df=spy_df,
                )

                new_f1 = train_results['avg_f1_weighted']
                logger.info(f"✓ Training complete: F1 = {new_f1:.4f}")

                results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'original_f1': ORIGINAL_SCORES.get((symbol, timeframe), 0),
                    'after_improvements_f1': new_f1,
                })

            except Exception as e:
                logger.error(f"✗ Training failed: {e}", exc_info=True)

    # Generate comparison table
    print("\n" + "="*100)
    print("BEFORE/AFTER F1 COMPARISON - ALL CRYPTO MODELS")
    print("="*100)
    print(f"{'Symbol':<12} {'TF':<4} {'Original F1':<12} {'After Improvements':<18} {'Delta':<12}")
    print("-" * 100)

    for r in results:
        original = r['original_f1']
        after = r['after_improvements_f1']
        delta = after - original
        delta_str = f"{delta:+.4f}" if original > 0 else "N/A"

        print(f"{r['symbol']:<12} {r['timeframe']:<4} {original:<12.4f} {after:<18.4f} {delta_str:<12}")

    successful = len([r for r in results if r['after_improvements_f1'] > 0])
    print(f"\n✓ Successfully trained: {successful}/{len(results)} models")

    print("\n" + "="*100)
    print("IMPROVEMENTS APPLIED:")
    print("="*100)
    print("1. Order Flow Delta (7 features)")
    print("2. Time Features (10 features)")
    print("3. Risk-Adjusted Target: ATR-normalized with ±0.3 threshold")
    print("4. Ensemble Model: XGBoost + LightGBM averaged predictions")
    print("5. Multi-Timeframe Confirmation: 1h signals check 4h")
    print("="*100)


if __name__ == "__main__":
    main()
