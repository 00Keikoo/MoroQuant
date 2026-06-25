"""Production drift monitoring system for detecting model degradation."""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from utils.logger import get_logger
from data.database import get_database
from models.predictor import load_latest_model

logger = get_logger(__name__)

# ─── Drift snapshot persistence (cache layer) ─────────────────────

def persist_drift_snapshot(symbol: str, timeframe: str, report: Dict) -> bool:
    """Persist a drift report as a cached snapshot in the DB.

    Extracts the key fields from the full report and stores them for
    fast retrieval by the API endpoint.

    Returns True on success, False on failure (never raises).
    """
    try:
        db = get_database()
        import json

        # Extract sub-scores for the narrow columns.
        feature_drift_val = report.get('feature_drift', {}).get('max_psi', 0)
        confidence_drift_val = report.get('confidence_drift', {}).get('drift_score', 0)
        metadata = {
            'feature_drift': report.get('feature_drift'),
            'confidence_drift': report.get('confidence_drift'),
            'regime_drift': report.get('regime_drift'),
            'retrain_reasons': report.get('retrain_reasons', []),
        }

        training_samples = (
            report.get('feature_drift', {}).get('live_sample_size', 0)
        )

        overall_score = report.get('overall_score')

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO model_drift_snapshots
                    (symbol, timeframe, drift_score, drift_status,
                     feature_drift, prediction_drift,
                     training_samples, live_samples,
                     metadata_json, snapshot_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    timeframe,
                    overall_score,  # may be None for 'unknown' status
                    report.get('health_status', 'unknown'),
                    feature_drift_val,
                    confidence_drift_val,
                    0,  # training_samples — not available directly
                    training_samples,
                    json.dumps(metadata),
                    datetime.now().isoformat(),
                ),
            )
        return True
    except Exception as e:
        logger.error(f"persist_drift_snapshot failed for {symbol} {timeframe}: {e}")
        return False


def get_latest_drift_snapshot(symbol: str, timeframe: str) -> Optional[Dict]:
    """Retrieve the most recent drift snapshot from the DB cache.

    Returns the full drift report dict (reconstructed from the cached
    snapshot + stored metadata), or None if no snapshot exists.

    Target latency: < 50 ms (single indexed SELECT).
    """
    try:
        import json

        db = get_database()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT drift_score, drift_status, feature_drift,
                       prediction_drift, metadata_json, snapshot_timestamp
                FROM model_drift_snapshots
                WHERE symbol = ? AND timeframe = ?
                ORDER BY snapshot_timestamp DESC
                LIMIT 1
                """,
                (symbol, timeframe),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        metadata = json.loads(row[4]) if row[4] else {}

        raw_score = row[0]

        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'health_status': row[1],
            'overall_score': round(raw_score, 3) if raw_score is not None else None,
            'retrain_required': row[1] == 'red' or (
                row[2] is not None and row[2] > 0.25
            ),
            'retrain_reasons': metadata.get('retrain_reasons', []),
            'feature_drift': metadata.get('feature_drift', {}),
            'confidence_drift': metadata.get('confidence_drift', {}),
            'regime_drift': metadata.get('regime_drift', {}),
            'timestamp': row[5],
        }
    except Exception as e:
        logger.error(f"get_latest_drift_snapshot failed for {symbol} {timeframe}: {e}")
        return None


def calculate_psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    """
    Calculate Population Stability Index (PSI).

    PSI measures distribution drift between expected (training) and actual (live) data.

    PSI < 0.1: No significant change
    PSI 0.1-0.25: Moderate change, investigate
    PSI > 0.25: Significant change, retrain recommended

    Args:
        expected: Training distribution
        actual: Live distribution
        bins: Number of bins for histogram

    Returns:
        PSI score
    """
    # Remove NaN values
    expected = expected[~np.isnan(expected)]
    actual = actual[~np.isnan(actual)]

    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    # Define bin edges based on expected distribution
    bin_edges = np.linspace(
        min(expected.min(), actual.min()),
        max(expected.max(), actual.max()),
        bins + 1
    )

    # Calculate distributions
    expected_percents = np.histogram(expected, bins=bin_edges)[0] / len(expected)
    actual_percents = np.histogram(actual, bins=bin_edges)[0] / len(actual)

    # Add small constant to avoid division by zero
    expected_percents = np.where(expected_percents == 0, 0.0001, expected_percents)
    actual_percents = np.where(actual_percents == 0, 0.0001, actual_percents)

    # Calculate PSI
    psi = np.sum((actual_percents - expected_percents) * np.log(actual_percents / expected_percents))

    return float(psi)


def compute_feature_drift(symbol: str, timeframe: str, n_candles: int = 500) -> Dict:
    """
    Compare latest live candles with training feature statistics.

    Computes:
    - Mean shift for each feature
    - Std shift for each feature
    - PSI (Population Stability Index) for each feature

    Args:
        symbol: Trading symbol
        timeframe: Timeframe
        n_candles: Number of recent candles to analyze

    Returns:
        Dict with feature drift metrics
    """
    model_package = load_latest_model(symbol, timeframe)

    if not model_package:
        return {
            'status': 'error',
            'message': f'No trained model found for {symbol} {timeframe}'
        }

    metadata = model_package.get('metadata', {})
    feature_cols = metadata.get('feature_cols', [])

    # Get training statistics if available
    training_stats = metadata.get('training_stats', {})

    if not training_stats:
        logger.warning(
            f"Missing feature drift baseline for {symbol} {timeframe}. "
            f"Falling back to UNKNOWN status."
        )
        return {
            'status': 'unknown',
            'message': 'No training statistics available in model metadata',
            'feature_count': len(feature_cols)
        }

    # Fetch recent live data
    db = get_database()
    with db.get_connection() as conn:
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM ohlcv
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(symbol, timeframe, n_candles))

    if df.empty:
        return {
            'status': 'error',
            'message': f'No recent data found for {symbol} {timeframe}'
        }

    df = df.sort_values('timestamp').reset_index(drop=True)

    # Prepare features using same pipeline as training
    from models.trainer import prepare_features
    df = prepare_features(df, symbol=symbol)

    df_clean = df[feature_cols].dropna()

    if df_clean.empty:
        return {
            'status': 'error',
            'message': 'No valid data after feature engineering'
        }

    # Calculate drift metrics for each feature
    feature_drifts = []
    max_psi = 0.0

    for feature in feature_cols:
        if feature not in df_clean.columns:
            continue

        live_values = df_clean[feature].values

        if feature in training_stats:
            train_mean = training_stats[feature].get('mean', np.nan)
            train_std = training_stats[feature].get('std', np.nan)

            live_mean = np.mean(live_values)
            live_std = np.std(live_values)

            # Calculate shifts
            mean_shift = abs((live_mean - train_mean) / train_mean) if train_mean != 0 else 0
            std_shift = abs((live_std - train_std) / train_std) if train_std != 0 else 0

            # Calculate PSI using real training distribution if available
            train_values = training_stats[feature].get('values', [])
            if len(train_values) > 0:
                train_samples = np.array(train_values)
                psi = calculate_psi(train_samples, live_values)
            else:
                psi = 0.0

            max_psi = max(max_psi, psi)

            feature_drifts.append({
                'feature': feature,
                'mean_shift': round(mean_shift, 4),
                'std_shift': round(std_shift, 4),
                'psi': round(psi, 4),
                'train_mean': round(train_mean, 4),
                'live_mean': round(live_mean, 4),
                'train_std': round(train_std, 4),
                'live_std': round(live_std, 4),
            })

    # Determine status based on max PSI
    if max_psi > 0.25:
        status = 'critical'
    elif max_psi > 0.1:
        status = 'warning'
    else:
        status = 'normal'

    # Sort by PSI descending
    feature_drifts.sort(key=lambda x: x['psi'], reverse=True)

    return {
        'status': status,
        'max_psi': round(max_psi, 4),
        'feature_count': len(feature_drifts),
        'top_drifting_features': feature_drifts[:10],
        'all_features': feature_drifts,
        'live_sample_size': len(df_clean),
        'timestamp': datetime.now().isoformat()
    }


def compute_confidence_drift(symbol: str, timeframe: str, n_signals: int = 1000) -> Dict:
    """
    Compare recent signal confidence distribution with validation distribution.

    Args:
        symbol: Trading symbol
        timeframe: Timeframe
        n_signals: Number of recent signals to analyze

    Returns:
        Dict with confidence drift metrics
    """
    model_package = load_latest_model(symbol, timeframe)

    if not model_package:
        return {
            'status': 'error',
            'message': f'No trained model found for {symbol} {timeframe}'
        }

    metadata = model_package.get('metadata', {})
    validation = metadata.get('validation', {})

    # Get validation confidence distribution
    val_confidence = validation.get('confidence_distribution')

    if not val_confidence:
        logger.warning(
            f"Missing confidence drift baseline for {symbol} {timeframe}. "
            f"Falling back to UNKNOWN status."
        )
        return {
            'status': 'unknown',
            'message': 'No validation confidence distribution available'
        }

    # Fetch recent signals
    db = get_database()
    with db.get_connection() as conn:
        query = """
            SELECT confidence
            FROM signals
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        cursor = conn.cursor()
        cursor.execute(query, (symbol, timeframe, n_signals))
        rows = cursor.fetchall()

    if not rows:
        return {
            'status': 'error',
            'message': f'No recent signals found for {symbol} {timeframe}'
        }

    live_confidences = np.array([row[0] for row in rows])

    # Calculate distribution metrics
    live_mean = np.mean(live_confidences)
    live_std = np.std(live_confidences)

    val_mean = val_confidence.get('mean', live_mean)
    val_std = val_confidence.get('std', live_std)

    # Calculate drift metrics
    mean_shift = abs((live_mean - val_mean) / val_mean) if val_mean != 0 else 0
    std_shift = abs((live_std - val_std) / val_std) if val_std != 0 else 0

    # Calculate PSI for confidence distribution using real validation values if available
    val_values = val_confidence.get('values', [])
    if len(val_values) > 0:
        val_samples = np.array(val_values)
        psi = calculate_psi(val_samples, live_confidences)
    else:
        psi = 0.0

    # Determine drift score and status
    drift_score = (mean_shift + std_shift + psi) / 3

    if drift_score > 0.3 or psi > 0.25:
        status = 'critical'
    elif drift_score > 0.15 or psi > 0.1:
        status = 'warning'
    else:
        status = 'normal'

    # Calculate bucket distribution
    live_buckets = {
        '0-39': np.sum((live_confidences >= 0) & (live_confidences < 40)),
        '40-59': np.sum((live_confidences >= 40) & (live_confidences < 60)),
        '60-79': np.sum((live_confidences >= 60) & (live_confidences < 80)),
        '80-100': np.sum((live_confidences >= 80) & (live_confidences <= 100)),
    }

    return {
        'status': status,
        'drift_score': round(drift_score, 4),
        'psi': round(psi, 4),
        'mean_shift': round(mean_shift, 4),
        'std_shift': round(std_shift, 4),
        'validation': {
            'mean': round(val_mean, 2),
            'std': round(val_std, 2),
        },
        'live': {
            'mean': round(live_mean, 2),
            'std': round(live_std, 2),
            'sample_size': len(live_confidences),
            'distribution': {k: int(v) for k, v in live_buckets.items()}
        },
        'timestamp': datetime.now().isoformat()
    }


def compute_regime_drift(symbol: str, timeframe: str, days_back: int = 30) -> Dict:
    """
    Compare training regime distribution with recent regime distribution.

    Args:
        symbol: Trading symbol
        timeframe: Timeframe
        days_back: Number of days to look back for live regime distribution

    Returns:
        Dict with regime drift metrics
    """
    model_package = load_latest_model(symbol, timeframe)

    if not model_package:
        return {
            'status': 'error',
            'message': f'No trained model found for {symbol} {timeframe}'
        }

    metadata = model_package.get('metadata', {})
    training_regime_dist = metadata.get('regime_distribution', {})

    if not training_regime_dist:
        logger.warning(
            f"Missing regime drift baseline for {symbol} {timeframe}. "
            f"Falling back to UNKNOWN status."
        )
        return {
            'status': 'unknown',
            'message': 'No training regime distribution available'
        }

    # Calculate time window
    time_window = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)

    # Fetch recent candles with regime labels
    db = get_database()
    with db.get_connection() as conn:
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM ohlcv
            WHERE symbol = ? AND timeframe = ? AND timestamp >= ?
            ORDER BY timestamp DESC
        """
        df = pd.read_sql_query(query, conn, params=(symbol, timeframe, time_window))

    if df.empty:
        return {
            'status': 'error',
            'message': f'No recent data found for {symbol} {timeframe}'
        }

    df = df.sort_values('timestamp').reset_index(drop=True)

    # Add regime features
    from models.trainer import prepare_features
    df = prepare_features(df, symbol=symbol)

    if 'market_phase' not in df.columns:
        return {
            'status': 'error',
            'message': 'Regime labels not available in recent data'
        }

    # Calculate live regime distribution
    regime_counts = df['market_phase'].value_counts()
    total = len(df)

    live_regime_dist = {
        regime: round(count / total * 100, 1)
        for regime, count in regime_counts.items()
    }

    # Calculate drift percentage for each regime
    regime_drifts = []
    max_drift = 0.0

    for regime in set(list(training_regime_dist.keys()) + list(live_regime_dist.keys())):
        train_pct = training_regime_dist.get(regime, 0)
        live_pct = live_regime_dist.get(regime, 0)

        drift_pct = abs(live_pct - train_pct)
        max_drift = max(max_drift, drift_pct)

        regime_drifts.append({
            'regime': regime,
            'training_pct': train_pct,
            'live_pct': live_pct,
            'drift_pct': round(drift_pct, 1)
        })

    # Sort by drift descending
    regime_drifts.sort(key=lambda x: x['drift_pct'], reverse=True)

    # Determine status based on max drift
    if max_drift > 30:
        status = 'critical'
    elif max_drift > 15:
        status = 'warning'
    else:
        status = 'normal'

    return {
        'status': status,
        'max_drift_pct': round(max_drift, 1),
        'regime_comparison': regime_drifts,
        'training_distribution': training_regime_dist,
        'live_distribution': live_regime_dist,
        'live_sample_size': total,
        'days_analyzed': days_back,
        'timestamp': datetime.now().isoformat()
    }


def get_drift_report(symbol: str, timeframe: str) -> Dict:
    """
    Generate comprehensive drift report for a model.

    Returns:
        Complete drift analysis with retrain recommendation
    """
    logger.info(f"Generating drift report for {symbol} {timeframe}")

    # Compute all drift metrics
    feature_drift = compute_feature_drift(symbol, timeframe)
    confidence_drift = compute_confidence_drift(symbol, timeframe)
    regime_drift = compute_regime_drift(symbol, timeframe)

    # Calculate overall drift score (0-1 scale)
    # Skip sub-drifts with 'error' or 'unknown' status — we can't score them
    scores = []
    has_unknown = False

    if feature_drift.get('status') in ('error', 'unknown'):
        if feature_drift.get('status') == 'unknown':
            has_unknown = True
    else:
        # Map PSI to 0-1 scale (0.25+ = 1.0)
        feature_score = min(feature_drift.get('max_psi', 0) / 0.25, 1.0)
        scores.append(feature_score)

    if confidence_drift.get('status') in ('error', 'unknown'):
        if confidence_drift.get('status') == 'unknown':
            has_unknown = True
    else:
        confidence_score = min(confidence_drift.get('drift_score', 0) / 0.3, 1.0)
        scores.append(confidence_score)

    if regime_drift.get('status') in ('error', 'unknown'):
        if regime_drift.get('status') == 'unknown':
            has_unknown = True
    else:
        # Map max drift percentage to 0-1 scale (30%+ = 1.0)
        regime_score = min(regime_drift.get('max_drift_pct', 0) / 30, 1.0)
        scores.append(regime_score)

    # If ALL sub-drifts are unknown/error, we have no baseline at all.
    # Return UNKNOWN — never classify as warning/critical.
    if not scores:
        if has_unknown:
            logger.warning(
                f"Missing drift baseline for {symbol} {timeframe}. "
                f"Falling back to UNKNOWN status."
            )
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'health_status': 'unknown',
                'overall_score': None,
                'retrain_required': False,
                'retrain_reasons': [],
                'feature_drift': feature_drift,
                'confidence_drift': confidence_drift,
                'regime_drift': regime_drift,
                'timestamp': datetime.now().isoformat(),
            }
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'health_status': 'unknown',
            'overall_score': None,
            'retrain_required': False,
            'retrain_reasons': [],
            'feature_drift': feature_drift,
            'confidence_drift': confidence_drift,
            'regime_drift': regime_drift,
            'timestamp': datetime.now().isoformat(),
        }

    overall_score = float(np.mean(scores))

    # Determine retrain requirement
    retrain_required = False
    retrain_reasons = []

    # Rule 1: PSI > 0.25
    if feature_drift.get('max_psi', 0) > 0.25:
        retrain_required = True
        retrain_reasons.append(f"Feature PSI exceeds threshold: {feature_drift.get('max_psi'):.3f} > 0.25")

    # Rule 2: Confidence drift critical
    if confidence_drift.get('status') == 'critical':
        retrain_required = True
        retrain_reasons.append(f"Confidence drift critical: score {confidence_drift.get('drift_score'):.3f}")

    # Rule 3: Regime drift > 30%
    if regime_drift.get('max_drift_pct', 0) > 30:
        retrain_required = True
        retrain_reasons.append(f"Regime drift exceeds 30%: {regime_drift.get('max_drift_pct'):.1f}%")

    # Determine overall health status
    if overall_score > 0.7 or retrain_required:
        health_status = 'red'
    elif overall_score > 0.4:
        health_status = 'yellow'
    else:
        health_status = 'green'

    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'health_status': health_status,
        'overall_score': round(overall_score, 3),
        'retrain_required': retrain_required,
        'retrain_reasons': retrain_reasons,
        'feature_drift': feature_drift,
        'confidence_drift': confidence_drift,
        'regime_drift': regime_drift,
        'timestamp': datetime.now().isoformat()
    }
