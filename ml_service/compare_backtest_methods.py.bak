#!/usr/bin/env python3
"""Compare labeling methods and confidence thresholds via walk-forward backtesting.

Trains models with:
  - Fixed Horizon
  - Triple Barrier (TP=2.0, SL=2.0)
  - Triple Barrier (TP=2.5, SL=1.5)
  - Triple Barrier (TP=3.0, SL=1.5)

Tests each with confidence filters: None, >=60%, >=70%

Uses percentage-based data splits (60/20/20):
  - Training: 60% (initial model only)
  - Calibration: 20% (split into train 60% / validation 40%)
  - Test: 20% (walk-forward backtest with out-of-sample predictions)

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
)
from ml_service.models import calibration as cal_mod
from ml_service.utils.config import get_forward_periods
from ml_service.utils.logger import get_logger, setup_logger

import xgboost as xgb
import lightgbm as lgb
from sklearn.metrics import f1_score

setup_logger()
logger = get_logger()

DEFAULT_SYMBOLS = ['BTCUSDT', 'ETHUSDT']
DEFAULT_TIMEFRAMES = ['1h']
DATA_LIMIT = 2000
TEST_SIZE = 50


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


def calculate_regions(N: int, H: int) -> Dict:
    """Calculate percentage-based region boundaries with purge gaps."""
    train_end = int(N * 0.60)

    cal_start = train_end + H
    cal_end = int(N * 0.80) - H
    cal_size = cal_end - cal_start

    cal_train_end = cal_start + int(cal_size * 0.60)
    cal_val_start = cal_train_end + H

    test_start = int(N * 0.80) + H
    test_end = N

    return {
        'train': (0, train_end),
        'cal_train': (cal_start, cal_train_end),
        'cal_val': (cal_val_start, cal_end),
        'test': (test_start, test_end),
        'purge_size': H,
        'N': N,
    }


def train_model_on_window(
    df: pd.DataFrame,
    feature_cols: List[str],
    train_start: int,
    train_end: int,
) -> Tuple[object, str]:
    """Train model on specified window."""
    df_clean = df[feature_cols + ['target']].iloc[train_start:train_end].dropna()

    if len(df_clean) < 50:
        return None, None

    X_train = df_clean[feature_cols]
    y_train = df_clean['target']

    xgb_params = {
        'max_depth': 6,
        'learning_rate': 0.1,
        'n_estimators': 100,
        'objective': 'multi:softmax',
        'num_class': 3,
        'random_state': 42,
    }

    lgb_params = {
        'max_depth': 6,
        'learning_rate': 0.1,
        'n_estimators': 100,
        'objective': 'multiclass',
        'num_class': 3,
        'random_state': 42,
        'verbose': -1,
    }

    xgb_model = xgb.XGBClassifier(**xgb_params)
    xgb_model.fit(X_train, y_train)

    lgb_model = lgb.LGBMClassifier(**lgb_params)
    lgb_model.fit(X_train, y_train)

    xgb_pred = xgb_model.predict(X_train[-50:])
    lgb_pred = lgb_model.predict(X_train[-50:])

    xgb_f1 = f1_score(y_train[-50:], xgb_pred, average='weighted', zero_division=0)
    lgb_f1 = f1_score(y_train[-50:], lgb_pred, average='weighted', zero_division=0)

    if xgb_f1 >= lgb_f1:
        return xgb_model, 'xgboost'
    else:
        return lgb_model, 'lightgbm'


def build_calibration_dataset(
    df: pd.DataFrame,
    feature_cols: List[str],
    regions: Dict,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Build calibration train and validation datasets."""
    cal_train_start, cal_train_end = regions['cal_train']
    cal_val_start, cal_val_end = regions['cal_val']
    train_end = regions['train'][1]

    logger.info(f"Training initial model on [0:{train_end}]")
    initial_model, model_type = train_model_on_window(df, feature_cols, 0, train_end)

    if initial_model is None:
        return None, None, None, None

    logger.info(f"Initial model: {model_type}")

    cal_train_probas_list = []
    cal_train_y_list = []

    n_cal_train_folds = (cal_train_end - cal_train_start) // TEST_SIZE
    logger.info(f"Generating {n_cal_train_folds} calibration-train folds [{cal_train_start}:{cal_train_end}]")

    for i in range(n_cal_train_folds):
        fold_start = cal_train_start + i * TEST_SIZE
        fold_end = fold_start + TEST_SIZE

        X_fold = df[feature_cols].iloc[fold_start:fold_end]
        y_fold = df['target'].iloc[fold_start:fold_end]

        valid_mask = X_fold.notna().all(axis=1) & y_fold.notna()
        if valid_mask.sum() == 0:
            continue

        probas = initial_model.predict_proba(X_fold[valid_mask])
        cal_train_probas_list.append(probas)
        cal_train_y_list.append(y_fold[valid_mask].values)

    cal_train_probas = np.vstack(cal_train_probas_list)
    cal_train_y = np.concatenate(cal_train_y_list)

    cal_val_probas_list = []
    cal_val_y_list = []

    n_cal_val_folds = (cal_val_end - cal_val_start) // TEST_SIZE
    logger.info(f"Generating {n_cal_val_folds} calibration-val folds [{cal_val_start}:{cal_val_end}]")

    for i in range(n_cal_val_folds):
        fold_start = cal_val_start + i * TEST_SIZE
        fold_end = fold_start + TEST_SIZE

        X_fold = df[feature_cols].iloc[fold_start:fold_end]
        y_fold = df['target'].iloc[fold_start:fold_end]

        valid_mask = X_fold.notna().all(axis=1) & y_fold.notna()
        if valid_mask.sum() == 0:
            continue

        probas = initial_model.predict_proba(X_fold[valid_mask])
        cal_val_probas_list.append(probas)
        cal_val_y_list.append(y_fold[valid_mask].values)

    cal_val_probas = np.vstack(cal_val_probas_list)
    cal_val_y = np.concatenate(cal_val_y_list)

    logger.info(f"Calibration-train: {len(cal_train_y)} samples")
    logger.info(f"Calibration-val: {len(cal_val_y)} samples")

    return cal_train_probas, cal_train_y, cal_val_probas, cal_val_y


def fit_and_select_calibrator(
    cal_train_probas: np.ndarray,
    cal_train_y: np.ndarray,
    cal_val_probas: np.ndarray,
    cal_val_y: np.ndarray,
) -> Dict:
    """Fit calibrators on train set, select best on validation set."""
    logger.info("Fitting calibrators on calibration-train set")
    calibrators = {}
    for method in ['raw', 'platt', 'isotonic']:
        calibrators[method] = cal_mod.fit_calibrator(method, cal_train_probas, cal_train_y)

    logger.info("Evaluating calibrators on calibration-val set")
    val_metrics = {}
    for method, calibrator in calibrators.items():
        probas_calibrated = cal_mod.apply_calibrator(calibrator, cal_val_probas)
        val_metrics[method] = cal_mod.metric_bundle(probas_calibrated, cal_val_y)

    chosen_method = cal_mod.pick_best_method(val_metrics)
    logger.info(f"Selected calibrator: {chosen_method}")
    logger.info(f"  Validation ECE: {val_metrics[chosen_method]['ece']:.4f}")

    all_probas = np.vstack([cal_train_probas, cal_val_probas])
    all_y = np.concatenate([cal_train_y, cal_val_y])
    final_calibrator = cal_mod.fit_calibrator(chosen_method, all_probas, all_y)

    return final_calibrator


def generate_walk_forward_predictions(
    df: pd.DataFrame,
    feature_cols: List[str],
    calibrator: Dict,
    regions: Dict,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate out-of-sample predictions via walk-forward on test region."""
    test_start, test_end = regions['test']
    H = regions['purge_size']
    N = regions['N']

    predictions = np.full(N, np.nan)
    probas = np.zeros((N, 3))
    valid_mask = np.zeros(N, dtype=bool)

    test_size = test_end - test_start
    n_folds = (test_size - TEST_SIZE) // TEST_SIZE + 1

    logger.info(f"Walk-forward test: {n_folds} folds on [{test_start}:{test_end}]")

    for fold_idx in range(n_folds):
        fold_test_start = test_start + fold_idx * TEST_SIZE
        fold_test_end = min(fold_test_start + TEST_SIZE, test_end)

        if fold_test_end - fold_test_start < TEST_SIZE:
            break

        train_end = fold_test_start - H

        model, model_type = train_model_on_window(df, feature_cols, 0, train_end)
        if model is None:
            continue

        X_test = df[feature_cols].iloc[fold_test_start:fold_test_end]
        valid_rows = X_test.notna().all(axis=1)

        if valid_rows.sum() == 0:
            continue

        probas_raw = model.predict_proba(X_test[valid_rows])
        probas_calibrated = cal_mod.apply_calibrator(calibrator, probas_raw)
        preds = np.argmax(probas_calibrated, axis=1)

        valid_indices = X_test[valid_rows].index.values
        predictions[valid_indices] = preds
        probas[valid_indices] = probas_calibrated
        valid_mask[valid_indices] = True

        logger.info(f"  Fold {fold_idx + 1}/{n_folds}: [{fold_test_start}:{fold_test_end}] → {valid_rows.sum()} predictions")

    return predictions, probas, valid_mask


def run_backtest_simulation(
    df: pd.DataFrame,
    predictions: np.ndarray,
    probas: np.ndarray,
    valid_mask: np.ndarray,
    confidence_threshold: Optional[float],
    regions: Dict,
    initial_capital: float = 10000.0,
    fee_rate: float = 0.0004,
) -> Dict:
    """Simulate backtest using out-of-sample predictions."""
    test_start = regions['test'][0]
    H = regions['purge_size']

    filtered_predictions = predictions.copy()

    if confidence_threshold is not None:
        max_conf = probas.max(axis=1)
        low_conf_mask = (max_conf < confidence_threshold) & valid_mask
        filtered_predictions[low_conf_mask] = 1

    direction_map = {0: 'short', 1: 'neutral', 2: 'long'}
    signals = [direction_map.get(p, 'neutral') if not np.isnan(p) else 'neutral'
               for p in filtered_predictions]

    capital = initial_capital
    position = None
    trades = []
    equity_curve = []

    for i in range(test_start, len(df)):
        if not valid_mask[i]:
            continue

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
            elif hold_duration >= H:
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


def calculate_metrics(trades: List[Dict], equity_curve: List[Dict],
                     initial_capital: float, final_capital: float) -> Dict:
    """Calculate performance metrics."""
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
        logger.info(f"Labeling Method: {config['name']}")
        logger.info(f"{'='*80}")

        if config['method'] == 'fixed_horizon':
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
                tp_atr_mult=config['tp_mult'],
                sl_atr_mult=config['sl_mult'],
            )

        feature_cols = get_feature_columns(df_labeled)
        df_clean = df_labeled[feature_cols + ['target']].dropna()
        N = len(df_clean)

        if N < 200:
            logger.warning(f"Insufficient clean data: {N} rows")
            continue

        regions = calculate_regions(N, H)
        logger.info(f"Data regions (N={N}, H={H}):")
        logger.info(f"  Training: {regions['train']}")
        logger.info(f"  Cal-train: {regions['cal_train']}")
        logger.info(f"  Cal-val: {regions['cal_val']}")
        logger.info(f"  Test: {regions['test']}")

        df_clean = df_clean.reset_index(drop=True)

        cal_train_probas, cal_train_y, cal_val_probas, cal_val_y = build_calibration_dataset(
            df_clean, feature_cols, regions
        )

        if cal_train_probas is None:
            logger.warning("Failed to build calibration dataset")
            continue

        calibrator = fit_and_select_calibrator(
            cal_train_probas, cal_train_y, cal_val_probas, cal_val_y
        )

        predictions, probas, valid_mask = generate_walk_forward_predictions(
            df_clean, feature_cols, calibrator, regions
        )

        n_predictions = valid_mask.sum()
        logger.info(f"Generated {n_predictions} out-of-sample predictions")

        for threshold, threshold_name in confidence_thresholds:
            logger.info(f"  Running backtest: {threshold_name}")

            backtest_result = run_backtest_simulation(
                df_clean, predictions, probas, valid_mask,
                confidence_threshold=threshold,
                regions=regions,
            )

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
        pf_display = f"{m['profit_factor']:.2f}" if m['profit_factor'] != float('inf') else 'inf'
        print(fmt_row([
            r['labeling'],
            r['confidence'],
            f"{m['total_return_pct']:.2f}",
            f"{m['sharpe_ratio']:.2f}",
            f"{m['sortino_ratio']:.2f}",
            pf_display,
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

    valid_pf_results = [r for r in results if r['metrics']['profit_factor'] != float('inf')]
    ranked_by_pf = sorted(valid_pf_results, key=lambda x: x['metrics']['profit_factor'], reverse=True)
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
