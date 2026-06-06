#!/usr/bin/env python3
"""Auto-retrain scheduler for ML models."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import csv
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ml_service.data.database import get_database
from ml_service.data.ingestion import fetch_all
from ml_service.data.coingecko import get_coingecko_fetcher
from ml_service.models.trainer import train_model
from ml_service.utils.logger import setup_logger, get_logger

setup_logger()
logger = get_logger()

SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'HYPEUSDT']
TIMEFRAMES = ['1h', '4h']
F1_THRESHOLD = 0.95
RETRAIN_LOG_PATH = Path(__file__).parent / 'storage' / 'logs' / 'retrain_log.csv'

_scheduler = None
_last_retrain_time = None
_last_retrain_results = []


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


def get_current_model_f1(symbol: str, timeframe: str) -> float:
    """Get F1 score of current model from metadata file."""
    model_dir = Path(__file__).parent / 'storage' / 'models'
    metadata_file = model_dir / f"{symbol}_{timeframe}_metadata.txt"

    if not metadata_file.exists():
        return 0.0

    try:
        with open(metadata_file, 'r') as f:
            for line in f:
                if 'avg_f1_weighted' in line:
                    return float(line.split(':')[1].strip())
    except Exception as e:
        logger.warning(f"Could not read F1 from metadata: {e}")

    return 0.0


def retrain_job():
    """Main retraining job - runs every 24 hours."""
    global _last_retrain_time, _last_retrain_results

    logger.info("="*80)
    logger.info("Starting scheduled retrain job")
    logger.info("="*80)

    _last_retrain_time = datetime.now()
    _last_retrain_results = []

    logger.info("Step 1: Fetching latest data (last 7 days)...")
    try:
        fetch_all(days_back=7)
        logger.info("Data fetch complete")
    except Exception as e:
        logger.error(f"Data fetch failed: {e}")
        return

    logger.info("Step 2: Loading reference data...")
    btc_1h = load_data('BTCUSDT', '1h')
    btc_4h = load_data('BTCUSDT', '4h')
    eth_1h = load_data('ETHUSDT', '1h')
    eth_4h = load_data('ETHUSDT', '4h')
    spy_1h = load_data('ES_proxy', '1h')
    spy_4h = load_data('ES_proxy', '4h')

    logger.info("Step 3: Loading market dominance data...")
    fetcher = get_coingecko_fetcher()
    dominance_df = fetcher.get_dominance_dataframe()
    logger.info(f"Loaded {len(dominance_df)} market dominance records")

    logger.info("Step 4: Retraining all models...")

    for symbol in SYMBOLS:
        for timeframe in TIMEFRAMES:
            logger.info(f"\nTraining {symbol} {timeframe}")

            df = load_data(symbol, timeframe)

            if df is None or len(df) < 100:
                logger.warning(f"Insufficient data for {symbol} {timeframe}")
                _last_retrain_results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'status': 'skipped',
                    'reason': 'insufficient_data',
                    'old_f1': 0.0,
                    'new_f1': 0.0,
                })
                continue

            old_f1 = get_current_model_f1(symbol, timeframe)

            btc_df = None if symbol == 'BTCUSDT' else (btc_1h if timeframe == '1h' else btc_4h)
            eth_df = eth_1h if timeframe == '1h' else eth_4h
            spy_df = spy_1h if timeframe == '1h' else spy_4h

            try:
                train_results = train_model(
                    df=df,
                    symbol=symbol,
                    timeframe=timeframe,
                    btc_df=btc_df,
                    eth_df=eth_df,
                    spy_df=spy_df,
                    dominance_df=dominance_df,
                )

                new_f1 = train_results['avg_f1_weighted']

                if new_f1 >= old_f1 * F1_THRESHOLD:
                    logger.info(f"✓ Model accepted: old={old_f1:.4f}, new={new_f1:.4f}")
                    status = 'replaced'
                else:
                    logger.warning(f"✗ Model rejected: old={old_f1:.4f}, new={new_f1:.4f} (below threshold)")
                    status = 'rejected'

                _last_retrain_results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'status': status,
                    'reason': '',
                    'old_f1': old_f1,
                    'new_f1': new_f1,
                })

            except Exception as e:
                logger.error(f"Training failed for {symbol} {timeframe}: {e}")
                _last_retrain_results.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'status': 'failed',
                    'reason': str(e),
                    'old_f1': old_f1,
                    'new_f1': 0.0,
                })

    logger.info("Step 5: Logging results...")
    log_retrain_results(_last_retrain_results)

    logger.info("="*80)
    logger.info("Scheduled retrain job complete")
    logger.info("="*80)


def market_dominance_job():
    """Fetch market dominance data from CoinGecko - runs every hour."""
    logger.info("Fetching market dominance data from CoinGecko...")

    try:
        fetcher = get_coingecko_fetcher()
        success = fetcher.fetch_and_store()

        if success:
            logger.info("Market dominance data updated successfully")
        else:
            logger.warning("Failed to update market dominance data")
    except Exception as e:
        logger.error(f"Market dominance fetch failed: {e}")


def log_retrain_results(results):
    """Log retrain results to CSV."""
    RETRAIN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    file_exists = RETRAIN_LOG_PATH.exists()

    with open(RETRAIN_LOG_PATH, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'timestamp', 'symbol', 'timeframe', 'status', 'old_f1', 'new_f1', 'reason'
        ])

        if not file_exists:
            writer.writeheader()

        timestamp = datetime.now().isoformat()
        for result in results:
            writer.writerow({
                'timestamp': timestamp,
                'symbol': result['symbol'],
                'timeframe': result['timeframe'],
                'status': result['status'],
                'old_f1': result['old_f1'],
                'new_f1': result['new_f1'],
                'reason': result['reason'],
            })


def start_scheduler():
    """Start the background scheduler."""
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        logger.warning("Scheduler already running")
        return

    _scheduler = BackgroundScheduler(daemon=True)

    _scheduler.add_job(
        retrain_job,
        trigger=IntervalTrigger(hours=24),
        id='retrain_job',
        name='Auto-retrain all models',
        replace_existing=True,
    )

    _scheduler.add_job(
        market_dominance_job,
        trigger=IntervalTrigger(hours=1),
        id='market_dominance_job',
        name='Fetch market dominance from CoinGecko',
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("Scheduler started - retrain every 24h, market dominance every 1h")


def stop_scheduler():
    """Stop the background scheduler."""
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")
    else:
        logger.warning("Scheduler not running")


def get_scheduler_status():
    """Get scheduler status information."""
    if _scheduler is None or not _scheduler.running:
        return {
            'running': False,
            'last_retrain': None,
            'next_retrain': None,
            'results': [],
        }

    next_run = _scheduler.get_job('retrain_job').next_run_time if _scheduler.get_job('retrain_job') else None

    return {
        'running': True,
        'last_retrain': _last_retrain_time.isoformat() if _last_retrain_time else None,
        'next_retrain': next_run.isoformat() if next_run else None,
        'results': _last_retrain_results,
    }
