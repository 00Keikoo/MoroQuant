#!/usr/bin/env python3
"""Triple Barrier Sensitivity Study - Test different TP/SL ATR multipliers.

Tests multiple TP/SL configurations to identify the most balanced class performance.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np

from ml_service.data.database import get_database
from ml_service.models.trainer import (
    create_target_variable_triple_barrier,
    get_feature_columns,
    prepare_features,
    walk_forward_validation,
)
from ml_service.utils.config import get_forward_periods
from ml_service.utils.logger import get_logger, setup_logger

setup_logger()
logger = get_logger()


CONFIGURATIONS = [
    {'name': 'Config 1: TP=1.5 SL=1.5', 'tp': 1.5, 'sl': 1.5},
    {'name': 'Config 2: TP=2.0 SL=1.5', 'tp': 2.0, 'sl': 1.5},
    {'name': 'Config 3: TP=2.0 SL=2.0', 'tp': 2.0, 'sl': 2.0},
    {'name': 'Config 4: TP=2.5 SL=1.5', 'tp': 2.5, 'sl': 1.5},
    {'name': 'Config 5: TP=3.0 SL=1.5', 'tp': 3.0, 'sl': 1.5},
]

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
    counts = pd.Series(y).value_counts(normalize=True) * 100
    return {
        'short_pct': float(counts.get(0, 0.0)),
        'neutral_pct': float(counts.get(1, 0.0)),
        'long_pct': float(counts.get(2, 0.0)),
    }


def compute_balance_score(dist, metrics):
    """Score how balanced the configuration is.

    Lower is better - penalizes class imbalance and F1 variance.
    """
    # Class distribution variance (ideal is 33.3% each)
    target = 33.33
    dist_penalty = (
        abs(dist['short_pct'] - target) +
        abs(dist['neutral_pct'] - target) +
        abs(dist['long_pct'] - target)
    ) / 3.0

    # F1 variance across classes
    f1_values = [metrics['f1_short'], metrics['f1_neutral'], metrics['f1_long']]
    f1_std = float(np.std(f1_values))

    # Combined score: lower = more balanced
    return dist_penalty + (f1_std * 100)


def fold_split_for(clean_len: int):
    if clean_len < 100:
        return int(clean_len * 0.6), int(clean_len * 0.15), int(clean_len * 0.15)
    if clean_len < 300:
        return int(clean_len * 0.7), int(clean_len * 0.15), int(clean_len * 0.15)
    return 400, 50, 50


def run_configuration(df_base, feature_cols, tp_mult, sl_mult, symbol, timeframe):
    """Run training with specified TP/SL multipliers."""
    H = get_forward_periods()

    df = create_target_variable_triple_barrier(
        df_base.copy(),
        holding_horizon=H,
        tp_atr_mult=tp_mult,
        sl_atr_mult=sl_mult,
    )

    df_clean = df[feature_cols + ['target']].dropna()
    distribution = analyze_class_distribution(df_clean['target'])

    min_train, test_size, step_size = fold_split_for(len(df_clean))

    if len(df_clean) < min_train + test_size:
        return None

    fold_results, _ = walk_forward_validation(
        df, feature_cols,
        min_train_size=min_train,
        test_size=test_size,
        step_size=step_size,
        forward_periods=H,
        purge=True,
    )

    metrics = {
        'f1_weighted': float(np.mean([r['f1_weighted'] for r in fold_results])),
        'f1_short': float(np.mean([r['f1_short'] for r in fold_results])),
        'f1_neutral': float(np.mean([r['f1_neutral'] for r in fold_results])),
        'f1_long': float(np.mean([r['f1_long'] for r in fold_results])),
    }

    balance_score = compute_balance_score(distribution, metrics)

    return {
        'tp_mult': tp_mult,
        'sl_mult': sl_mult,
        'distribution': distribution,
        'metrics': metrics,
        'balance_score': balance_score,
        'n_folds': len(fold_results),
    }


def print_report(results, symbol, timeframe):
    print()
    print("="*120)
    print(f"TRIPLE BARRIER SENSITIVITY STUDY: {symbol} {timeframe}")
    print("="*120)
    print()

    header = [
        'Config', 'TP×ATR', 'SL×ATR',
        'Short%', 'Neutral%', 'Long%',
        'wF1', 'F1_Short', 'F1_Neutral', 'F1_Long',
        'Balance'
    ]
    widths = [25, 7, 7, 8, 9, 7, 7, 9, 11, 8, 9]

    def fmt_row(values):
        return '  '.join(str(v).rjust(w) if i > 0 else str(v).ljust(w)
                        for i, (v, w) in enumerate(zip(values, widths)))

    print(fmt_row(header))
    print('-' * (sum(widths) + 2 * (len(widths) - 1)))

    for i, (config, result) in enumerate(zip(CONFIGURATIONS, results), 1):
        if result is None:
            continue

        d = result['distribution']
        m = result['metrics']

        print(fmt_row([
            config['name'],
            f"{result['tp_mult']:.1f}",
            f"{result['sl_mult']:.1f}",
            f"{d['short_pct']:.1f}%",
            f"{d['neutral_pct']:.1f}%",
            f"{d['long_pct']:.1f}%",
            f"{m['f1_weighted']:.3f}",
            f"{m['f1_short']:.3f}",
            f"{m['f1_neutral']:.3f}",
            f"{m['f1_long']:.3f}",
            f"{result['balance_score']:.2f}",
        ]))

    print()
    print("="*120)
    print("ANALYSIS")
    print("="*120)
    print()

    # Find best configurations
    valid_results = [(i, r) for i, r in enumerate(results) if r is not None]

    best_wf1 = max(valid_results, key=lambda x: x[1]['metrics']['f1_weighted'])
    best_balance = min(valid_results, key=lambda x: x[1]['balance_score'])

    print("HIGHEST WEIGHTED F1:")
    print(f"  {CONFIGURATIONS[best_wf1[0]]['name']}")
    print(f"  wF1 = {best_wf1[1]['metrics']['f1_weighted']:.3f}")
    print()

    print("MOST BALANCED CLASS PERFORMANCE:")
    print(f"  {CONFIGURATIONS[best_balance[0]]['name']}")
    print(f"  Balance score = {best_balance[1]['balance_score']:.2f} (lower is better)")

    br = best_balance[1]
    print(f"  Class distribution: Short={br['distribution']['short_pct']:.1f}% "
          f"Neutral={br['distribution']['neutral_pct']:.1f}% "
          f"Long={br['distribution']['long_pct']:.1f}%")
    print(f"  F1 scores: Short={br['metrics']['f1_short']:.3f} "
          f"Neutral={br['metrics']['f1_neutral']:.3f} "
          f"Long={br['metrics']['f1_long']:.3f}")
    print(f"  F1 std dev = {np.std([br['metrics']['f1_short'], br['metrics']['f1_neutral'], br['metrics']['f1_long']]):.3f}")
    print()

    print("KEY OBSERVATIONS:")
    print()

    # Analyze trends
    for i, result in enumerate(results):
        if result is None:
            continue
        config = CONFIGURATIONS[i]
        d = result['distribution']
        m = result['metrics']

        if d['short_pct'] > 50:
            print(f"  • {config['name']}: High short bias ({d['short_pct']:.1f}%) - SL too tight relative to TP")
        if d['long_pct'] < 15:
            print(f"  • {config['name']}: Very low long signals ({d['long_pct']:.1f}%) - TP too far or SL too tight")
        if m['f1_weighted'] > 0.35:
            print(f"  • {config['name']}: Strong overall performance (wF1={m['f1_weighted']:.3f})")

    print()
    print("RECOMMENDATION:")
    print()

    if best_balance[0] == best_wf1[0]:
        print(f"  ✓ USE {CONFIGURATIONS[best_balance[0]]['name']}")
        print("    - Best weighted F1 AND most balanced class performance")
        print("    - Update config.yaml if this differs from current production setting")
    else:
        print(f"  → CHOOSE BASED ON OBJECTIVE:")
        print(f"    - For highest accuracy: {CONFIGURATIONS[best_wf1[0]]['name']} (wF1={best_wf1[1]['metrics']['f1_weighted']:.3f})")
        print(f"    - For balanced classes: {CONFIGURATIONS[best_balance[0]]['name']} (balance={best_balance[1]['balance_score']:.2f})")
        print("    - Balanced approach may generalize better to unseen market conditions")

    print()


def main():
    symbol = 'BTCUSDT'
    timeframe = '1h'

    logger.info(f"Starting barrier sensitivity study for {symbol} {timeframe}")
    logger.info(f"Testing {len(CONFIGURATIONS)} configurations...")

    # Load and prepare data once
    df = load_data(symbol, timeframe)
    if df is None or len(df) < 100:
        logger.error(f"Insufficient data for {symbol} {timeframe}")
        return

    df = prepare_features(df, symbol=symbol, btc_df=None, spy_df=None)
    feature_cols = get_feature_columns(df)

    results = []

    for i, config in enumerate(CONFIGURATIONS, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"Configuration {i}/{len(CONFIGURATIONS)}: {config['name']}")
        logger.info(f"{'='*80}")

        try:
            result = run_configuration(
                df, feature_cols,
                config['tp'], config['sl'],
                symbol, timeframe
            )
            results.append(result)

            if result:
                logger.info(f"wF1={result['metrics']['f1_weighted']:.3f}, "
                           f"Balance={result['balance_score']:.2f}")
        except Exception as e:
            logger.exception(f"Configuration {i} failed: {e}")
            results.append(None)

    print_report(results, symbol, timeframe)


if __name__ == '__main__':
    main()
