"""Data-driven TP/SL optimization based on backtest history."""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple

from ..utils.logger import get_logger
from ..data.database import get_database
from ..models.trainer import prepare_features

logger = get_logger()


def load_backtest_trades(symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
    """Load backtest trade history from CSV."""
    storage_dir = Path(__file__).parent.parent / "storage" / "backtest"
    trades_file = storage_dir / f"{symbol}_{timeframe}_trades.csv"

    if not trades_file.exists():
        logger.warning(f"No backtest trades found: {trades_file}")
        return None

    df = pd.read_csv(trades_file)
    logger.info(f"Loaded {len(df)} backtest trades for {symbol} {timeframe}")
    return df


def load_ohlcv_with_atr(symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
    """Load OHLCV data with ATR feature."""
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
        logger.error(f"No OHLCV data found for {symbol} {timeframe}")
        return None

    df_features = prepare_features(df, symbol=symbol)

    if 'atr' not in df_features.columns:
        logger.error("ATR feature not found in prepared features")
        return None

    logger.info(f"Loaded {len(df_features)} candles with ATR for {symbol} {timeframe}")
    return df_features


def calculate_max_excursions(
    df: pd.DataFrame,
    trade_type: str,
    entry_idx: int,
    exit_idx: int,
    entry_price: float,
) -> Tuple[float, float]:
    """
    Calculate max favorable and adverse price movements during a trade.

    Args:
        df: OHLCV DataFrame
        trade_type: 'long' or 'short'
        entry_idx: Entry candle index
        exit_idx: Exit candle index
        entry_price: Entry price

    Returns:
        (max_favorable_excursion, max_adverse_excursion)
    """
    trade_candles = df.iloc[entry_idx:exit_idx + 1]

    if trade_type == 'long':
        max_favorable = trade_candles['high'].max() - entry_price
        max_adverse = entry_price - trade_candles['low'].min()
    else:
        max_favorable = entry_price - trade_candles['low'].min()
        max_adverse = trade_candles['high'].max() - entry_price

    max_favorable = max(0, max_favorable)
    max_adverse = max(0, max_adverse)

    return max_favorable, max_adverse


def optimize_tp_sl(symbol: str, timeframe: str) -> Optional[Dict]:
    """
    Optimize TP/SL multipliers based on backtest history.

    Args:
        symbol: Trading symbol
        timeframe: Timeframe

    Returns:
        Optimization results dict or None
    """
    logger.info(f"Optimizing TP/SL for {symbol} {timeframe}")

    trades_df = load_backtest_trades(symbol, timeframe)
    if trades_df is None or trades_df.empty:
        logger.warning("No backtest data available for optimization")
        return None

    ohlcv_df = load_ohlcv_with_atr(symbol, timeframe)
    if ohlcv_df is None:
        return None

    ohlcv_df['idx'] = range(len(ohlcv_df))
    timestamp_to_idx = dict(zip(ohlcv_df['timestamp'], ohlcv_df['idx']))

    tp_multipliers = []
    sl_multipliers = []
    candles_to_target = []

    winning_trades = 0
    analyzed_trades = 0

    for _, trade in trades_df.iterrows():
        entry_ts = int(trade['entry_timestamp'])
        exit_ts = int(trade['exit_timestamp'])

        if entry_ts not in timestamp_to_idx or exit_ts not in timestamp_to_idx:
            continue

        entry_idx = timestamp_to_idx[entry_ts]
        exit_idx = timestamp_to_idx[exit_ts]

        entry_row = ohlcv_df.iloc[entry_idx]
        atr_at_entry = entry_row.get('atr', None)

        if pd.isna(atr_at_entry) or atr_at_entry <= 0:
            continue

        max_favorable, max_adverse = calculate_max_excursions(
            ohlcv_df,
            trade['type'],
            entry_idx,
            exit_idx,
            trade['entry_price']
        )

        if max_favorable > 0:
            tp_mult = max_favorable / atr_at_entry
            tp_multipliers.append(tp_mult)

        if max_adverse > 0:
            sl_mult = max_adverse / atr_at_entry
            sl_multipliers.append(sl_mult)

        if trade.get('pnl', 0) > 0 or trade.get('pnl_pct', 0) > 0:
            winning_trades += 1
            candles_held = trade.get('hold_candles', 0)
            if candles_held > 0:
                candles_to_target.append(candles_held)

        analyzed_trades += 1

    if not tp_multipliers or not sl_multipliers:
        logger.warning("Insufficient data to calculate multipliers")
        return None

    optimal_tp = np.median(tp_multipliers)
    optimal_sl = np.median(sl_multipliers) * 1.2

    if candles_to_target:
        optimal_hold = int(np.percentile(candles_to_target, 75))
    else:
        optimal_hold = 12

    win_rate = winning_trades / analyzed_trades if analyzed_trades > 0 else 0

    results = {
        'tp_multiplier': round(optimal_tp, 2),
        'sl_multiplier': round(optimal_sl, 2),
        'optimal_hold_candles': optimal_hold,
        'win_rate_at_these_levels': round(win_rate, 4),
        'sample_size': analyzed_trades,
        'last_updated': datetime.now().isoformat(),
        'tp_multiplier_p25': round(np.percentile(tp_multipliers, 25), 2),
        'tp_multiplier_p75': round(np.percentile(tp_multipliers, 75), 2),
        'sl_multiplier_p25': round(np.percentile(sl_multipliers, 25), 2),
        'sl_multiplier_p75': round(np.percentile(sl_multipliers, 75), 2),
    }

    logger.info(f"Optimization complete: TP={results['tp_multiplier']}x, SL={results['sl_multiplier']}x, "
                f"Hold={results['optimal_hold_candles']} candles, WinRate={results['win_rate_at_these_levels']:.2%}")

    return results


def save_optimized_params(params: Dict, symbol: str, timeframe: str) -> str:
    """Save optimized TP/SL parameters."""
    storage_dir = Path(__file__).parent.parent / "storage" / "tuned_params"
    storage_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{symbol}_{timeframe}_tp_sl.json"
    filepath = storage_dir / filename

    with open(filepath, 'w') as f:
        json.dump(params, f, indent=2)

    logger.info(f"Optimized TP/SL params saved to {filepath}")
    return str(filepath)


def load_optimized_params(symbol: str, timeframe: str) -> Optional[Dict]:
    """Load optimized TP/SL parameters."""
    storage_dir = Path(__file__).parent.parent / "storage" / "tuned_params"
    filepath = storage_dir / f"{symbol}_{timeframe}_tp_sl.json"

    if not filepath.exists():
        return None

    with open(filepath, 'r') as f:
        params = json.load(f)

    return params
