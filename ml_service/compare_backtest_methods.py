#!/usr/bin/env python3
"""Compare labeling methods and confidence thresholds via backtesting.

Trains models with:
  - Fixed Horizon
  - Triple Barrier (TP=2.0, SL=2.0)
  - Triple Barrier (TP=2.5, SL=1.5)
  - Triple Barrier (TP=3.0, SL=1.5)

Tests each with confidence filters: None, >=60%, >=70%

Reports: Return, Sharpe, Sortino, Profit Factor, Max DD, Win Rate, Trades, Avg Trade
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple

from ml_service.data.database import get_database
from ml_service.models.trainer import (
    create_target_variable,
    create_target_variable_triple_barrier,
    get_feature_columns,
    prepare_features,
    walk_forward_validation,
    train_final_model,
)
from ml_service.models import calibration as cal_mod
from ml_service.utils.config import get_forward_periods
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


def fold_split_for(clean_len: int):
    if clean_len < 100:
        return int(clean_len * 0.6), int(clean_len * 0.15), int(clean_len * 0.15)
    if clean_len < 300:
        return int(clean_len * 0.7), int(clean_len * 0.15), int(clean_len * 0.15)
    return 400, 50, 50


def train_with_labeling_method(
    df: pd.DataFrame,
    symbol: str,
    labeling_config: Dict,
    feature_cols: List[str],
    H: int,
) -> Tuple[object, Dict, str]:
    """Train model with specified labeling method and fit calibrator.

    Returns:
        (model, calibrator, model_type)
    """
    method = labeling_config['method']

    if method == 'fixed_horizon':
        df_labeled = create_target_variable(
            df.copy(),
            forward_periods=H,
            long_threshold=0.005,
            short_threshold=-0.005,
        )
    else:
        df_labeled = create_target_variable_triple_barrier(
            df.copy(),
            holding_horizon=H,
            tp_atr_mult=labeling_config['tp_mult'],
            sl_atr_mult=labeling_config['sl_mult'],
        )

    df_clean = df_labeled[feature_cols + ['target']].dropna()
    clean_len = len(df_clean)

    min_train, test_size, step_size = fold_split_for(clean_len)

    if clean_len < min_train + test_size:
        logger.warning(f"Insufficient clean data: {clean_len}")
        return None, None, None

    fold_results, _ = walk_forward_validation(
        df_labeled, feature_cols,
        min_train_size=min_train,
        test_size=test_size,
        step_size=step_size,
        forward_periods=H,
        purge=True,
        collect_calibration_holdout=True,
    )

    if not fold_results:
        return None, None, None

    holdout = fold_results[-1].get('calibration_holdout')
    if not holdout:
        logger.warning("No calibration holdout captured")
        return None, None, None

    best_model_type = fold_results[-1]['model_type']
    model, _ = train_final_model(df_labeled, feature_cols, model_type=best_model_type)

    probas = holdout['probas']
    y = holdout['y']
    calibrators, metrics, _ = cal_mod.fit_and_score_all(probas, y)
    chosen_method = cal_mod.pick_best_method(metrics)
    calibrator = calibrators[chosen_method]

    logger.info(f"{method} trained: {best_model_type}, calibrator: {chosen_method}")

    return model, calibrator, best_model_type


def run_backtest_with_confidence(
    df: pd.DataFrame,
    model: object,
    calibrator: Dict,
    feature_cols: List[str],
    confidence_threshold: Optional[float],
    initial_capital: float = 10000.0,
    fee_rate: float = 0.0004,
    max_hold_candles: int = None,
) -> Dict:
    """Run backtest with optional confidence filtering."""

    warmup = 250
    if len(df) < warmup:
        return None

    df_features_clean = df[feature_cols].copy()

    valid_mask = df_features_clean.notna().all(axis=1)
    predictions = np.full(len(df_features_clean), 1)
    probas_all = np.zeros((len(df_features_clean), 3))

    if valid_mask.any():
        X_valid = df_features_clean[valid_mask]
        probas_raw = model.predict_proba(X_valid)
        probas_calibrated = cal_mod.apply_calibrator(calibrator, probas_raw)

        if confidence_threshold is not None:
            max_conf = probas_calibrated.max(axis=1)
            high_conf_mask = max_conf >= confidence_threshold
            predictions_temp = np.full(len(probas_calibrated), 1)
            predictions_temp[high_conf_mask] = np.argmax(probas_calibrated[high_conf_mask], axis=1)
            predictions[valid_mask] = predictions_temp
        else:
            predictions[valid_mask] = np.argmax(probas_calibrated, axis=1)

        probas_all[valid_mask] = probas_calibrated

    direction_map = {0: 'short', 1: 'neutral', 2: 'long'}
    signals = [direction_map.get(p, 'neutral') for p in predictions]

    capital = initial_capital
    position = None
    trades = []
    equity_curve = []

    for i in range(warmup, len(df)):
        row = df.iloc[i]
        signal = signals[i]

        equity_curve.append({
            'timestamp': int(row['timestamp']),
            'equity': capital,
            'signal': signal,
        })

        if position is not None:
            hold_duration = i - position['entry_idx']

            should_close = False
            if position['type'] == 'long' and signal == 'short':
                should_close = True
            elif position['type'] == 'short' and signal == 'long':
                should_close = True
            elif hold_duration >= max_hold_candles:
                should_close = True

            if should_close:
                entry_price = position['entry_price']
                position_capital = position['capital']

                if position['type'] == 'long':
                    pnl_pct = (row['close'] - entry_price) / entry_price
                else:
                    pnl_pct = (entry_price - row['close']) / entry_price

                pnl = position_capital * pnl_pct
                fee = (position_capital + pnl) * fee_rate
                final_pnl = pnl - fee

                capital = position_capital + final_pnl

                trades.append({
                    'type': position['type'],
                    'entry_price': entry_price,
                    'exit_price': row['close'],
                    'pnl': final_pnl,
                    'pnl_pct': (final_pnl / position_capital) * 100,
                })

                position = None

        else:
            if signal == 'long':
                fee = capital * fee_rate
                position = {
                    'type': 'long',
                    'entry_price': row['close'],
                    'entry_idx': i,
                    'capital': capital - fee,
                }
            elif signal == 'short':
                fee = capital * fee_rate
                position = {
                    'type': 'short',
                    'entry_price': row['close'],
                    'entry_idx': i,
                    'capital': capital - fee,
                }

    if position is not None:
        last_row = df.iloc[-1]
        entry_price = position['entry_price']
        position_capital = position['capital']

        if position['type'] == 'long':
            pnl_pct = (last_row['close'] - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - last_row['close']) / entry_price

        pnl = position_capital * pnl_pct
        fee = (position_capital + pnl) * fee_rate
        final_pnl = pnl - fee

        capital = position_capital + final_pnl

        trades.append({
            'type': position['type'],
            'entry_price': entry_price,
            'exit_price': last_row['close'],
            'pnl': final_pnl,
            'pnl_pct': (final_pnl / position_capital) * 100,
        })

    metrics = calculate_metrics(trades, equity_curve, initial_capital, capital)

    return {
        'metrics': metrics,
        'trades': trades,
        'equity_curve': equity_curve,
    }


def calculate_metrics(trades: List[Dict], equity_curve: List[Dict], initial_capital: float, final_capital: float) -> Dict:
    """Calculate performance metrics including Sortino."""

    if not trades:
        return {
            'total_return_pct': 0,
            'sharpe_ratio': 0,
            'sortino_ratio': 0,
            'win_rate_pct': 0,
            'profit_factor': 0,
            'max_drawdown_pct': 0,
            'total_trades': 0,
            'avg_trade_pct': 0,
        }

    total_return_pct = ((final_capital - initial_capital) / initial_capital) * 100

    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] <= 0]

    win_rate_pct = (len(winning_trades) / len(trades)) * 100 if trades else 0

    total_profit = sum(t['pnl'] for t in winning_trades)
    total_loss = abs(sum(t['pnl'] for t in losing_trades))
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

    equity_series = [e['equity'] for e in equity_curve]
    peak = equity_series[0]
    max_drawdown = 0
    for equity in equity_series:
        if equity > peak:
            peak = equity
        drawdown = (peak - equity) / peak
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    max_drawdown_pct = max_drawdown * 100

    returns = [t['pnl_pct'] for t in trades]
    if len(returns) > 1:
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        sharpe_ratio = (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0

        negative_returns = [r for r in returns if r < 0]
        if negative_returns:
            downside_std = np.std(negative_returns)
            sortino_ratio = (mean_return / downside_std) * np.sqrt(252) if downside_std > 0 else 0
        else:
            sortino_ratio = sharpe_ratio
    else:
        sharpe_ratio = 0
        sortino_ratio = 0

    avg_trade_pct = np.mean(returns) if returns else 0

    return {
        'total_return_pct': round(total_return_pct, 2),
        'sharpe_ratio': round(sharpe_ratio, 2),
        'sortino_ratio': round(sortino_ratio, 2),
        'win_rate_pct': round(win_rate_pct, 2),
        'profit_factor': round(profit_factor, 2),
        'max_drawdown_pct': round(max_drawdown_pct, 2),
        'total_trades': len(trades),
        'avg_trade_pct': round(avg_trade_pct, 2),
    }


def run_comparison(symbol: str, timeframe: str, btc_df, spy_df):
    """Run full comparison across labeling methods and confidence thresholds."""

    df = load_data(symbol, timeframe)
    if df is None or len(df) < 100:
        logger.warning(f"{symbol} {timeframe}: insufficient data")
        return None

    H = get_forward_periods()

    btc_arg = None if symbol == 'BTCUSDT' else btc_df
    df = prepare_features(df, symbol=symbol, btc_df=btc_arg, spy_df=spy_df)
    feature_cols = get_feature_columns(df)

    labeling_configs = [
        {'method': 'fixed_horizon', 'name': 'Fixed Horizon'},
        {'method': 'triple_barrier', 'name': 'Triple TP=2.0 SL=2.0', 'tp_mult': 2.0, 'sl_mult': 2.0},
        {'method': 'triple_barrier', 'name': 'Triple TP=2.5 SL=1.5', 'tp_mult': 2.5, 'sl_mult': 1.5},
        {'method': 'triple_barrier', 'name': 'Triple TP=3.0 SL=1.5', 'tp_mult': 3.0, 'sl_mult': 1.5},
    ]

    confidence_thresholds = [
        (None, 'No Filter'),
        (0.60, 'Conf >= 60%'),
        (0.70, 'Conf >= 70%'),
    ]

    results = []

    for config in labeling_configs:
        logger.info(f"\n{'='*80}")
        logger.info(f"Training: {config['name']}")
        logger.info(f"{'='*80}")

        model, calibrator, model_type = train_with_labeling_method(
            df, symbol, config, feature_cols, H
        )

        if model is None:
            logger.warning(f"Training failed for {config['name']}")
            continue

        for threshold, threshold_name in confidence_thresholds:
            logger.info(f"  Running backtest: {threshold_name}")

            backtest_result = run_backtest_with_confidence(
                df, model, calibrator, feature_cols,
                confidence_threshold=threshold,
                max_hold_candles=H,
            )

            if backtest_result is None:
                continue

            results.append({
                'labeling': config['name'],
                'confidence': threshold_name,
                'metrics': backtest_result['metrics'],
            })

    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'results': results,
    }


def print_comparison_report(comparison: Dict):
    """Print formatted comparison table with rankings."""

    if not comparison or not comparison.get('results'):
        print("\nNo results to compare.")
        return

    results = comparison['results']

    print()
    print("=" * 140)
    print(f"BACKTEST COMPARISON: {comparison['symbol']} {comparison['timeframe']}")
    print("=" * 140)
    print()

    header = [
        'Labeling Method', 'Confidence', 'Return%', 'Sharpe', 'Sortino',
        'PF', 'MaxDD%', 'WinRate%', 'Trades', 'AvgTrade%'
    ]
    widths = [24, 15, 10, 8, 9, 7, 9, 10, 8, 11]

    def fmt_row(values):
        return '  '.join(str(v).ljust(w) if isinstance(v, str) else str(v).rjust(w)
                        for v, w in zip(values, widths))

    print(fmt_row(header))
    print('-' * (sum(widths) + 2 * (len(widths) - 1)))

    for r in results:
        m = r['metrics']
        print(fmt_row([
            r['labeling'],
            r['confidence'],
            f"{m['total_return_pct']:.2f}",
            f"{m['sharpe_ratio']:.2f}",
            f"{m['sortino_ratio']:.2f}",
            f"{m['profit_factor']:.2f}",
            f"{m['max_drawdown_pct']:.2f}",
            f"{m['win_rate_pct']:.2f}",
            m['total_trades'],
            f"{m['avg_trade_pct']:.2f}",
        ]))

    print()
    print("=" * 140)
    print("RANKINGS")
    print("=" * 140)
    print()

    ranked_by_sharpe = sorted(results, key=lambda x: x['metrics']['sharpe_ratio'], reverse=True)
    print("BY SHARPE RATIO:")
    print(fmt_row(['Rank', 'Labeling', 'Confidence', 'Sharpe', 'Return%', 'Sortino', 'Trades']))
    print('-' * 100)
    for i, r in enumerate(ranked_by_sharpe[:5], 1):
        m = r['metrics']
        print(f"{i:3d}.  {r['labeling']:24s}  {r['confidence']:15s}  "
              f"{m['sharpe_ratio']:6.2f}  {m['total_return_pct']:8.2f}%  "
              f"{m['sortino_ratio']:7.2f}  {m['total_trades']:6d}")

    print()
    ranked_by_pf = sorted(results, key=lambda x: x['metrics']['profit_factor'], reverse=True)
    print("BY PROFIT FACTOR:")
    print(fmt_row(['Rank', 'Labeling', 'Confidence', 'PF', 'Return%', 'WinRate%', 'Trades']))
    print('-' * 100)
    for i, r in enumerate(ranked_by_pf[:5], 1):
        m = r['metrics']
        print(f"{i:3d}.  {r['labeling']:24s}  {r['confidence']:15s}  "
              f"{m['profit_factor']:6.2f}  {m['total_return_pct']:8.2f}%  "
              f"{m['win_rate_pct']:8.2f}%  {m['total_trades']:6d}")

    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--symbol', action='append', help='Restrict to specific symbols')
    parser.add_argument('--timeframe', action='append', help='Restrict to specific timeframes')
    args = parser.parse_args()

    symbols = args.symbol if args.symbol else DEFAULT_SYMBOLS
    timeframes = args.timeframe if args.timeframe else DEFAULT_TIMEFRAMES

    logger.info("Loading reference data...")
    btc_by_tf = {tf: load_data('BTCUSDT', tf) for tf in timeframes}
    spy_by_tf = {tf: load_data('ES_proxy', tf) for tf in timeframes}

    for symbol in symbols:
        for tf in timeframes:
            try:
                comparison = run_comparison(symbol, tf, btc_by_tf.get(tf), spy_by_tf.get(tf))
                if comparison:
                    print_comparison_report(comparison)
            except Exception as e:
                logger.exception(f"{symbol} {tf} comparison failed: {e}")
                continue


if __name__ == '__main__':
    main()
