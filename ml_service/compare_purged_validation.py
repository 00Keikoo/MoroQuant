#!/usr/bin/env python3
"""Compare walk-forward validation with and without purge/embargo.

Runs the same walk_forward_validation twice on each (symbol, timeframe) —
once with purge=False (the prior behavior, leaky), once with purge=True
(H-bar purge between train and test, H-bar embargo between folds). Prints
a side-by-side report so the impact of honest validation is visible.

Usage:
    python -m ml_service.compare_purged_validation
    python -m ml_service.compare_purged_validation --symbol BTCUSDT --timeframe 1h
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd

from ml_service.data.database import get_database
from ml_service.models.trainer import (
    create_target_variable,
    get_feature_columns,
    prepare_features,
    walk_forward_validation,
)
from ml_service.utils.config import get_forward_periods
from ml_service.utils.logger import get_logger, setup_logger

setup_logger()
logger = get_logger()


DEFAULT_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'HYPEUSDT']
DEFAULT_TIMEFRAMES = ['1h', '4h']
FORWARD_PERIODS = get_forward_periods()
LONG_THRESHOLD = 0.005
SHORT_THRESHOLD = -0.005
DATA_LIMIT = 2000


def load_data(symbol: str, timeframe: str, limit: int = DATA_LIMIT):
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
    return df.sort_values('timestamp').reset_index(drop=True)


def summarize_folds(fold_results):
    if not fold_results:
        return {
            'n_folds': 0,
            'f1_weighted': float('nan'),
            'f1_short': float('nan'),
            'f1_neutral': float('nan'),
            'f1_long': float('nan'),
            'total_train_samples': 0,
            'total_test_samples': 0,
        }
    return {
        'n_folds': len(fold_results),
        'f1_weighted': float(np.mean([r['f1_weighted'] for r in fold_results])),
        'f1_short': float(np.mean([r['f1_short'] for r in fold_results])),
        'f1_neutral': float(np.mean([r['f1_neutral'] for r in fold_results])),
        'f1_long': float(np.mean([r['f1_long'] for r in fold_results])),
        'total_train_samples': int(sum(r['train_size'] for r in fold_results)),
        'total_test_samples': int(sum(r['test_size'] for r in fold_results)),
    }


def fold_split_for(df_clean_len: int):
    """Match the adaptive split logic in train_model()."""
    if df_clean_len < 100:
        return int(df_clean_len * 0.6), int(df_clean_len * 0.15), int(df_clean_len * 0.15)
    if df_clean_len < 300:
        return int(df_clean_len * 0.7), int(df_clean_len * 0.15), int(df_clean_len * 0.15)
    return 400, 50, 50


def run_pair(symbol: str, timeframe: str, btc_df, spy_df):
    df = load_data(symbol, timeframe)
    if df is None or len(df) < 100:
        logger.warning(f"Insufficient data for {symbol} {timeframe}")
        return None

    btc_arg = None if symbol == 'BTCUSDT' else btc_df
    df = prepare_features(df, symbol=symbol, btc_df=btc_arg, spy_df=spy_df)
    df = create_target_variable(
        df,
        forward_periods=FORWARD_PERIODS,
        long_threshold=LONG_THRESHOLD,
        short_threshold=SHORT_THRESHOLD,
    )

    feature_cols = get_feature_columns(df)
    df_clean_len = len(df[feature_cols + ['target']].dropna())
    min_train, test_size, step_size = fold_split_for(df_clean_len)

    if df_clean_len < min_train + test_size:
        logger.warning(
            f"{symbol} {timeframe}: clean rows {df_clean_len} < min_train+test "
            f"{min_train + test_size}"
        )
        return None

    common_kwargs = dict(
        min_train_size=min_train,
        test_size=test_size,
        step_size=step_size,
        forward_periods=FORWARD_PERIODS,
    )

    logger.info(f"{symbol} {timeframe}: BEFORE (no purge)")
    before_folds, _ = walk_forward_validation(df, feature_cols, purge=False, **common_kwargs)

    logger.info(f"{symbol} {timeframe}: AFTER (purge={FORWARD_PERIODS}, embargo={FORWARD_PERIODS})")
    after_folds, _ = walk_forward_validation(df, feature_cols, purge=True, **common_kwargs)

    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'clean_rows': df_clean_len,
        'before': summarize_folds(before_folds),
        'after': summarize_folds(after_folds),
    }


def print_report(rows):
    if not rows:
        print("No results.")
        return

    header_cols = [
        'pair', 'clean',
        'folds_b', 'folds_a',
        'wF1_b', 'wF1_a', 'd_wF1',
        'short_b', 'short_a',
        'neutral_b', 'neutral_a',
        'long_b', 'long_a',
        'train_b', 'train_a',
        'test_b', 'test_a',
    ]
    widths = [12, 6, 7, 7, 7, 7, 7, 7, 7, 9, 9, 6, 6, 8, 8, 7, 7]

    def fmt_row(values):
        return '  '.join(str(v).rjust(w) for v, w in zip(values, widths))

    print()
    print('Purged Walk-Forward Validation — Before vs After')
    print('=' * (sum(widths) + 2 * (len(widths) - 1)))
    print(fmt_row(header_cols))
    print('-' * (sum(widths) + 2 * (len(widths) - 1)))

    for r in rows:
        b, a = r['before'], r['after']
        d_wf1 = a['f1_weighted'] - b['f1_weighted']
        print(fmt_row([
            f"{r['symbol']}/{r['timeframe']}",
            r['clean_rows'],
            b['n_folds'], a['n_folds'],
            f"{b['f1_weighted']:.3f}", f"{a['f1_weighted']:.3f}", f"{d_wf1:+.3f}",
            f"{b['f1_short']:.3f}", f"{a['f1_short']:.3f}",
            f"{b['f1_neutral']:.3f}", f"{a['f1_neutral']:.3f}",
            f"{b['f1_long']:.3f}", f"{a['f1_long']:.3f}",
            b['total_train_samples'], a['total_train_samples'],
            b['total_test_samples'], a['total_test_samples'],
        ]))

    print()
    print('Legend: _b = before (no purge), _a = after (purge + embargo).')
    print(f'        purge=embargo={FORWARD_PERIODS} bars (H = forward_periods).')
    print('        wF1 = weighted F1 across folds; short/neutral/long = per-class F1.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--symbol', action='append', help='Restrict to one or more symbols')
    parser.add_argument('--timeframe', action='append', help='Restrict to one or more timeframes')
    args = parser.parse_args()

    symbols = args.symbol if args.symbol else DEFAULT_SYMBOLS
    timeframes = args.timeframe if args.timeframe else DEFAULT_TIMEFRAMES

    logger.info("Loading reference data for cross-pair correlations...")
    btc_by_tf = {tf: load_data('BTCUSDT', tf) for tf in timeframes}
    spy_by_tf = {tf: load_data('ES_proxy', tf) for tf in timeframes}

    rows = []
    for symbol in symbols:
        for tf in timeframes:
            logger.info(f"--- {symbol} {tf} ---")
            try:
                row = run_pair(symbol, tf, btc_by_tf.get(tf), spy_by_tf.get(tf))
            except Exception as e:
                logger.exception(f"{symbol} {tf} failed: {e}")
                continue
            if row is not None:
                rows.append(row)

    print_report(rows)


if __name__ == '__main__':
    main()
