"""Adaptive drift-based retraining policy.

Pure decision logic — no scheduler, no training. Given a model's latest
drift snapshot and age, ``should_retrain_model()`` decides whether the
scheduler should rebuild it. This replaces the static daily/weekly tier
cadence with condition-based self-healing retraining.

Decision order (first match wins):
    1. cooldown      — retrained too recently → SKIP
    2. missing_drift — no usable drift baseline → retrain only if aged out
    3. drift_threshold — drift score >= threshold → RETRAIN
    4. max_age       — model older than max_model_age_days → RETRAIN
    5. healthy_skip  — otherwise → SKIP

All thresholds come from the ``adaptive_retraining`` section of
``config.yaml`` and fall back to safe defaults if missing. Nothing here
raises — a missing config or a broken metadata blob degrades to the
defaults, never crashes the scheduler.
"""

from __future__ import annotations

import os
import re
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from ml_service.utils.logger import get_logger

logger = get_logger(__name__)

# ─── Safe defaults ────────────────────────────────────────────────
# Applied when the config section or any individual key is absent.
DEFAULTS: Dict[str, object] = {
    'enabled': True,
    'drift_threshold': 0.60,
    'max_model_age_days': 14,
    'min_retrain_interval_hours': 24,
}

_CONFIG_PATH = Path(__file__).parent / 'config.yaml'

# Filename timestamp pattern used by trainer.save_model(): _YYYYMMDD_HHMMSS
_FILENAME_TS_RE = re.compile(r'_(\d{8})_(\d{6})')


def get_adaptive_retraining_config() -> Dict[str, object]:
    """Load the ``adaptive_retraining`` config section merged over defaults.

    Never raises — a missing/unreadable/malformed config returns the safe
    defaults so the scheduler keeps running. Unknown keys are ignored;
    known keys are coerced to the correct type where possible.
    """
    config = dict(DEFAULTS)

    try:
        if not _CONFIG_PATH.exists():
            return config

        with open(_CONFIG_PATH) as f:
            raw = yaml.safe_load(f) or {}

        section = raw.get('adaptive_retraining') or {}

        # Coerce each known key defensively.
        if isinstance(section.get('enabled'), bool):
            config['enabled'] = section['enabled']
        if section.get('drift_threshold') is not None:
            config['drift_threshold'] = float(section['drift_threshold'])
        if section.get('max_model_age_days') is not None:
            config['max_model_age_days'] = int(section['max_model_age_days'])
        if section.get('min_retrain_interval_hours') is not None:
            config['min_retrain_interval_hours'] = float(
                section['min_retrain_interval_hours']
            )
    except Exception as e:
        logger.warning(
            f"Failed to load adaptive_retraining config, using defaults: {e}"
        )

    return config


def _parse_iso_trained_at(value: str) -> Optional[datetime]:
    """Parse the ``trained_at`` ISO timestamp stored in model metadata."""
    if not value:
        return None
    try:
        # metadata stores datetime.now().isoformat(); fromisoformat handles
        # both naive and timezone-aware forms in Python 3.11+.
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _parse_filename_timestamp(path: str) -> Optional[datetime]:
    """Extract a training timestamp from a model filename (_YYYYMMDD_HHMMSS)."""
    try:
        name = Path(path).name
        match = _FILENAME_TS_RE.search(name)
        if not match:
            return None
        return datetime.strptime(match.group(1) + match.group(2), '%Y%m%d%H%M%S')
    except (ValueError, TypeError):
        return None


def get_model_age_hours(symbol: str, timeframe: str) -> Optional[float]:
    """Return the production model's age in hours, or None if no model exists.

    Resolution order (prefer the most reliable available source):
        1. governance metadata ``trained_at`` (ISO timestamp in the pickle)
        2. timestamp embedded in the production model filename
        3. filesystem mtime of the production model file

    Returns None only when there is no production model at all.
    """
    try:
        from models.governance import (
            get_production_model_path,
            load_model_metadata,
        )

        production_path = get_production_model_path(symbol, timeframe)
        if not production_path:
            return None

        trained_at: Optional[datetime] = None

        # 1. Prefer metadata trained_at.
        metadata = load_model_metadata(production_path)
        if metadata:
            trained_at = _parse_iso_trained_at(metadata.get('trained_at'))

        # 2. Fall back to the filename timestamp.
        if trained_at is None:
            trained_at = _parse_filename_timestamp(production_path)

        # 3. Fall back to filesystem mtime.
        if trained_at is None:
            trained_at = datetime.fromtimestamp(os.path.getmtime(production_path))

        age = (datetime.now() - trained_at).total_seconds() / 3600.0
        return max(age, 0.0)
    except Exception as e:
        logger.warning(
            f"Could not determine model age for {symbol} {timeframe}: {e}"
        )
        return None


def _get_drift_snapshot(
    symbol: str, timeframe: str
) -> Optional[Dict]:
    """Fetch the latest drift snapshot, swallowing errors → None."""
    try:
        from analytics.drift_monitor import get_latest_drift_snapshot
        return get_latest_drift_snapshot(symbol, timeframe)
    except Exception as e:
        logger.warning(
            f"Drift snapshot lookup failed for {symbol} {timeframe}: {e}"
        )
        return None


def should_retrain_model(
    symbol: str,
    timeframe: str,
    config: Optional[Dict[str, object]] = None,
) -> Tuple[bool, str, Dict[str, object]]:
    """Decide whether ``symbol``/``timeframe`` should be retrained now.

    Returns ``(should_retrain, reason, details)`` where ``details`` carries
    the drift score, age, and health status for observability logging.

    Args:
        symbol: e.g. "BTCUSDT"
        timeframe: e.g. "1h"
        config: pre-loaded adaptive config (loaded fresh if omitted)
    """
    cfg = config if config is not None else get_adaptive_retraining_config()

    drift_threshold = float(cfg.get('drift_threshold', DEFAULTS['drift_threshold']))
    max_age_days = int(cfg.get('max_model_age_days', DEFAULTS['max_model_age_days']))
    min_interval_h = float(
        cfg.get('min_retrain_interval_hours', DEFAULTS['min_retrain_interval_hours'])
    )
    max_age_hours = max_age_days * 24.0

    age_hours = get_model_age_hours(symbol, timeframe)
    snapshot = _get_drift_snapshot(symbol, timeframe)

    drift_score = snapshot.get('overall_score') if snapshot else None
    health_status = snapshot.get('health_status') if snapshot else None

    details: Dict[str, object] = {
        'drift_score': drift_score,
        'age_hours': age_hours,
        'age_days': round(age_hours / 24.0, 1) if age_hours is not None else None,
        'health_status': health_status,
        'drift_threshold': drift_threshold,
        'max_age_hours': max_age_hours,
        'min_interval_hours': min_interval_h,
    }

    # No production model at all → train (handled by the caller's skip-on-
    # failure, but signal RETRAIN so a missing model gets built). We can't
    # apply cooldown/drift without a model, so short-circuit here.
    if age_hours is None:
        details['note'] = 'no_production_model'
        return True, 'max_age', details

    # 1. Cooldown — never retrain storms. Checked first regardless of drift.
    if age_hours < min_interval_h:
        return False, 'cooldown', details

    # 2. Missing drift baseline — snapshot absent or score unknown.
    drift_unknown = (
        snapshot is None
        or drift_score is None
        or health_status in (None, 'unknown')
    )
    if drift_unknown:
        # Only force a rebuild when the model is also aged out, so we
        # refresh baselines for stale models without looping endlessly on
        # freshly-trained models that simply lack a snapshot yet.
        if age_hours >= max_age_hours:
            return True, 'missing_drift', details
        return False, 'missing_drift', details

    # 3. Drift trigger.
    if drift_score is not None and drift_score >= drift_threshold:
        return True, 'drift_threshold', details

    # 4. Max-age safety net.
    if age_hours >= max_age_hours:
        return True, 'max_age', details

    # 5. Healthy.
    return False, 'healthy_skip', details
