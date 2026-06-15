#!/usr/bin/env python3
"""Compare probability calibration methods (raw / Platt / isotonic).

For each (symbol, timeframe):
  - Run walk-forward validation with collect_calibration_holdout=True.
  - Take the LAST fold's (predict_proba, y_test).
  - Fit raw / Platt / isotonic calibrators on that hold-out.
  - Score Brier, log loss, and ECE for each method.
  - Write a reliability-diagram PNG to storage/calibration/.
  - Print a single side-by-side comparison table at the end.

Does not retrain or persist anything to production. Use this to inspect
calibration quality without disturbing the live model artifacts.

Usage:
    python -m ml_service.compare_calibration
    python -m ml_service.compare_calibration --symbol BTCUSDT --timeframe 1h
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from ml_service.data.database import get_database
from ml_service.models import calibration as cal_mod
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


def fold_split_for(clean_len: int):
    if clean_len < 100:
        return int(clean_len * 0.6), int(clean_len * 0.15), int(clean_len * 0.15)
    if clean_len < 300:
        return int(clean_len * 0.7), int(clean_len * 0.15), int(clean_len * 0.15)
    return 400, 50, 50


def run_pair(symbol: str, timeframe: str, btc_df, spy_df, out_dir: Path):
    df = load_data(symbol, timeframe)
    if df is None or len(df) < 100:
        logger.warning(f"{symbol} {timeframe}: insufficient data")
        return None

    H = get_forward_periods()
    btc_arg = None if symbol == 'BTCUSDT' else btc_df

    df = prepare_features(df, symbol=symbol, btc_df=btc_arg, spy_df=spy_df)
    df = create_target_variable(
        df,
        forward_periods=H,
        long_threshold=LONG_THRESHOLD,
        short_threshold=SHORT_THRESHOLD,
    )

    feature_cols = get_feature_columns(df)
    clean_len = len(df[feature_cols + ['target']].dropna())
    min_train, test_size, step_size = fold_split_for(clean_len)

    if clean_len < min_train + test_size:
        logger.warning(f"{symbol} {timeframe}: clean={clean_len} < min_train+test {min_train+test_size}")
        return None

    fold_results, _ = walk_forward_validation(
        df, feature_cols,
        min_train_size=min_train,
        test_size=test_size,
        step_size=step_size,
        forward_periods=H,
        purge=True,
        collect_calibration_holdout=True,
    )

    if not fold_results:
        logger.warning(f"{symbol} {timeframe}: no folds produced")
        return None

    holdout = fold_results[-1].get('calibration_holdout')
    if not holdout:
        logger.warning(f"{symbol} {timeframe}: no calibration hold-out captured")
        return None

    probas = holdout['probas']
    y = holdout['y']

    calibrators, metrics, calibrated = cal_mod.fit_and_score_all(probas, y)
    chosen = cal_mod.pick_best_method(metrics)

    png_path = out_dir / f"{symbol}_{timeframe}_reliability.png"
    cal_mod.plot_reliability(
        method_to_probas=calibrated,
        y=y,
        title=f"{symbol} {timeframe} — reliability diagram (holdout n={len(y)})",
        out_path=png_path,
    )

    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'holdout_size': len(y),
        'model_type': holdout['model_type'],
        'metrics': metrics,
        'chosen': chosen,
        'png_path': png_path,
    }


def print_report(rows):
    if not rows:
        print("No results.")
        return

    header = [
        'pair', 'model', 'n',
        'brier_raw', 'brier_platt', 'brier_iso',
        'logloss_raw', 'logloss_platt', 'logloss_iso',
        'ece_raw', 'ece_platt', 'ece_iso',
        'chosen',
    ]
    widths = [12, 8, 5, 9, 11, 9, 11, 13, 11, 7, 9, 7, 8]

    def fmt(values):
        return '  '.join(str(v).rjust(w) for v, w in zip(values, widths))

    print()
    print('Probability Calibration — Before vs After')
    print('=' * (sum(widths) + 2 * (len(widths) - 1)))
    print(fmt(header))
    print('-' * (sum(widths) + 2 * (len(widths) - 1)))

    for r in rows:
        m = r['metrics']
        print(fmt([
            f"{r['symbol']}/{r['timeframe']}",
            r['model_type'],
            r['holdout_size'],
            f"{m['raw']['brier']:.3f}", f"{m['platt']['brier']:.3f}", f"{m['isotonic']['brier']:.3f}",
            f"{m['raw']['log_loss']:.3f}", f"{m['platt']['log_loss']:.3f}", f"{m['isotonic']['log_loss']:.3f}",
            f"{m['raw']['ece']:.3f}", f"{m['platt']['ece']:.3f}", f"{m['isotonic']['ece']:.3f}",
            r['chosen'],
        ]))

    print()
    print('Lower is better for all three metrics.')
    print('Chosen by lowest ECE; ties broken by log loss, then Brier.')
    print('Reliability PNGs written under storage/calibration/.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--symbol', action='append', help='Restrict to one or more symbols')
    parser.add_argument('--timeframe', action='append', help='Restrict to one or more timeframes')
    args = parser.parse_args()

    symbols = args.symbol if args.symbol else DEFAULT_SYMBOLS
    timeframes = args.timeframe if args.timeframe else DEFAULT_TIMEFRAMES

    out_dir = Path(__file__).parent / 'storage' / 'calibration'
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading reference data for cross-pair correlations...")
    btc_by_tf = {tf: load_data('BTCUSDT', tf) for tf in timeframes}
    spy_by_tf = {tf: load_data('ES_proxy', tf) for tf in timeframes}

    rows = []
    for symbol in symbols:
        for tf in timeframes:
            logger.info(f"--- {symbol} {tf} ---")
            try:
                row = run_pair(symbol, tf, btc_by_tf.get(tf), spy_by_tf.get(tf), out_dir)
            except Exception as e:
                logger.exception(f"{symbol} {tf} failed: {e}")
                continue
            if row is not None:
                rows.append(row)

    print_report(rows)


if __name__ == '__main__':
    main()
