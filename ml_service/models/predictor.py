"""Signal generation using trained ML models."""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Tuple
import pickle
import json
import yaml

from utils.logger import get_logger
from utils.config import get_forward_periods, get_config
from data.database import get_database
from models.trainer import prepare_features, get_feature_columns
from models import calibration as cal_mod

logger = get_logger(__name__)

# ─── Calibration config (safe defaults, never crashes) ─────────────
_CAL_CONFIG_PATH = Path(__file__).parent.parent / 'config.yaml'
_CAL_CONFIG_CACHE: Optional[Dict] = None

_CALIBRATION_DEFAULTS = {
    'production_default_method': 'platt',
    'isotonic_override_enabled': True,
    'sanity_check_threshold': 0.98,
    'sanity_check_consecutive_limit': 5,
}


def _get_calibration_config() -> Dict:
    """Load the ``calibration`` config section merged over safe defaults.

    Never raises — a missing/malformed config returns defaults.
    """
    global _CAL_CONFIG_CACHE
    if _CAL_CONFIG_CACHE is not None:
        return _CAL_CONFIG_CACHE

    config = dict(_CALIBRATION_DEFAULTS)

    try:
        if _CAL_CONFIG_PATH.exists():
            with open(_CAL_CONFIG_PATH) as f:
                raw = yaml.safe_load(f) or {}
            section = raw.get('calibration') or {}
            if isinstance(section.get('production_default_method'), str):
                config['production_default_method'] = section['production_default_method']
            if isinstance(section.get('isotonic_override_enabled'), bool):
                config['isotonic_override_enabled'] = section['isotonic_override_enabled']
            if section.get('sanity_check_threshold') is not None:
                config['sanity_check_threshold'] = float(section['sanity_check_threshold'])
            if section.get('sanity_check_consecutive_limit') is not None:
                config['sanity_check_consecutive_limit'] = int(
                    section['sanity_check_consecutive_limit']
                )
    except Exception as e:
        logger.warning(f"Failed to load calibration config, using defaults: {e}")

    _CAL_CONFIG_CACHE = config
    return _CAL_CONFIG_CACHE


# ─── Calibration sanity-check state ─────────────────────────────────
_consecutive_extreme_count = 0

def get_metadata_value(metadata, key, default=None):
	if isinstance(metadata, dict):
		return metadata.get(key, default)
	return getattr(metadata, key, default)

_model_cache = {}
_signal_cache = {}


def validate_model_features(
    model_package: Dict,
    generated_features: List[str],
    context: str = "",
) -> Tuple[bool, List[str]]:
    """Validate a model's required features against what we can generate.

    Compares ``metadata['feature_cols']`` (the features the model was
    trained on) against the currently-generated feature columns. If any
    required feature is missing, the model is rejected with a detailed
    log so production inference never crashes on a feature mismatch.

    Args:
        model_package: The loaded model package dict (or any dict with a
            ``metadata`` sub-dict containing ``feature_cols``).
        generated_features: Feature column names currently producible.
        context: Optional label (e.g. symbol/timeframe) for log clarity.

    Returns:
        (is_compatible, missing_features)
    """
    if not model_package:
        return False, []

    metadata = model_package.get('metadata', {})
    required = metadata.get('feature_cols', [])

    if not required:
        logger.error(
            f"Model rejected: no feature_cols in metadata"
            f"{f' [{context}]' if context else ''}"
        )
        return False, []

    required_set = set(required)
    generated_set = set(generated_features)
    missing = sorted(required_set - generated_set)

    if missing:
        logger.error(
            f"Model rejected:{f' [{context}]' if context else ''}"
        )
        logger.error(f"missing features: {missing}")
        return False, missing

    return True, []


def load_latest_model(symbol: str, timeframe: str) -> Optional[Dict]:
    """
    Load the current production model for a symbol/timeframe.

    Args:
        symbol: Trading symbol
        timeframe: Timeframe

    Returns:
        Model package dict or None if no model found
    """
    from models.governance import get_production_model_path, validate_model_compatibility

    cache_key = f"{symbol}_{timeframe}"
    if cache_key in _model_cache:
        logger.info(f"Using cached model for {symbol} {timeframe}")
        return _model_cache[cache_key]

    model_path = get_production_model_path(symbol, timeframe)
    if not model_path:
        logger.warning(f"No production model found for {symbol} {timeframe}")
        return None

    df_sample = pd.DataFrame({
        'timestamp': range(500),
        'open': [100.0] * 500,
        'high': [101.0] * 500,
        'low': [99.0] * 500,
        'close': [100.0] * 500,
        'volume': [1000.0] * 500,
    })
    df_sample = prepare_features(df_sample, symbol=symbol)
    current_features = get_feature_columns(df_sample)

    is_compatible, missing_features = validate_model_compatibility(model_path, current_features)

    if not is_compatible:
        # Detailed rejection log — never crash on feature mismatch.
        context = f"{symbol} {timeframe}"
        logger.error(
            f"Model rejected: {Path(model_path).name} [{context}] "
            f"is incompatible with current features"
        )
        logger.error(f"missing features: {missing_features}")
        logger.error("Model cannot be loaded. Fix active_models.json to reference a compatible model.")
        return None

    with open(model_path, 'rb') as f:
        model_package = pickle.load(f)

    model_package['model_path'] = model_path

    metadata = model_package.get('metadata', {})
    labeling_method = get_metadata_value(metadata, 'labeling_method', 'UNKNOWN')
    trained_at = get_metadata_value(metadata, 'trained_at', 'UNKNOWN')
    tp_mult = get_metadata_value(metadata, 'tp_mult', 'N/A')
    sl_mult = get_metadata_value(metadata, 'sl_mult', 'N/A')

    cal_artifact = cal_mod.load_calibration_artifact(model_path)
    if cal_artifact:
        model_package['calibration'] = cal_artifact

    model_name = Path(model_path).name
    logger.info(f"{'='*60}")
    logger.info(f"LOADED MODEL: {model_name}")
    logger.info(f"  Model path: {model_path}")
    logger.info(f"  Trained at: {trained_at}")
    logger.info(f"  Labeling method: {labeling_method}")
    if labeling_method == 'triple_barrier':
        logger.info(f"  TP multiplier: {tp_mult}x ATR")
        logger.info(f"  SL multiplier: {sl_mult}x ATR")
    logger.info(f"  Calibration available: {cal_artifact is not None}")
    logger.info(f"{'='*60}")

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
    confidence_threshold: float = 0.0,
    override_timestamp: Optional[int] = None,
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
    if not override_timestamp:
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
        """
        params = [symbol, timeframe]
        if override_timestamp:
            query += " AND timestamp <= ?"
            params.append(override_timestamp)
        query += """
            ORDER BY timestamp DESC
            LIMIT ?
        """
        params.append(n_candles)
        df = pd.read_sql_query(query, conn, params=params)

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
        raw_proba = (xgb_proba + lgb_proba) / 2

        xgb_importance = model['xgb'].feature_importances_
        lgb_importance = model['lgb'].feature_importances_
        combined_importance = (xgb_importance + lgb_importance) / 2
        feature_importance = dict(zip(feature_cols, combined_importance))
        feature_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))
    else:
        raw_proba = model.predict_proba(X_latest)[0]
        feature_importance = calculate_feature_importance(model, feature_cols, X_latest)

    # --- Confidence pipeline: raw → calibrated → confidence ---
    cal_config = _get_calibration_config()
    cal_artifact = model_package.get('calibration')
    calibration_available = cal_artifact is not None
    calibration_applied = False
    calibration_method = cal_artifact['chosen_method'] if calibration_available else 'none'

    raw_proba_max = float(np.max(raw_proba))

    # ── Isotonic override: force platt when feature flag is enabled ───
    # Isotonic regression overfits on small hold-out sets and collapses
    # probabilities to extreme values in production (confidence=100%).
    # When isotonic_override_enabled=true, silently use platt instead.
    effective_method = calibration_method
    if (
        calibration_available
        and calibration_method == 'isotonic'
        and cal_config.get('isotonic_override_enabled', True)
    ):
        effective_method = 'platt'
        logger.info(
            f"Calibration override: isotonic → platt "
            f"(feature flag: isotonic_override_enabled)"
        )

    if calibration_available and effective_method != 'raw':
        chosen_cal = cal_artifact['calibrators'].get(effective_method)
        if chosen_cal is not None:
            try:
                prediction_proba = cal_mod.apply_calibrator(chosen_cal, raw_proba.reshape(1, -1)).flatten()
                calibration_applied = True
                logger.info(f"Calibration applied: {effective_method} "
                            f"(raw max={raw_proba_max:.3f} → calibrated max={float(np.max(prediction_proba)):.3f})")
            except Exception as e:
                logger.warning(f"Calibration failed ({effective_method}): {e}, falling back to raw probabilities")
                prediction_proba = raw_proba
        else:
            prediction_proba = raw_proba
    else:
        prediction_proba = raw_proba

    calibrated_proba_max = float(np.max(prediction_proba))

    # ── Calibration sanity check: detect collapsed probabilities ──────
    sanity_threshold = float(cal_config.get('sanity_check_threshold', 0.98))
    consecutive_limit = int(cal_config.get('sanity_check_consecutive_limit', 5))
    global _consecutive_extreme_count

    if calibrated_proba_max >= sanity_threshold:
        _consecutive_extreme_count += 1
        if _consecutive_extreme_count >= consecutive_limit:
            logger.warning(
                f"Calibration sanity check: calibrated_max >= {sanity_threshold} "
                f"for {_consecutive_extreme_count} consecutive predictions "
                f"(method={effective_method}, raw_max={raw_proba_max:.3f}, "
                f"calibrated_max={calibrated_proba_max:.4f}, "
                f"symbol={symbol}, timeframe={timeframe}). "
                f"Probable calibration collapse — consider retraining."
            )
    else:
        _consecutive_extreme_count = 0

    # Update calibration_method in signal to reflect the effective method
    calibration_method = effective_method if calibration_applied else calibration_method
    prediction = int(np.argmax(prediction_proba))
    confidence = float(prediction_proba[prediction])
    confidence_pct = int(confidence * 100)

    direction_map = {0: 'short', 1: 'neutral', 2: 'long'}
    direction = direction_map[prediction]

    # Log prediction details
    logger.info(f"Raw probability distribution: {[round(float(p), 3) for p in raw_proba]}")
    if calibration_applied:
        logger.info(f"Calibrated probability distribution ({calibration_method}): {[round(float(p), 3) for p in prediction_proba]}")
    logger.info(f"Predicted class: {prediction} ({direction})")
    logger.info(f"Confidence: {confidence_pct}% (raw_max={raw_proba_max:.3f}, calibrated_max={calibrated_proba_max:.3f})")

    # Apply confidence threshold filter
    filtered_by_confidence = False
    if confidence < confidence_threshold and direction != 'neutral':
        direction = 'neutral'
        filtered_by_confidence = True
        logger.info(f"Signal filtered by confidence threshold: {confidence_pct}% < {int(confidence_threshold*100)}%")

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
        max_hold_candles = get_forward_periods()
        tp_sl_source = 'default'

    take_profit, stop_loss = calculate_tp_sl(
        current_price, atr, direction, tp_multiplier, sl_multiplier
    )

    timeframe_hours = {'1h': 1, '4h': 4, '15m': 0.25, '30m': 0.5, '1d': 24}
    hours = timeframe_hours.get(timeframe, 1)
    from datetime import timedelta
    dt_base = datetime.fromtimestamp(override_timestamp / 1000) if override_timestamp else datetime.now()
    valid_until = (dt_base + timedelta(hours=max_hold_candles * hours)).isoformat()

    # Use more precision for low-priced assets
    decimal_places = 4 if current_price < 1.0 else 2

    # Get labeling method from metadata or config
    labeling_method = get_metadata_value(metadata, 'labeling_method', 'unknown')

    # Get model trained timestamp
    trained_at = get_metadata_value(metadata, 'trained_at', 'unknown')

    # Extract model version from model path (e.g., BTCUSDT_1h_20240101_120000.pkl -> 20240101_120000)
    model_path = model_package.get('model_path', '')
    model_version = Path(model_path).stem.split('_', 2)[-1] if model_path else 'unknown'

    # Calculate prediction distribution for diagnostics (post-calibration)
    pred_distribution = {
        'class0_short': round(float(prediction_proba[0]), 3),
        'class1_neutral': round(float(prediction_proba[1]), 3),
        'class2_long': round(float(prediction_proba[2]), 3),
    }

    signal = {
        'symbol': symbol,
        'timeframe': timeframe,
        'direction': direction,
        'confidence': confidence_pct,
        'model_version': model_version,
        'confidence_raw': round(confidence, 3),
        'confidence_threshold': int(confidence_threshold * 100),
        'filtered_by_confidence': filtered_by_confidence,
        'calibration_applied': calibration_applied,
        'calibration_available': calibration_available,
        'calibration_method': calibration_method,
        'raw_probability_max': round(raw_proba_max, 4),
        'calibrated_probability_max': round(calibrated_proba_max, 4),
        'price': current_price,
        'stop_loss': round(stop_loss, decimal_places) if stop_loss else None,
        'take_profit': round(take_profit, decimal_places) if take_profit else None,
        'atr': round(atr, 2),
        'tp_multiplier': tp_multiplier,
        'sl_multiplier': sl_multiplier,
        'risk_reward': f'1:{round(tp_multiplier / sl_multiplier, 1)}' if direction != 'neutral' else None,
        'valid_until': valid_until,
        'max_hold_candles': max_hold_candles,
        'prob_short': round(float(prediction_proba[0]), 3),
        'prob_neutral': round(float(prediction_proba[1]), 3),
        'prob_long': round(float(prediction_proba[2]), 3),
        'tp_sl_source': tp_sl_source,
        'top_features': {k: float(v) for k, v in top_features.items()},
        'regime': regime,
        'generated_at': dt_base.isoformat(),
        'model_type': metadata['model_type'],
        'labeling_method': labeling_method,
        'trained_at': trained_at,
        'prediction_distribution': pred_distribution,
        'mtf_alignment': 'NEUTRAL',
    }

    if override_timestamp:
        signal['timestamp'] = override_timestamp

    if timeframe == '1h' and not skip_mtf:
        try:
            higher_tf_signal = generate_signal(
                symbol=symbol,
                timeframe='4h',
                n_candles=n_candles,
                skip_mtf=True,
                confidence_threshold=confidence_threshold,
                override_timestamp=override_timestamp
            )

            if higher_tf_signal is not None:
                if higher_tf_signal['direction'] == signal['direction']:
                    signal['mtf_alignment'] = 'AGREE'
                    logger.info(f"MTF alignment: AGREE (1h={signal['direction']}, 4h={higher_tf_signal['direction']})")
                elif signal['direction'] == 'neutral' or higher_tf_signal['direction'] == 'neutral':
                    signal['mtf_alignment'] = 'NEUTRAL'
                    logger.info(f"MTF alignment: NEUTRAL (1h={signal['direction']}, 4h={higher_tf_signal['direction']})")
                else:
                    signal['mtf_alignment'] = 'DISAGREE'
                    logger.info(f"MTF alignment: DISAGREE (1h={signal['direction']}, 4h={higher_tf_signal['direction']})")
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


def calculate_tp_sl(
    current_price: float,
    atr: float,
    direction: str,
    tp_multiplier: float,
    sl_multiplier: float,
) -> tuple[Optional[float], Optional[float]]:
    """
    Calculate take profit and stop loss levels.

    Args:
        current_price: Current market price
        atr: Average True Range
        direction: Trade direction ('long', 'short', or 'neutral')
        tp_multiplier: Take profit multiplier
        sl_multiplier: Stop loss multiplier

    Returns:
        (take_profit, stop_loss) tuple
    """
    stop_loss = None
    take_profit = None

    if direction == 'neutral':
        return take_profit, stop_loss

    if atr > 0:
        if direction == 'long':
            stop_loss = current_price - (atr * sl_multiplier)
            take_profit = current_price + (atr * tp_multiplier)
        elif direction == 'short':
            stop_loss = current_price + (atr * sl_multiplier)
            take_profit = current_price - (atr * tp_multiplier)
    else:
        # Fallback to percentage-based TP/SL when ATR is zero
        tp_pct = 0.02  # 2%
        sl_pct = 0.015  # 1.5%
        if direction == 'long':
            stop_loss = current_price * (1 - sl_pct)
            take_profit = current_price * (1 + tp_pct)
        elif direction == 'short':
            stop_loss = current_price * (1 + sl_pct)
            take_profit = current_price * (1 - tp_pct)

    return take_profit, stop_loss


def save_signal_to_db(signal: Dict) -> None:
    """
    Save signal to database.

    Args:
        signal: Signal dictionary
    """
    db = get_database()

    timestamp = signal.get('timestamp') or int(datetime.now().timestamp() * 1000)
    features_json = json.dumps(signal['top_features'])

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO signals (
                symbol, timeframe, timestamp, direction, confidence, features_json,
                tp_multiplier, sl_multiplier, labeling_method, atr, regime, model_version,
                entry_price, take_profit, stop_loss,
                prob_short, prob_neutral, prob_long,
                mtf_alignment, raw_probability_max, calibrated_probability_max,
                calibration_method, valid_until
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal['symbol'],
                signal['timeframe'],
                timestamp,
                signal['direction'],
                signal['confidence'],
                features_json,
                signal.get('tp_multiplier'),
                signal.get('sl_multiplier'),
                signal.get('labeling_method'),
                signal.get('atr'),
                signal.get('regime'),
                signal.get('model_version'),
                signal.get('price'),
                signal.get('take_profit'),
                signal.get('stop_loss'),
                signal.get('prob_short'),
                signal.get('prob_neutral'),
                signal.get('prob_long'),
                signal.get('mtf_alignment', 'NEUTRAL'),
                signal.get('raw_probability_max'),
                signal.get('calibrated_probability_max'),
                signal.get('calibration_method'),
                signal.get('valid_until'),
            )
        )

    logger.info(f"Signal saved to database")


def get_latest_signal_from_db(symbol: str, timeframe: str) -> Optional[Dict]:
    """
    Read most recent signal from database without running inference.

    Args:
        symbol: Trading symbol
        timeframe: Timeframe

    Returns:
        Signal dictionary or None if no signal found
    """
    db = get_database()

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id, symbol, timeframe, timestamp, direction, confidence,
                features_json, tp_multiplier, sl_multiplier, labeling_method,
                atr, regime, model_version, created_at,
                entry_price, take_profit, stop_loss,
                valid_until, signal_status
            FROM signals
            WHERE symbol = ? AND timeframe = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (symbol, timeframe)
        )

        row = cursor.fetchone()

        if not row:
            logger.warning(f"No signal found in database for {symbol} {timeframe}")
            return None

        # Parse features_json
        features_json = row[6]
        top_features = json.loads(features_json) if features_json else {}

        # Calculate signal age
        created_at_str = row[13]
        created_at = datetime.fromisoformat(created_at_str)
        age_seconds = (datetime.now() - created_at).total_seconds()
        age_minutes = int(age_seconds / 60)

        signal = {
            'signal_id': row[0],
            'symbol': row[1],
            'timeframe': row[2],
            'timestamp': row[3],
            'direction': row[4],
            'confidence': row[5],
            'top_features': top_features,
            'tp_multiplier': row[7],
            'sl_multiplier': row[8],
            'labeling_method': row[9],
            'atr': row[10],
            'regime': row[11],
            'model_version': row[12],
            'generated_at': created_at.isoformat(),
            'age_minutes': age_minutes,
            'source': 'database',
            'entry_price': row[14],
            'take_profit': row[15],
            'stop_loss': row[16],
            'valid_until': row[17],
            'signal_status': row[18] or 'ACTIVE',
        }

        logger.info(f"Retrieved signal from database: {symbol} {timeframe} (age: {age_minutes} min)")
        return signal
