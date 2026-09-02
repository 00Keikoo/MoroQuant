"""
Provenance and Determinism

Canonical fingerprint computation for research pipeline stages.
Guarantees: same inputs + config + seed => same fingerprints.
"""

import hashlib
import json
from typing import Any, Dict


def compute_canonical_fingerprint(data: Dict[str, Any]) -> str:
    """
    Compute deterministic SHA256 fingerprint from canonical data.

    Args:
        data: Dictionary with sorted keys

    Returns:
        Hex-encoded SHA256 hash
    """
    serialized = json.dumps(data, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def dataset_fingerprint(
    dataset_version_id: str,
    snapshot_id: str,
    file_hash: str,
) -> str:
    """
    Compute canonical dataset fingerprint.

    Args:
        dataset_version_id: Dataset version identifier
        snapshot_id: Frozen snapshot identifier
        file_hash: SHA256 of dataset file content

    Returns:
        Deterministic dataset fingerprint
    """
    canonical = {
        "type": "dataset",
        "dataset_version_id": dataset_version_id,
        "snapshot_id": snapshot_id,
        "file_hash": file_hash,
    }
    return compute_canonical_fingerprint(canonical)


def feature_fingerprint(
    feature_dataset_id: str,
    source_dataset_fingerprint: str,
    transformation_config: Dict[str, Any],
) -> str:
    """
    Compute canonical feature fingerprint.

    Args:
        feature_dataset_id: Feature dataset identifier
        source_dataset_fingerprint: Fingerprint of source dataset
        transformation_config: Feature transformation configuration

    Returns:
        Deterministic feature fingerprint
    """
    canonical = {
        "type": "feature",
        "feature_dataset_id": feature_dataset_id,
        "source_dataset_fingerprint": source_dataset_fingerprint,
        "transformation_config": transformation_config,
    }
    return compute_canonical_fingerprint(canonical)


def replay_fingerprint(
    dataset_fingerprint: str,
    execution_config: Dict[str, Any],
    random_seed: int,
) -> str:
    """
    Compute canonical replay fingerprint.

    Args:
        dataset_fingerprint: Fingerprint of dataset used
        execution_config: Execution configuration (slippage, commission, etc)
        random_seed: Random seed for deterministic replay

    Returns:
        Deterministic replay fingerprint
    """
    canonical = {
        "type": "replay",
        "dataset_fingerprint": dataset_fingerprint,
        "execution_config": execution_config,
        "random_seed": random_seed,
    }
    return compute_canonical_fingerprint(canonical)


def experiment_fingerprint(
    replay_fingerprint: str,
    strategy_config: Dict[str, Any],
    model_config: Dict[str, Any],
    random_seed: int,
) -> str:
    """
    Compute canonical experiment fingerprint.

    Args:
        replay_fingerprint: Fingerprint of replay used
        strategy_config: Strategy configuration
        model_config: Model configuration
        random_seed: Random seed for experiment

    Returns:
        Deterministic experiment fingerprint
    """
    canonical = {
        "type": "experiment",
        "replay_fingerprint": replay_fingerprint,
        "strategy_config": strategy_config,
        "model_config": model_config,
        "random_seed": random_seed,
    }
    return compute_canonical_fingerprint(canonical)


def evaluation_fingerprint(
    experiment_fingerprint: str,
    metrics_config: Dict[str, Any],
) -> str:
    """
    Compute canonical evaluation fingerprint.

    Args:
        experiment_fingerprint: Fingerprint of experiment evaluated
        metrics_config: Metrics computation configuration

    Returns:
        Deterministic evaluation fingerprint
    """
    canonical = {
        "type": "evaluation",
        "experiment_fingerprint": experiment_fingerprint,
        "metrics_config": metrics_config,
    }
    return compute_canonical_fingerprint(canonical)


def model_fingerprint(
    dataset_fingerprint: str,
    feature_fingerprint: str,
    experiment_fingerprint: str,
    training_config: Dict[str, Any],
    random_seed: int,
) -> str:
    """
    Compute canonical model fingerprint.

    Args:
        dataset_fingerprint: Fingerprint of dataset used
        feature_fingerprint: Fingerprint of features used
        experiment_fingerprint: Fingerprint of experiment
        training_config: Training configuration
        random_seed: Random seed for training

    Returns:
        Deterministic model fingerprint
    """
    canonical = {
        "type": "model",
        "dataset_fingerprint": dataset_fingerprint,
        "feature_fingerprint": feature_fingerprint,
        "experiment_fingerprint": experiment_fingerprint,
        "training_config": training_config,
        "random_seed": random_seed,
    }
    return compute_canonical_fingerprint(canonical)
