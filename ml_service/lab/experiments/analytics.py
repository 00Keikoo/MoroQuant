"""Experiment analytics calculation engine.

Pure functions computing aggregate metrics from experiment domain objects.
Focus on core experiment lifecycle metrics only.

Note: Trading performance metrics (Sharpe, Sortino, etc.) belong in Model Registry.
Calibration metrics (ECE, Brier) belong in Calibration Center.
"""

from dataclasses import dataclass
from typing import List

from ml_service.lab.experiments.types import ExperimentContract


@dataclass
class ExperimentAnalyticsResult:
    """Calculated aggregate metrics for experiment lifecycle."""
    total_experiments: int
    completed_experiments: int
    failed_experiments: int
    training_experiments: int
    created_experiments: int
    completion_rate: float
    failure_rate: float
    avg_train_loss: float
    avg_validation_loss: float
    best_validation_loss_run_id: str
    worst_validation_loss_run_id: str


def calculate_experiment_analytics(experiments: List[ExperimentContract]) -> ExperimentAnalyticsResult:
    """Calculate aggregate analytics from experiment list.

    Pure function with no side effects. Only processes core experiment metrics.

    Args:
        experiments: List of ExperimentContract domain objects

    Returns:
        ExperimentAnalyticsResult containing calculated metrics
    """
    if not experiments:
        return _empty_result()

    total_experiments = len(experiments)
    completed = [e for e in experiments if e.status == 'COMPLETED']
    failed = [e for e in experiments if e.status == 'FAILED']
    training = [e for e in experiments if e.status == 'TRAINING']
    created = [e for e in experiments if e.status == 'CREATED']

    completed_count = len(completed)
    failed_count = len(failed)
    training_count = len(training)
    created_count = len(created)

    completion_rate = completed_count / total_experiments if total_experiments > 0 else 0.0
    failure_rate = failed_count / total_experiments if total_experiments > 0 else 0.0

    train_loss_values = [e.train_loss for e in completed if e.train_loss is not None]
    validation_loss_values = [e.validation_loss for e in completed if e.validation_loss is not None]

    avg_train_loss = sum(train_loss_values) / len(train_loss_values) if train_loss_values else 0.0
    avg_validation_loss = sum(validation_loss_values) / len(validation_loss_values) if validation_loss_values else 0.0

    best_val_loss_run_id = ""
    worst_val_loss_run_id = ""
    if validation_loss_values:
        experiments_with_val_loss = [e for e in completed if e.validation_loss is not None]
        best_exp = min(experiments_with_val_loss, key=lambda e: e.validation_loss)
        worst_exp = max(experiments_with_val_loss, key=lambda e: e.validation_loss)
        best_val_loss_run_id = best_exp.run_id
        worst_val_loss_run_id = worst_exp.run_id

    return ExperimentAnalyticsResult(
        total_experiments=total_experiments,
        completed_experiments=completed_count,
        failed_experiments=failed_count,
        training_experiments=training_count,
        created_experiments=created_count,
        completion_rate=completion_rate,
        failure_rate=failure_rate,
        avg_train_loss=avg_train_loss,
        avg_validation_loss=avg_validation_loss,
        best_validation_loss_run_id=best_val_loss_run_id,
        worst_validation_loss_run_id=worst_val_loss_run_id
    )


def _empty_result() -> ExperimentAnalyticsResult:
    """Return zero-initialized analytics result for empty experiment list."""
    return ExperimentAnalyticsResult(
        total_experiments=0,
        completed_experiments=0,
        failed_experiments=0,
        training_experiments=0,
        created_experiments=0,
        completion_rate=0.0,
        failure_rate=0.0,
        avg_train_loss=0.0,
        avg_validation_loss=0.0,
        best_validation_loss_run_id="",
        worst_validation_loss_run_id=""
    )
