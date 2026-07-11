"""Experiment Registry domain types.

Core experiment entity focused on identity, metadata, status, and relationships.
Performance metrics belong to their respective registries (Validation, Calibration, Models).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ExperimentContract:
    """Immutable experiment entity representing a single training run.

    Owns only core experiment concerns:
    - Identity (id, experiment_id, run_id)
    - Metadata (versions, hyperparameters)
    - Status (lifecycle state)
    - Timestamps (lifecycle events)

    Does NOT own:
    - Trading metrics (Sharpe, Sortino, etc.) - belongs to Model Registry
    - Calibration metrics (ECE, Brier) - belongs to Calibration Center
    - Validation metrics - belongs to Validation Center
    - Paper trading metrics - belongs to Paper Trading Registry
    """

    # Identity
    id: Optional[int]
    experiment_id: str
    run_id: str

    # Status
    status: str

    # Metadata - references to other registries
    dataset_version: Optional[str]
    feature_version: Optional[str]
    model_version: Optional[str]
    hyperparameters: Optional[str]

    # Loss metrics (training-specific, acceptable here)
    train_loss: Optional[float]
    validation_loss: Optional[float]

    # Timestamps
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

    # Optional: execution context metadata
    notes: Optional[str] = None
