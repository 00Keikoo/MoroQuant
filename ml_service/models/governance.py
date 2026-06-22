"""Model governance for safe production deployment."""

import pickle
import shutil
import json
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from datetime import datetime

from utils.logger import get_logger

logger = get_logger(__name__)


def get_model_directories() -> Dict[str, Path]:
    """Get governance directory paths."""
    base_dir = Path(__file__).parent.parent / "storage" / "models"
    return {
        'production': base_dir / 'production',
        'candidates': base_dir / 'candidates',
        'archive': base_dir / 'archive',
    }


def load_model_metadata(model_path: str) -> Optional[Dict]:
    """Load metadata from a model file."""
    try:
        with open(model_path, 'rb') as f:
            model_package = pickle.load(f)
        return model_package.get('metadata', {})
    except Exception as e:
        logger.error(f"Failed to load model metadata from {model_path}: {e}")
        return None


def load_active_models_registry() -> Dict:
    """Load active models registry from JSON file."""
    dirs = get_model_directories()
    registry_path = dirs['production'].parent / 'active_models.json'

    if not registry_path.exists():
        logger.warning(f"Active models registry not found: {registry_path}")
        return {}

    try:
        with open(registry_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load active models registry: {e}")
        return {}


def save_active_models_registry(registry: Dict) -> None:
    """Save active models registry to JSON file."""
    dirs = get_model_directories()
    registry_path = dirs['production'].parent / 'active_models.json'

    try:
        with open(registry_path, 'w') as f:
            json.dump(registry, f, indent=2)
        logger.info(f"Active models registry saved to {registry_path}")
    except Exception as e:
        logger.error(f"Failed to save active models registry: {e}")


def get_production_model_path(symbol: str, timeframe: str) -> Optional[str]:
    """Get current production model path for symbol/timeframe using registry."""
    dirs = get_model_directories()
    production_dir = dirs['production']

    if not production_dir.exists():
        return None

    registry = load_active_models_registry()

    if symbol in registry and timeframe in registry[symbol]:
        filename = registry[symbol][timeframe]
        model_path = production_dir / filename

        if model_path.exists():
            return str(model_path)
        else:
            logger.error(f"Registry references non-existent model: {filename}")
            return None

    logger.warning(f"No active model in registry for {symbol} {timeframe}")
    return None


def validate_model_compatibility(model_path: str, current_features: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate model feature compatibility against current feature generation.

    Args:
        model_path: Path to model file
        current_features: List of features from current generation

    Returns:
        (is_compatible, missing_features)
    """
    metadata = load_model_metadata(model_path)

    if not metadata:
        return False, []

    model_features = metadata.get('feature_cols', [])

    if not model_features:
        logger.warning(f"Model {model_path} has no feature_cols in metadata")
        return False, []

    model_features_set = set(model_features)
    current_features_set = set(current_features)

    missing = model_features_set - current_features_set

    if missing:
        return False, sorted(list(missing))

    return True, []


def should_promote_model(
    candidate_metrics: Dict,
    production_metrics: Optional[Dict],
    improvement_threshold: float = 1.03,
    min_trades_threshold: int = 10,
) -> Tuple[bool, str]:
    """
    Determine if candidate model should replace production model.

    Args:
        candidate_metrics: Validation metrics from candidate model
        production_metrics: Validation metrics from current production model (None if no production model)
        improvement_threshold: Required improvement factor (1.03 = 3% improvement)
        min_trades_threshold: Minimum trades in validation for promotion

    Returns:
        (should_promote, reason) tuple
    """
    if production_metrics is None:
        return True, "no_existing_production_model"

    candidate_f1 = candidate_metrics.get('avg_f1_weighted', 0.0)
    production_f1 = production_metrics.get('avg_f1_weighted', 0.0)

    candidate_folds = candidate_metrics.get('n_folds', 0)

    if candidate_folds < 3:
        return False, f"insufficient_validation_folds (got {candidate_folds}, need 3+)"

    required_f1 = production_f1 * improvement_threshold

    if candidate_f1 < required_f1:
        return False, f"below_threshold (candidate={candidate_f1:.4f}, required={required_f1:.4f})"

    return True, f"improved (production={production_f1:.4f}, candidate={candidate_f1:.4f})"


def promote_model(
    candidate_path: str,
    symbol: str,
    timeframe: str,
) -> Dict:
    """
    Promote candidate model to production.

    Args:
        candidate_path: Path to candidate model file
        symbol: Trading symbol
        timeframe: Timeframe

    Returns:
        Dict with promotion results
    """
    dirs = get_model_directories()
    candidate_file = Path(candidate_path)

    if not candidate_file.exists():
        return {
            'status': 'error',
            'message': f"Candidate model not found: {candidate_path}"
        }

    production_dir = dirs['production']
    archive_dir = dirs['archive']
    production_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)

    old_production_path = get_production_model_path(symbol, timeframe)

    if old_production_path:
        old_file = Path(old_production_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = old_file.stem + f"_archived_{timestamp}" + old_file.suffix
        archive_path = archive_dir / archive_name

        shutil.move(str(old_file), str(archive_path))
        logger.info(f"Archived old production model: {archive_path}")

        old_calibration = old_file.parent / (old_file.stem + "_calibration.pkl")
        if old_calibration.exists():
            archive_cal_name = old_file.stem + f"_archived_{timestamp}_calibration.pkl"
            shutil.move(str(old_calibration), str(archive_dir / archive_cal_name))

    production_path = production_dir / candidate_file.name
    shutil.copy(str(candidate_file), str(production_path))

    candidate_calibration = candidate_file.parent / (candidate_file.stem + "_calibration.pkl")
    if candidate_calibration.exists():
        production_cal_path = production_dir / candidate_calibration.name
        shutil.copy(str(candidate_calibration), str(production_cal_path))

    logger.info(f"Promoted model to production: {production_path}")

    return {
        'status': 'promoted',
        'production_path': str(production_path),
        'archived_path': str(old_production_path) if old_production_path else None,
        'promoted_at': datetime.now().isoformat()
    }


def compare_and_promote(
    candidate_path: str,
    symbol: str,
    timeframe: str,
    improvement_threshold: float = 1.03,
) -> Dict:
    """
    Compare candidate model against production and promote if better.

    Args:
        candidate_path: Path to candidate model
        symbol: Trading symbol
        timeframe: Timeframe
        improvement_threshold: Required improvement factor

    Returns:
        Dict with comparison and promotion results
    """
    candidate_metadata = load_model_metadata(candidate_path)
    if not candidate_metadata:
        return {
            'status': 'error',
            'message': 'Failed to load candidate model metadata'
        }

    candidate_validation = candidate_metadata.get('validation')
    if not candidate_validation:
        return {
            'status': 'error',
            'message': 'Candidate model missing validation metrics'
        }

    production_path = get_production_model_path(symbol, timeframe)
    production_validation = None

    if production_path:
        production_metadata = load_model_metadata(production_path)
        if production_metadata:
            production_validation = production_metadata.get('validation')

    should_promote, reason = should_promote_model(
        candidate_validation,
        production_validation,
        improvement_threshold=improvement_threshold
    )

    result = {
        'symbol': symbol,
        'timeframe': timeframe,
        'candidate_path': candidate_path,
        'candidate_f1': candidate_validation.get('avg_f1_weighted', 0.0),
        'production_path': production_path,
        'production_f1': production_validation.get('avg_f1_weighted', 0.0) if production_validation else None,
        'should_promote': should_promote,
        'reason': reason,
        'improvement_threshold': improvement_threshold,
    }

    if should_promote:
        promotion_result = promote_model(candidate_path, symbol, timeframe)
        result.update(promotion_result)
        logger.info(f"✓ Model promoted: {symbol} {timeframe} - {reason}")
    else:
        result['status'] = 'rejected'
        logger.warning(f"✗ Model rejected: {symbol} {timeframe} - {reason}")

    return result


def rollback_model(symbol: str, timeframe: str) -> Dict:
    """
    Rollback to most recent archived model.

    Args:
        symbol: Trading symbol
        timeframe: Timeframe

    Returns:
        Dict with rollback results
    """
    dirs = get_model_directories()
    archive_dir = dirs['archive']
    production_dir = dirs['production']

    if not archive_dir.exists():
        return {
            'status': 'error',
            'message': 'No archive directory found'
        }

    pattern = f"{symbol}_{timeframe}_*_archived_*.pkl"
    archived_files = [
        f for f in archive_dir.glob(pattern)
        if not f.name.endswith("_calibration.pkl")
    ]

    if not archived_files:
        return {
            'status': 'error',
            'message': f'No archived models found for {symbol} {timeframe}'
        }

    latest_archive = max(archived_files, key=lambda p: p.stat().st_mtime)

    current_production = get_production_model_path(symbol, timeframe)
    if current_production:
        current_file = Path(current_production)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_name = current_file.stem + f"_replaced_{timestamp}" + current_file.suffix
        temp_path = archive_dir / temp_name
        shutil.move(str(current_file), str(temp_path))

        current_cal = current_file.parent / (current_file.stem + "_calibration.pkl")
        if current_cal.exists():
            temp_cal_name = current_file.stem + f"_replaced_{timestamp}_calibration.pkl"
            shutil.move(str(current_cal), str(archive_dir / temp_cal_name))

    restored_name = latest_archive.name.replace("_archived_", "_restored_")
    production_path = production_dir / restored_name
    shutil.copy(str(latest_archive), str(production_path))

    archived_cal = archive_dir / (latest_archive.stem + "_calibration.pkl")
    if archived_cal.exists():
        production_cal = production_dir / (production_path.stem + "_calibration.pkl")
        shutil.copy(str(archived_cal), str(production_cal))

    logger.info(f"Rolled back to archived model: {latest_archive.name}")

    return {
        'status': 'rolled_back',
        'production_path': str(production_path),
        'restored_from': str(latest_archive),
        'rolled_back_at': datetime.now().isoformat()
    }
