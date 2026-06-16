#!/usr/bin/env python3
"""Validate labeling methods across different market regimes.

Tests whether the walk-forward winner (Triple TP=3.0 SL=1.5) remains
superior across rolling chronological windows to validate robustness.

Uses the same leak-free walk-forward architecture from compare_backtest_methods.py
with purge and embargo logic preserved.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from collections import defaultdict

from ml_service.data.database import get_database
from ml_service.models.trainer import (
    create_target_variable,
    create_target_variable_triple_barrier,
    get_feature_columns,
    prepare_features,
)
from ml_service.utils.config import get_forward_periods
from ml_service.utils.logger import get_logger, setup_logger

from ml_service.compare_backtest_methods import (
    calculate_regions,
    train_model_on_window,
    build_calibration_dataset,
    fit_and_select_calibrator,
    generate_walk_forward_predictions,
    run_backtest_simulation,
)

setup_logger()
logger = get_logger()

DEFAULT_SYMBOLS = ['BTCUSDT']
DEFAULT_TIMEFRAMES = ['1h']


def load_data_full(symbol: str, timeframe: str):
    """Load all available data for regime analysis."""
    db = get_database()
    with db.get_connection() as conn:
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM ohlcv
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp ASC
        """
        df = pd.read_sql_query(query, conn, params=(symbol, timeframe))
    if df.empty:
        return None
    return df.reset_index(drop=True)


def run_single_window(
    df_window: pd.DataFrame,
    labeling_config: Dict,
    symbol: str,
    H: int,
) -> Dict:
    """Run walk-forward backtest on a single window for one labeling method.

    Returns metrics dict with added diagnostics:
    - prediction_dist: {class0, class1, class2}
    - confidence_stats: {mean, median, p90, p95, max}
    - trade_diagnostics: {total, long, short, skipped_by_conf}
    """

    if labeling_config['method'] == 'fixed_horizon':
        df_labeled = create_target_variable(
            df_window.copy(),
            forward_periods=H,
            long_threshold=0.005,
            short_threshold=-0.005,
        )
    else:
        df_labeled = create_target_variable_triple_barrier(
            df_window.copy(),
            holding_horizon=H,
            tp_atr_mult=labeling_config['tp_mult'],
            sl_atr_mult=labeling_config['sl_mult'],
        )

    feature_cols = get_feature_columns(df_labeled)
    required_cols = ['timestamp', 'close'] + feature_cols + ['target']

    missing_cols = [c for c in required_cols if c not in df_labeled.columns]
    if missing_cols:
        logger.warning(f"Missing columns: {missing_cols}")
        return None

    df_clean = df_labeled[required_cols].dropna()
    N = len(df_clean)

    if N < 200:
        logger.warning(f"Insufficient clean data: {N} rows")
        return None

    regions = calculate_regions(N, H)
    df_clean = df_clean.reset_index(drop=True)

    if 'timestamp' not in df_clean.columns or 'close' not in df_clean.columns:
        logger.warning("Missing required columns after reset")
        return None

    try:
        cal_train_probas, cal_train_y, cal_val_probas, cal_val_y = build_calibration_dataset(
            df_clean, feature_cols, regions
        )

        if cal_train_probas is None:
            logger.warning("Failed to build calibration dataset")
            return None

        calibrator = fit_and_select_calibrator(
            cal_train_probas, cal_train_y, cal_val_probas, cal_val_y
        )

        predictions, probas, valid_mask = generate_walk_forward_predictions(
            df_clean, feature_cols, calibrator, regions
        )

        # Calculate prediction diagnostics
        valid_preds = predictions[valid_mask & ~np.isnan(predictions)]
        valid_probas = probas[valid_mask]

        from collections import Counter
        pred_dist = Counter(valid_preds.astype(int))

        max_conf = valid_probas.max(axis=1)
        confidence_stats = {
            'mean': float(np.mean(max_conf)),
            'median': float(np.median(max_conf)),
            'p90': float(np.percentile(max_conf, 90)),
            'p95': float(np.percentile(max_conf, 95)),
            'max': float(np.max(max_conf)),
        }

        # Run backtest with diagnostics
        backtest_result = run_backtest_simulation(
            df_clean, predictions, probas, valid_mask,
            confidence_threshold=0.60,
            regions=regions,
        )

        # Add trade diagnostics
        trades = backtest_result.get('trades', [])
        long_trades = sum(1 for t in trades if t['type'] == 'long')
        short_trades = sum(1 for t in trades if t['type'] == 'short')

        # Calculate skipped signals
        skipped = sum(1 for conf in max_conf if conf < 0.60)

        metrics = backtest_result['metrics']
        metrics['prediction_dist'] = {
            'class0': int(pred_dist.get(0, 0)),
            'class1': int(pred_dist.get(1, 0)),
            'class2': int(pred_dist.get(2, 0)),
        }
        metrics['confidence_stats'] = confidence_stats
        metrics['trade_diagnostics'] = {
            'total': len(trades),
            'long': long_trades,
            'short': short_trades,
            'skipped_by_conf': skipped,
        }

        return metrics

    except Exception as e:
        logger.warning(f"Window failed: {e}")
        return None


def calculate_rank_statistics(window_rankings: List[List[Dict]], all_methods: List[str]) -> Dict:
    """Calculate rank stability statistics for each method."""
    rank_by_method = defaultdict(list)

    for window in window_rankings:
        methods_in_window = {r['method']: r['rank'] for r in window}
        for method in all_methods:
            if method in methods_in_window:
                rank_by_method[method].append(methods_in_window[method])

    stats = {}
    for method, ranks in rank_by_method.items():
        if not ranks:
            continue

        times_best = sum(1 for r in ranks if r == 1)
        times_worst = sum(1 for r in ranks if r == len(all_methods))

        stats[method] = {
            'avg_rank': np.mean(ranks),
            'std_rank': np.std(ranks),
            'times_best': times_best,
            'times_worst': times_worst,
            'n_windows': len(ranks),
        }

    return stats


def run_regime_validation(symbol: str, timeframe: str, btc_df, spy_df,
                         window_size: int = 1000, window_step: int = 200):
    """Run validation across rolling windows."""

    logger.info(f"\n{'='*80}")
    logger.info(f"REGIME VALIDATION: {symbol} {timeframe}")
    logger.info(f"{'='*80}")

    df_full = load_data_full(symbol, timeframe)
    if df_full is None or len(df_full) < window_size:
        logger.warning(f"Insufficient data: {len(df_full) if df_full is not None else 0} rows")
        return None

    H = get_forward_periods()
    btc_arg = None if symbol == 'BTCUSDT' else btc_df

    logger.info(f"Preparing features on full dataset ({len(df_full)} rows)")
    df_full = prepare_features(df_full, symbol=symbol, btc_df=btc_arg, spy_df=spy_df)

    labeling_configs = [
        {'method': 'fixed_horizon', 'name': 'Fixed Horizon'},
        {'method': 'triple_barrier', 'name': 'Triple TP=2.0 SL=2.0', 'tp_mult': 2.0, 'sl_mult': 2.0},
        {'method': 'triple_barrier', 'name': 'Triple TP=2.5 SL=1.5', 'tp_mult': 2.5, 'sl_mult': 1.5},
        {'method': 'triple_barrier', 'name': 'Triple TP=3.0 SL=1.5', 'tp_mult': 3.0, 'sl_mult': 1.5},
    ]

    n_windows = (len(df_full) - window_size) // window_step + 1
    logger.info(f"Creating {n_windows} rolling windows (size={window_size}, step={window_step})")

    results_by_method = defaultdict(lambda: {
        'sharpe': [],
        'return': [],
        'win_rate': [],
        'sortino': [],
        'profit_factor': [],
        'trade_count': [],
    })

    window_rankings = []

    for window_idx in range(n_windows):
        window_start = window_idx * window_step
        window_end = window_start + window_size

        if window_end > len(df_full):
            break

        logger.info(f"\n--- Window {window_idx + 1}/{n_windows}: rows [{window_start}:{window_end}] ---")

        df_window = df_full.iloc[window_start:window_end].copy()
        window_results = []

        for config in labeling_configs:
            logger.info(f"  Testing: {config['name']}")

            metrics = run_single_window(df_window, config, symbol, H)

            if metrics is None or metrics['total_trades'] == 0:
                logger.info(f"    Skipped (no trades or failed)")
                continue

            results_by_method[config['name']]['sharpe'].append(metrics['sharpe_ratio'])
            results_by_method[config['name']]['return'].append(metrics['total_return_pct'])
            results_by_method[config['name']]['win_rate'].append(metrics['win_rate_pct'])
            results_by_method[config['name']]['sortino'].append(metrics['sortino_ratio'])
            results_by_method[config['name']]['profit_factor'].append(metrics['profit_factor'])
            results_by_method[config['name']]['trade_count'].append(metrics['total_trades'])

            window_results.append({
                'method': config['name'],
                'sharpe': metrics['sharpe_ratio'],
            })

            logger.info(f"    Sharpe={metrics['sharpe_ratio']:.2f}, "
                       f"Return={metrics['total_return_pct']:.2f}%, "
                       f"WinRate={metrics['win_rate_pct']:.1f}%")

        if window_results:
            ranked = sorted(window_results, key=lambda x: x['sharpe'], reverse=True)
            for rank, result in enumerate(ranked, 1):
                result['rank'] = rank
            window_rankings.append(ranked)

    rank_stats = calculate_rank_statistics(window_rankings, [c['name'] for c in labeling_configs])

    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'n_windows': n_windows,
        'window_size': window_size,
        'window_step': window_step,
        'results': dict(results_by_method),
        'rank_stats': rank_stats,
    }


def print_regime_report(validation: Dict):
    """Print regime validation summary."""

    if not validation or not validation.get('results'):
        print("\nNo results to report.")
        return

    results = validation['results']
    rank_stats = validation.get('rank_stats', {})
    n_windows = validation['n_windows']
    window_size = validation['window_size']
    window_step = validation['window_step']

    print()
    print("=" * 140)
    print(f"REGIME VALIDATION SUMMARY: {validation['symbol']} {validation['timeframe']}")
    print(f"Windows analyzed: {n_windows} (size={window_size}, step={window_step})")
    print("=" * 140)
    print()

    header = [
        'Labeling Method', 'N', 'Sharpe μ', 'Sharpe σ', 'Return μ', 'WinRate μ',
        'Sortino μ', 'PF μ', 'Consistency'
    ]
    widths = [24, 4, 10, 10, 10, 11, 11, 8, 12]

    def fmt_row(values):
        return '  '.join(str(v).ljust(w) if isinstance(v, str) else str(v).rjust(w)
                        for v, w in zip(values, widths))

    print(fmt_row(header))
    print('-' * (sum(widths) + 2 * (len(widths) - 1)))

    summary = []
    for method, metrics in results.items():
        n_valid = len(metrics['sharpe'])

        if n_valid == 0:
            continue

        sharpe_mean = np.mean(metrics['sharpe'])
        sharpe_std = np.std(metrics['sharpe'])
        return_mean = np.mean(metrics['return'])
        win_rate_mean = np.mean(metrics['win_rate'])
        sortino_mean = np.mean(metrics['sortino'])
        pf_mean = np.mean([pf for pf in metrics['profit_factor'] if pf != float('inf')])

        positive_sharpe = sum(1 for s in metrics['sharpe'] if s > 0)
        consistency = (positive_sharpe / n_valid) * 100 if n_valid > 0 else 0

        summary.append({
            'method': method,
            'n': n_valid,
            'sharpe_mean': sharpe_mean,
            'sharpe_std': sharpe_std,
            'return_mean': return_mean,
            'win_rate_mean': win_rate_mean,
            'sortino_mean': sortino_mean,
            'pf_mean': pf_mean,
            'consistency': consistency,
        })

        print(fmt_row([
            method,
            n_valid,
            f"{sharpe_mean:.2f}",
            f"{sharpe_std:.2f}",
            f"{return_mean:.2f}%",
            f"{win_rate_mean:.1f}%",
            f"{sortino_mean:.2f}",
            f"{pf_mean:.2f}",
            f"{consistency:.0f}%",
        ]))

    print()
    print("=" * 140)
    print("RANKINGS")
    print("=" * 140)
    print()

    ranked_by_sharpe = sorted(summary, key=lambda x: x['sharpe_mean'], reverse=True)
    print("BY SHARPE MEAN (robustness across regimes):")
    print(fmt_row(['Rank', 'Method', 'Sharpe μ', 'Sharpe σ', 'Consistency', 'N']))
    print('-' * 80)
    for i, r in enumerate(ranked_by_sharpe, 1):
        print(f"{i:3d}.  {r['method']:24s}  {r['sharpe_mean']:6.2f}  "
              f"{r['sharpe_std']:8.2f}  {r['consistency']:10.0f}%  {r['n']:3d}")

    print()

    ranked_by_consistency = sorted(summary, key=lambda x: x['consistency'], reverse=True)
    print("BY CONSISTENCY (% of windows with positive Sharpe):")
    print(fmt_row(['Rank', 'Method', 'Consistency', 'Sharpe μ', 'N']))
    print('-' * 80)
    for i, r in enumerate(ranked_by_consistency, 1):
        print(f"{i:3d}.  {r['method']:24s}  {r['consistency']:10.0f}%  "
              f"{r['sharpe_mean']:8.2f}  {r['n']:3d}")

    print()

    if rank_stats:
        rank_summary = []
        for method, stats in rank_stats.items():
            rank_summary.append({
                'method': method,
                'avg_rank': stats['avg_rank'],
                'std_rank': stats['std_rank'],
                'times_best': stats['times_best'],
                'times_worst': stats['times_worst'],
                'n_windows': stats['n_windows'],
            })

        ranked_by_avg_rank = sorted(rank_summary, key=lambda x: x['avg_rank'])

        print("RANK STABILITY ANALYSIS:")
        print(fmt_row(['Method', 'Avg Rank', 'Rank σ', 'Times Best', 'Times Worst', 'N']))
        print('-' * 100)
        for r in ranked_by_avg_rank:
            print(f"{r['method']:24s}  {r['avg_rank']:8.2f}  {r['std_rank']:7.2f}  "
                  f"{r['times_best']:10d}  {r['times_worst']:11d}  {r['n_windows']:3d}")
        print()

    best = ranked_by_sharpe[0]
    print("RECOMMENDATION:")
    print(f"  Most robust method: {best['method']}")
    print(f"  Mean Sharpe: {best['sharpe_mean']:.2f} ± {best['sharpe_std']:.2f}")
    print(f"  Consistency: {best['consistency']:.0f}% positive windows")
    print(f"  Mean Return: {best['return_mean']:.2f}%")

    if rank_stats and best['method'] in rank_stats:
        rs = rank_stats[best['method']]
        print(f"  Rank stability: Avg rank {rs['avg_rank']:.2f}, Won {rs['times_best']} of {rs['n_windows']} windows")
    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--symbol', action='append', help='Restrict to specific symbols')
    parser.add_argument('--timeframe', action='append', help='Restrict to specific timeframes')
    parser.add_argument('--window-size', type=int, default=1000,
                       help='Window size (default: 1000)')
    parser.add_argument('--window-step', type=int, default=200,
                       help='Window step size (default: 200)')
    args = parser.parse_args()

    symbols = args.symbol if args.symbol else DEFAULT_SYMBOLS
    timeframes = args.timeframe if args.timeframe else DEFAULT_TIMEFRAMES

    logger.info("Loading reference data...")
    btc_by_tf = {}
    spy_by_tf = {}

    for symbol in symbols:
        for tf in timeframes:
            try:
                validation = run_regime_validation(
                    symbol, tf, btc_by_tf.get(tf), spy_by_tf.get(tf),
                    window_size=args.window_size,
                    window_step=args.window_step
                )
                if validation:
                    print_regime_report(validation)
            except Exception as e:
                logger.exception(f"{symbol} {tf} regime validation failed: {e}")
                continue


if __name__ == '__main__':
    main()
