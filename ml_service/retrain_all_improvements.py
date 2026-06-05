#!/usr/bin/env python3
"""Retrain all crypto models with all 4 improvements and generate comparison table."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from ml_service.data.database import get_database
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
    """Retrain all crypto models with improvements."""
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
                results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'f1': 'INSUFFICIENT DATA',
                    'status': 'SKIPPED'
                })
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

                f1 = train_results['avg_f1_weighted']
                logger.info(f"✓ Training complete: F1 = {f1:.4f}")

                results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'f1': f1,
                    'status': 'SUCCESS'
                })

            except Exception as e:
                logger.error(f"✗ Training failed: {e}", exc_info=True)
                results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'f1': 'FAILED',
                    'status': f'ERROR: {str(e)[:50]}'
                })

    print("\n" + "="*100)
    print("F1 SCORES - ALL CRYPTO MODELS (WITH ALL 4 IMPROVEMENTS)")
    print("="*100)
    print(f"{'Symbol':<12} {'Timeframe':<10} {'F1 Score':<12} {'Status':<20}")
    print("-" * 100)
    for r in results:
        f1_str = f"{r['f1']:.4f}" if isinstance(r['f1'], float) else r['f1']
        print(f"{r['symbol']:<12} {r['timeframe']:<10} {f1_str:<12} {r['status']:<20}")

    successful = len([r for r in results if r['status'] == 'SUCCESS'])
    print(f"\n✓ Successfully trained: {successful}/{len(results)} models")
    print(f"✗ Failed/Skipped: {len(results) - successful}/{len(results)} models")

    print("\n" + "="*100)
    print("IMPROVEMENTS INTEGRATED:")
    print("="*100)
    print("1. Order Flow Delta: buy_volume, sell_volume, delta, delta_ma, delta_divergence,")
    print("   cumulative_delta, delta_ratio")
    print("2. Time Features: hour_of_day, session flags, month-end indicators")
    print("3. Risk-Adjusted Target: ATR-normalized forward returns (±0.5 threshold)")
    print("4. Ensemble Model: XGBoost + LightGBM averaged predictions")
    print("5. Multi-Timeframe Confirmation: 1h signals check 4h for agreement")
    print("="*100)


if __name__ == "__main__":
    main()
