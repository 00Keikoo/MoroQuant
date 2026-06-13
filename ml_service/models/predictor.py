"""Signal generation using trained ML models."""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import pickle
import json

from ..utils.logger import get_logger
from ..data.database import get_database
from .trainer import prepare_features, get_feature_columns

logger = get_logger()

_model_cache = {}
_signal_cache = {}


def load_latest_model(symbol: str, timeframe: str) -> Optional[Dict]:
    """
    Load the most recent trained model for a symbol/timeframe.

    Args:
        symbol: Trading symbol
        timeframe: Timeframe

    Returns:
        Model package dict or None if no model found
    """
    cache_key = f"{symbol}_{timeframe}"
    if cache_key in _model_cache:
        logger.info(f"Using cached model for {symbol} {timeframe}")
        return _model_cache[cache_key]

    models_dir = Path(__file__).parent.parent / "storage" / "models"

    if not models_dir.exists():
        logger.warning(f"Models directory not found: {models_dir}")
        return None

    pattern = f"{symbol}_{timeframe}_*.pkl"
    model_files = list(models_dir.glob(pattern))

    if not model_files:
        logger.warning(f"No model found for {symbol} {timeframe}")
        return None

    latest_model = max(model_files, key=lambda p: p.stat().st_mtime)
    logger.info(f"Loading model from disk: {latest_model.name}")

    with open(latest_model, 'rb') as f:
        model_package = pickle.load(f)

    _model_cache[cache_key] = model_package
    return model_package


def calculate_feature_importance(
    model: object,
    feature_cols: List[str],
    X: pd.DataFrame,
) -> Dict[str, float]:
    """
    Calculate feature importance using model's built-in importance.

    Args:
        model: Trained model
        feature_cols: Feature column names
        X: Feature DataFrame (single row)

    Returns:
        Dict of feature: importance
    """
    try:
        importance = model.feature_importances_
        feature_importance = dict(zip(feature_cols, importance))
        sorted_features = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))
        return sorted_features
    except Exception as e:
        logger.error(f"Error calculating feature importance: {e}")
        return {}


def generate_signal(
    symbol: str,
    timeframe: str,
    n_candles: int = 300,
    skip_mtf: bool = False,
) -> Optional[Dict]:
    """
    Generate trading signal for a symbol/timeframe.

    Args:
        symbol: Trading symbol
        timeframe: Timeframe
        n_candles: Number of recent candles to load for feature calculation

    Returns:
        Signal dictionary or None if generation fails
    """
    from .tp_sl_optimizer import load_optimized_params

    cache_key = f"{symbol}_{timeframe}"
    cached = _signal_cache.get(cache_key)
    if cached:
        age = (datetime.now() - cached['cached_at']).total_seconds()
        if age < 300:
            logger.info(f"Using cached signal for {symbol} {timeframe} (age: {age:.1f}s)")
            # Return cached signal without price - routes.py will add fresh price
            return cached['signal']

    logger.info(f"Generating signal for {symbol} {timeframe}")

    model_package = load_latest_model(symbol, timeframe)
    if model_package is None:
        logger.error(f"No trained model found for {symbol} {timeframe}")
        return None

    model = model_package['model']
    metadata = model_package['metadata']
    feature_cols = metadata['feature_cols']

    db = get_database()
    with db.get_connection() as conn:
        query = f"""
            SELECT timestamp, open, high, low, close, volume
            FROM ohlcv
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(symbol, timeframe, n_candles))

    if df.empty:
        logger.error(f"No data found for {symbol} {timeframe}")
        return None

    df = df.sort_values('timestamp').reset_index(drop=True)

    df = prepare_features(df, symbol=symbol)

    df_clean = df[feature_cols].dropna()

    if df_clean.empty:
        logger.error("No valid data after feature engineering")
        return None

    X_latest = df_clean.iloc[[-1]]
    latest_row = df.iloc[-1]

    if isinstance(model, dict) and 'xgb' in model and 'lgb' in model:
        xgb_proba = model['xgb'].predict_proba(X_latest)[0]
        lgb_proba = model['lgb'].predict_proba(X_latest)[0]
        prediction_proba = (xgb_proba + lgb_proba) / 2
        prediction = int(np.argmax(prediction_proba))

        xgb_importance = model['xgb'].feature_importances_
        lgb_importance = model['lgb'].feature_importances_
        combined_importance = (xgb_importance + lgb_importance) / 2
        feature_importance = dict(zip(feature_cols, combined_importance))
        feature_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))
    else:
        prediction = model.predict(X_latest)[0]
        prediction_proba = model.predict_proba(X_latest)[0]
        feature_importance = calculate_feature_importance(model, feature_cols, X_latest)

    direction_map = {0: 'short', 1: 'neutral', 2: 'long'}
    direction = direction_map[prediction]

    confidence = int(prediction_proba[prediction] * 100)

    top_features = dict(list(feature_importance.items())[:5])

    regime = latest_row.get('market_phase', 'unknown')

    current_price = float(latest_row['close'])
    atr = float(latest_row.get('atr', 0))

    optimized_params = load_optimized_params(symbol, timeframe)
    if optimized_params:
        tp_multiplier = optimized_params['tp_multiplier']
        sl_multiplier = optimized_params['sl_multiplier']
        max_hold_candles = optimized_params['optimal_hold_candles']
        tp_sl_source = 'optimized'
        logger.info(f"Using optimized TP/SL: TP={tp_multiplier}x, SL={sl_multiplier}x, Hold={max_hold_candles}")
    else:
        tp_multiplier = 3.0
        sl_multiplier = 1.5
        max_hold_candles = 12
        tp_sl_source = 'default'

    stop_loss = None
    take_profit = None
    if atr > 0 and direction != 'neutral':
        if direction == 'long':
            stop_loss = current_price - (atr * sl_multiplier)
            take_profit = current_price + (atr * tp_multiplier)
        elif direction == 'short':
            stop_loss = current_price + (atr * sl_multiplier)
            take_profit = current_price - (atr * tp_multiplier)

    timeframe_hours = {'1h': 1, '4h': 4, '15m': 0.25, '30m': 0.5, '1d': 24}
    hours = timeframe_hours.get(timeframe, 1)
    from datetime import timedelta
    valid_until = (datetime.now() + timedelta(hours=max_hold_candles * hours)).isoformat()

    signal = {
        'symbol': symbol,
        'timeframe': timeframe,
        'direction': direction,
        'confidence': confidence,
        'price': current_price,
        'stop_loss': round(stop_loss, 2) if stop_loss else None,
        'take_profit': round(take_profit, 2) if take_profit else None,
        'atr': round(atr, 2),
        'risk_reward': f'1:{round(tp_multiplier / sl_multiplier, 1)}' if direction != 'neutral' else None,
        'valid_until': valid_until,
        'max_hold_candles': max_hold_candles,
        'tp_sl_source': tp_sl_source,
        'top_features': {k: float(v) for k, v in top_features.items()},
        'regime': regime,
        'generated_at': datetime.now().isoformat(),
        'model_type': metadata['model_type'],
        'mtf_conflict': False,
    }

    if timeframe == '1h' and not skip_mtf:
        try:
            higher_tf_signal = generate_signal(symbol=symbol, timeframe='4h', n_candles=n_candles, skip_mtf=True)

            if higher_tf_signal is not None:
                if higher_tf_signal['direction'] == signal['direction']:
                    signal['confidence'] = min(100, int(signal['confidence'] * 1.15))
                    logger.info(f"MTF confirmation: 1h and 4h agree, boosted confidence to {signal['confidence']}%")
                else:
                    signal['confidence'] = max(0, int(signal['confidence'] * 0.80))
                    signal['mtf_conflict'] = True
                    logger.info(f"MTF conflict: 1h={signal['direction']}, 4h={higher_tf_signal['direction']}, reduced confidence to {signal['confidence']}%")
        except Exception as e:
            logger.warning(f"MTF check failed: {e}")

    save_signal_to_db(signal)

    # Cache signal without price field (price is always fetched fresh in routes.py)
    signal_to_cache = {k: v for k, v in signal.items() if k != 'price'}
    _signal_cache[cache_key] = {
        'signal': signal_to_cache,
        'cached_at': datetime.now()
    }

    logger.info(f"Signal generated: {direction} with {confidence}% confidence")

    return signal


def save_signal_to_db(signal: Dict) -> None:
    """
    Save signal to database.

    Args:
        signal: Signal dictionary
    """
    db = get_database()

    timestamp = int(datetime.now().timestamp() * 1000)
    features_json = json.dumps(signal['top_features'])

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO signals (symbol, timeframe, timestamp, direction, confidence, features_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                signal['symbol'],
                signal['timeframe'],
                timestamp,
                signal['direction'],
                signal['confidence'],
                features_json,
            )
        )

    logger.info(f"Signal saved to database")
