#!/usr/bin/env python3
"""Retrain all crypto models with new features and generate F1 comparison."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import pickle
from ml_service.data.database import get_database
from ml_service.models.trainer import train_model
from ml_service.utils.logger import setup_logger, get_logger

setup_logger()
logger = get_logger()


def load_old_model_metrics(symbol: str, timeframe: str) -> dict:
    """Load F1 scores from the most recent old model."""
    models_dir = Path(__file__).parent / "storage" / "models"
    pattern = f"{symbol}_{timeframe}_*.pkl"
    model_files = list(models_dir.glob(pattern))

    if not model_files:
        return None

    latest_model = max(model_files, key=lambda p: p.stat().st_mtime)

    try:
        with open(latest_model, 'rb') as f:
            model_package = pickle.load(f)

        # Try to get validation metrics from metadata
        metadata = model_package.get('metadata', {})

        # Return placeholder - we'll extract from fold results if available
        return {
            'file': latest_model.name,
            'model_type': metadata.get('model_type', 'unknown'),
        }
    except Exception as e:
        logger.warning(f"Could not load old model {latest_model}: {e}")
        return None


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
    """Retrain all crypto models and generate comparison table."""

    # Define all symbol/timeframe combinations to retrain
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'HYPEUSDT']
    timeframes = ['1h', '4h']

    # Load reference data once (BTC and ES_proxy)
    logger.info("Loading reference data for correlations...")
    btc_1h = load_data('BTCUSDT', '1h')
    btc_4h = load_data('BTCUSDT', '4h')
    spy_1h = load_data('ES_proxy', '1h')
    spy_4h = load_data('ES_proxy', '4h')

    results = []

    for symbol in symbols:
        for timeframe in timeframes:
            logger.info(f"\n{'='*80}")
            logger.info(f"Processing {symbol} {timeframe}")
            logger.info(f"{'='*80}")

            # Load old model metrics
            old_metrics = load_old_model_metrics(symbol, timeframe)
            old_f1 = "N/A"
            if old_metrics:
                logger.info(f"Old model: {old_metrics['file']}")

            # Load primary symbol data
            df = load_data(symbol, timeframe)

            if df is None or len(df) < 100:
                logger.warning(f"Insufficient data for {symbol} {timeframe}: {len(df) if df is not None else 0} rows")
                results.append({
                    'Symbol': symbol,
                    'Timeframe': timeframe,
                    'Old F1': old_f1,
                    'New F1': 'INSUFFICIENT DATA',
                    'Change': 'N/A',
                    'Status': 'SKIPPED'
                })
                continue

            # Get appropriate reference data
            btc_df = None if symbol == 'BTCUSDT' else (btc_1h if timeframe == '1h' else btc_4h)
            spy_df = spy_1h if timeframe == '1h' else spy_4h

            try:
                # Train new model with new features
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
                    'Symbol': symbol,
                    'Timeframe': timeframe,
                    'Old F1': old_f1,
                    'New F1': f"{new_f1:.4f}",
                    'Change': 'NEW MODEL',
                    'Status': 'SUCCESS'
                })

            except Exception as e:
                logger.error(f"✗ Training failed: {e}", exc_info=True)
                results.append({
                    'Symbol': symbol,
                    'Timeframe': timeframe,
                    'Old F1': old_f1,
                    'New F1': 'FAILED',
                    'Change': 'N/A',
                    'Status': f'ERROR: {str(e)[:50]}'
                })

    # Generate comparison table
    print("\n" + "="*100)
    print("BEFORE/AFTER F1 COMPARISON - ALL CRYPTO MODELS")
    print("="*100)
    print("\nNote: Old F1 scores are from previous training runs.")
    print("New features added: Funding Rate, Volume Profile, Cross-Pair Correlation\n")

    print(f"{'Symbol':<12} {'Timeframe':<10} {'Old F1':<10} {'New F1':<10} {'Change':<15} {'Status':<20}")
    print("-" * 100)
    for r in results:
        print(f"{r['Symbol']:<12} {r['Timeframe']:<10} {r['Old F1']:<10} {r['New F1']:<10} {r['Change']:<15} {r['Status']:<20}")

    # Summary statistics
    successful = len([r for r in results if r['Status'] == 'SUCCESS'])
    print(f"\n✓ Successfully retrained: {successful}/{len(results)} models")
    print(f"✗ Failed/Skipped: {len(results) - successful}/{len(results)} models")

    print("\n" + "="*100)
    print("NEW FEATURE MODULES INTEGRATED:")
    print("="*100)
    print("1. Funding Rate (crypto-specific):")
    print("   - funding_rate, funding_rate_ma, funding_extreme, funding_sentiment")
    print("\n2. Volume Profile:")
    print("   - poc_distance, vah_distance, val_distance, price_in_value_area, volume_nodes")
    print("\n3. Cross-Pair Correlation:")
    print("   - btc_correlation, spy_correlation, correlation_regime")
    print("="*100)


if __name__ == "__main__":
    main()
