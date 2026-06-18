"""Data-driven TP/SL optimization based on backtest history."""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple

from utils.logger import get_logger
from utils.config import get_forward_periods
from data.database import get_database
from models.trainer import prepare_features

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


def simulate_trade_outcome(
    ohlcv_df: pd.DataFrame,
    trade_type: str,
    entry_idx: int,
    entry_price: float,
    atr_at_entry: float,
    tp_multiplier: float,
    sl_multiplier: float,
    max_hold_candles: int,
) -> str:
    """
    Simulate whether a trade would hit TP or SL first with given parameters.

    Args:
        ohlcv_df: OHLCV DataFrame
        trade_type: 'long' or 'short'
        entry_idx: Entry candle index
        entry_price: Entry price
        atr_at_entry: ATR at entry
        tp_multiplier: Take profit multiplier
        sl_multiplier: Stop loss multiplier
        max_hold_candles: Maximum candles to hold

    Returns:
        'win' if TP hit first, 'loss' if SL hit first, 'timeout' if neither hit
    """
    if trade_type == 'long':
        tp_price = entry_price + (atr_at_entry * tp_multiplier)
        sl_price = entry_price - (atr_at_entry * sl_multiplier)
    else:
        tp_price = entry_price - (atr_at_entry * tp_multiplier)
        sl_price = entry_price + (atr_at_entry * sl_multiplier)

    end_idx = min(entry_idx + max_hold_candles, len(ohlcv_df) - 1)

    for idx in range(entry_idx + 1, end_idx + 1):
        candle = ohlcv_df.iloc[idx]
        high = candle['high']
        low = candle['low']

        if trade_type == 'long':
            if high >= tp_price:
                return 'win'
            if low <= sl_price:
                return 'loss'
        else:
            if low <= tp_price:
                return 'win'
            if high >= sl_price:
                return 'loss'

    return 'timeout'


def optimize_tp_sl(symbol: str, timeframe: str) -> Optional[Dict]:
    """
    Optimize TP/SL multipliers using expectancy-based grid search.

    Args:
        symbol: Trading symbol
        timeframe: Timeframe

    Returns:
        Optimization results dict or None
    """
    logger.info(f"Optimizing TP/SL for {symbol} {timeframe} using expectancy-based grid search")

    trades_df = load_backtest_trades(symbol, timeframe)
    if trades_df is None or trades_df.empty:
        logger.warning("No backtest data available for optimization")
        return None

    ohlcv_df = load_ohlcv_with_atr(symbol, timeframe)
    if ohlcv_df is None:
        return None

    ohlcv_df['idx'] = range(len(ohlcv_df))
    timestamp_to_idx = dict(zip(ohlcv_df['timestamp'], ohlcv_df['idx']))

    valid_trades = []
    for _, trade in trades_df.iterrows():
        entry_ts = int(trade['entry_timestamp'])

        if entry_ts not in timestamp_to_idx:
            continue

        entry_idx = timestamp_to_idx[entry_ts]
        entry_row = ohlcv_df.iloc[entry_idx]
        atr_at_entry = entry_row.get('atr', None)

        if pd.isna(atr_at_entry) or atr_at_entry <= 0:
            continue

        valid_trades.append({
            'type': trade['type'],
            'entry_idx': entry_idx,
            'entry_price': trade['entry_price'],
            'atr': atr_at_entry,
        })

    if not valid_trades:
        logger.warning("No valid trades with ATR data for optimization")
        return None

    logger.info(f"Running grid search on {len(valid_trades)} valid trades")

    RR_OPTIONS = [1.0, 1.5, 2.0, 2.5, 3.0]
    SL_BASE = [0.8, 1.0, 1.2, 1.5]
    MAX_HOLD_CANDLES = get_forward_periods()

    best_expectancy = -float('inf')
    best_params = None

    for sl_mult in SL_BASE:
        for rr_ratio in RR_OPTIONS:
            tp_mult = sl_mult * rr_ratio

            wins = 0
            losses = 0
            timeouts = 0

            for trade in valid_trades:
                outcome = simulate_trade_outcome(
                    ohlcv_df,
                    trade['type'],
                    trade['entry_idx'],
                    trade['entry_price'],
                    trade['atr'],
                    tp_mult,
                    sl_mult,
                    MAX_HOLD_CANDLES,
                )

                if outcome == 'win':
                    wins += 1
                elif outcome == 'loss':
                    losses += 1
                else:
                    timeouts += 1

            total_trades = wins + losses
            if total_trades == 0:
                continue

            win_rate = wins / total_trades
            expectancy = (win_rate * rr_ratio) - (1 - win_rate)

            logger.debug(f"SL={sl_mult:.1f}x, RR={rr_ratio:.1f}x: "
                        f"WinRate={win_rate:.2%}, Expectancy={expectancy:.3f}, "
                        f"Wins={wins}, Losses={losses}, Timeouts={timeouts}")

            if expectancy > best_expectancy:
                best_expectancy = expectancy
                best_params = {
                    'tp_multiplier': round(tp_mult, 2),
                    'sl_multiplier': round(sl_mult, 2),
                    'rr_ratio': round(rr_ratio, 2),
                    'win_rate': round(win_rate, 4),
                    'expectancy': round(expectancy, 4),
                    'optimal_hold_candles': MAX_HOLD_CANDLES,
                    'sample_size': len(valid_trades),
                    'wins': wins,
                    'losses': losses,
                    'timeouts': timeouts,
                    'last_updated': datetime.now().isoformat(),
                }

    if best_params is None:
        logger.warning("No valid parameter combinations found")
        return None

    logger.info(f"Optimization complete: TP={best_params['tp_multiplier']}x, "
                f"SL={best_params['sl_multiplier']}x, RR={best_params['rr_ratio']}:1, "
                f"WinRate={best_params['win_rate']:.2%}, Expectancy={best_params['expectancy']:.3f}")

    return best_params


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
