#!/usr/bin/env python3
"""Compare Fixed-Horizon vs Triple Barrier Labeling methods.

Trains models using both labeling approaches and compares:
- Class distribution
- Weighted F1, Precision, Recall
- Backtest profitability
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from sklearn.metrics import classification_report, precision_recall_fscore_support

from ml_service.data.database import get_database
from ml_service.models.trainer import (
    create_target_variable,
    create_target_variable_triple_barrier,
    get_feature_columns,
    prepare_features,
    walk_forward_validation,
)
from ml_service.utils.config import get_forward_periods, get_config
from ml_service.utils.logger import get_logger, setup_logger

setup_logger()
logger = get_logger()


DEFAULT_SYMBOLS = ['BTCUSDT', 'ETHUSDT']
DEFAULT_TIMEFRAMES = ['1h']
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


def analyze_class_distribution(y):
    """Return class distribution as percentages."""
    counts = pd.Series(y).value_counts(normalize=True) * 100
    return {
        'short_pct': counts.get(0, 0.0),
        'neutral_pct': counts.get(1, 0.0),
        'long_pct': counts.get(2, 0.0),
    }


def fold_split_for(clean_len: int):
    if clean_len < 100:
        return int(clean_len * 0.6), int(clean_len * 0.15), int(clean_len * 0.15)
    if clean_len < 300:
        return int(clean_len * 0.7), int(clean_len * 0.15), int(clean_len * 0.15)
    return 400, 50, 50


def run_comparison(symbol: str, timeframe: str, btc_df, spy_df):
    """Train with both labeling methods and compare results."""
    df = load_data(symbol, timeframe)
    if df is None or len(df) < 100:
        logger.warning(f"{symbol} {timeframe}: insufficient data")
        return None

    config = get_config()
    H = get_forward_periods()
    tp_mult = config.model.tp_atr_mult if hasattr(config.model, 'tp_atr_mult') else 3.0
    sl_mult = config.model.sl_atr_mult if hasattr(config.model, 'sl_atr_mult') else 1.5

    btc_arg = None if symbol == 'BTCUSDT' else btc_df

    # Prepare features (shared by both methods)
    df = prepare_features(df, symbol=symbol, btc_df=btc_arg, spy_df=spy_df)

    logger.info(f"\n{'='*80}")
    logger.info(f"{symbol} {timeframe} - FIXED HORIZON METHOD")
    logger.info(f"{'='*80}")

    # Method 1: Fixed-horizon
    df_fixed = create_target_variable(
        df.copy(),
        forward_periods=H,
        long_threshold=0.005,
        short_threshold=-0.005,
    )

    feature_cols = get_feature_columns(df_fixed)
    df_clean_fixed = df_fixed[feature_cols + ['target']].dropna()
    clean_len = len(df_clean_fixed)

    fixed_dist = analyze_class_distribution(df_clean_fixed['target'])
    logger.info(f"Class distribution: Short={fixed_dist['short_pct']:.1f}% "
                f"Neutral={fixed_dist['neutral_pct']:.1f}% "
                f"Long={fixed_dist['long_pct']:.1f}%")

    min_train, test_size, step_size = fold_split_for(clean_len)

    if clean_len < min_train + test_size:
        logger.warning(f"Insufficient clean data: {clean_len} < {min_train + test_size}")
        return None

    fixed_folds, _ = walk_forward_validation(
        df_fixed, feature_cols,
        min_train_size=min_train,
        test_size=test_size,
        step_size=step_size,
        forward_periods=H,
        purge=True,
    )

    fixed_metrics = compute_fold_metrics(fixed_folds)

    logger.info(f"\n{'='*80}")
    logger.info(f"{symbol} {timeframe} - TRIPLE BARRIER METHOD (TP={tp_mult}x SL={sl_mult}x ATR)")
    logger.info(f"{'='*80}")

    # Method 2: Triple barrier
    df_triple = create_target_variable_triple_barrier(
        df.copy(),
        holding_horizon=H,
        tp_atr_mult=tp_mult,
        sl_atr_mult=sl_mult,
    )

    df_clean_triple = df_triple[feature_cols + ['target']].dropna()
    triple_dist = analyze_class_distribution(df_clean_triple['target'])
    logger.info(f"Class distribution: Short={triple_dist['short_pct']:.1f}% "
                f"Neutral={triple_dist['neutral_pct']:.1f}% "
                f"Long={triple_dist['long_pct']:.1f}%")

    triple_folds, _ = walk_forward_validation(
        df_triple, feature_cols,
        min_train_size=min_train,
        test_size=test_size,
        step_size=step_size,
        forward_periods=H,
        purge=True,
    )

    triple_metrics = compute_fold_metrics(triple_folds)

    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'clean_rows': clean_len,
        'fixed': {
            'distribution': fixed_dist,
            'metrics': fixed_metrics,
            'n_folds': len(fixed_folds),
        },
        'triple': {
            'distribution': triple_dist,
            'metrics': triple_metrics,
            'n_folds': len(triple_folds),
            'tp_mult': tp_mult,
            'sl_mult': sl_mult,
        },
    }


def compute_fold_metrics(fold_results):
    """Aggregate metrics across folds."""
    if not fold_results:
        return {}

    return {
        'f1_weighted': float(np.mean([r['f1_weighted'] for r in fold_results])),
        'f1_short': float(np.mean([r['f1_short'] for r in fold_results])),
        'f1_neutral': float(np.mean([r['f1_neutral'] for r in fold_results])),
        'f1_long': float(np.mean([r['f1_long'] for r in fold_results])),
    }


def print_comparison_report(results):
    """Print comprehensive comparison report."""
    if not results:
        print("\nNo results to compare.")
        return

    print()
    print("="*120)
    print("FIXED HORIZON vs TRIPLE BARRIER LABELING - COMPARISON REPORT")
    print("="*120)
    print()

    # Summary table
    header = [
        'Pair', 'Rows', 'Method',
        'Short%', 'Neutral%', 'Long%',
        'wF1', 'F1_Short', 'F1_Neutral', 'F1_Long',
    ]
    widths = [12, 6, 8, 8, 9, 7, 7, 9, 11, 8]

    def fmt_row(values):
        return '  '.join(str(v).rjust(w) if i > 0 else str(v).ljust(w)
                        for i, (v, w) in enumerate(zip(values, widths)))

    print(fmt_row(header))
    print('-' * (sum(widths) + 2 * (len(widths) - 1)))

    for r in results:
        pair = f"{r['symbol']}/{r['timeframe']}"

        # Fixed-horizon row
        fixed = r['fixed']
        fd = fixed['distribution']
        fm = fixed['metrics']
        print(fmt_row([
            pair, r['clean_rows'], 'Fixed',
            f"{fd['short_pct']:.1f}%", f"{fd['neutral_pct']:.1f}%", f"{fd['long_pct']:.1f}%",
            f"{fm['f1_weighted']:.3f}",
            f"{fm['f1_short']:.3f}",
            f"{fm['f1_neutral']:.3f}",
            f"{fm['f1_long']:.3f}",
        ]))

        # Triple-barrier row
        triple = r['triple']
        td = triple['distribution']
        tm = triple['metrics']
        print(fmt_row([
            '', '', 'Triple',
            f"{td['short_pct']:.1f}%", f"{td['neutral_pct']:.1f}%", f"{td['long_pct']:.1f}%",
            f"{tm['f1_weighted']:.3f}",
            f"{tm['f1_short']:.3f}",
            f"{tm['f1_neutral']:.3f}",
            f"{tm['f1_long']:.3f}",
        ]))

        # Delta row
        delta_wf1 = tm['f1_weighted'] - fm['f1_weighted']
        delta_short = td['short_pct'] - fd['short_pct']
        delta_neutral = td['neutral_pct'] - fd['neutral_pct']
        delta_long = td['long_pct'] - fd['long_pct']

        print(fmt_row([
            '', '', 'Δ',
            f"{delta_short:+.1f}%", f"{delta_neutral:+.1f}%", f"{delta_long:+.1f}%",
            f"{delta_wf1:+.3f}",
            f"{tm['f1_short'] - fm['f1_short']:+.3f}",
            f"{tm['f1_neutral'] - fm['f1_neutral']:+.3f}",
            f"{tm['f1_long'] - fm['f1_long']:+.3f}",
        ]))
        print()

    print("="*120)
    print("ANALYSIS & RECOMMENDATIONS")
    print("="*120)
    print()

    # Aggregate analysis
    avg_fixed_wf1 = np.mean([r['fixed']['metrics']['f1_weighted'] for r in results])
    avg_triple_wf1 = np.mean([r['triple']['metrics']['f1_weighted'] for r in results])

    avg_fixed_neutral = np.mean([r['fixed']['distribution']['neutral_pct'] for r in results])
    avg_triple_neutral = np.mean([r['triple']['distribution']['neutral_pct'] for r in results])

    avg_fixed_short = np.mean([r['fixed']['metrics']['f1_short'] for r in results])
    avg_triple_short = np.mean([r['triple']['metrics']['f1_short'] for r in results])

    avg_fixed_long = np.mean([r['fixed']['metrics']['f1_long'] for r in results])
    avg_triple_long = np.mean([r['triple']['metrics']['f1_long'] for r in results])

    print("CLASS DISTRIBUTION:")
    print(f"  Fixed-Horizon:   avg neutral = {avg_fixed_neutral:.1f}%")
    print(f"  Triple-Barrier:  avg neutral = {avg_triple_neutral:.1f}%")
    neutral_delta = avg_triple_neutral - avg_fixed_neutral
    print(f"  Δ: {neutral_delta:+.1f}% neutral labels")
    print()

    print("WEIGHTED F1:")
    print(f"  Fixed-Horizon:   {avg_fixed_wf1:.3f}")
    print(f"  Triple-Barrier:  {avg_triple_wf1:.3f}")
    wf1_delta = avg_triple_wf1 - avg_fixed_wf1
    print(f"  Δ: {wf1_delta:+.3f} ({wf1_delta/avg_fixed_wf1*100:+.1f}%)")
    print()

    print("DIRECTIONAL CLASS F1 (Short & Long):")
    print(f"  Fixed Short:  {avg_fixed_short:.3f}  |  Fixed Long:  {avg_fixed_long:.3f}")
    print(f"  Triple Short: {avg_triple_short:.3f}  |  Triple Long: {avg_triple_long:.3f}")
    print(f"  Δ Short: {avg_triple_short - avg_fixed_short:+.3f}  |  Δ Long: {avg_triple_long - avg_fixed_long:+.3f}")
    print()

    print("RECOMMENDATION:")
    print()

    if wf1_delta > 0.05:
        print("  ✓ MIGRATE TO TRIPLE BARRIER")
        print("    - Significantly higher weighted F1")
        print("    - Better aligned with actual trade execution")
        print("    - Path-dependent labeling reduces noise")
    elif wf1_delta < -0.05:
        print("  ✗ KEEP FIXED HORIZON")
        print("    - Triple barrier underperforms on validation metrics")
        print("    - Consider tuning TP/SL multipliers")
    else:
        print("  → RUN BACKTEST COMPARISON")
        print("    - Validation metrics are similar")
        print("    - Profitability comparison needed to decide")
        print("    - Triple barrier may show advantage in live execution alignment")

    print()
    print("NEXT STEPS:")
    print("  1. Run backtest comparison (use backtester.py with both models)")
    print("  2. Compare Sharpe ratio, profit factor, max drawdown")
    print("  3. If triple barrier wins, update config.yaml: labeling_method: triple_barrier")
    print()


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--symbol', action='append', help='Restrict to specific symbols')
    parser.add_argument('--timeframe', action='append', help='Restrict to specific timeframes')
    args = parser.parse_args()

    symbols = args.symbol if args.symbol else DEFAULT_SYMBOLS
    timeframes = args.timeframe if args.timeframe else DEFAULT_TIMEFRAMES

    logger.info("Loading reference data for cross-pair correlations...")
    btc_by_tf = {tf: load_data('BTCUSDT', tf) for tf in timeframes}
    spy_by_tf = {tf: load_data('ES_proxy', tf) for tf in timeframes}

    results = []
    for symbol in symbols:
        for tf in timeframes:
            try:
                result = run_comparison(symbol, tf, btc_by_tf.get(tf), spy_by_tf.get(tf))
                if result:
                    results.append(result)
            except Exception as e:
                logger.exception(f"{symbol} {tf} comparison failed: {e}")
                continue

    print_comparison_report(results)


if __name__ == '__main__':
    main()
