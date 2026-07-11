"""Unit tests for ExperimentAnalytics."""

import pytest
from ml_service.lab.experiments.analytics import calculate_experiment_analytics
from ml_service.lab.experiments.types import ExperimentContract


def test_empty_experiments():
    """Test analytics with empty list."""
    result = calculate_experiment_analytics([])

    assert result.total_experiments == 0
    assert result.completed_experiments == 0
    assert result.completion_rate == 0.0


def test_single_completed_experiment():
    """Test analytics with single completed experiment."""
    experiment = ExperimentContract(
        id=1,
        experiment_id="exp_001",
        run_id="run_001",
        status="COMPLETED",
        dataset_version="v1.0.0",
        feature_version="v1.0.0",
        model_version="v1.0.0",
        hyperparameters="{}",
        train_loss=0.5,
        validation_loss=0.6,
        started_at="2026-07-11T10:00:00",
        completed_at="2026-07-11T11:00:00",
        created_at="2026-07-11T10:00:00",
        updated_at="2026-07-11T11:00:00",
        notes=None
    )

    result = calculate_experiment_analytics([experiment])

    assert result.total_experiments == 1
    assert result.completed_experiments == 1
    assert result.completion_rate == 1.0
    assert result.avg_train_loss == 0.5
    assert result.avg_validation_loss == 0.6
    assert result.best_validation_loss_run_id == "run_001"


def test_multiple_experiments_mixed_status():
    """Test analytics with multiple experiments of different statuses."""
    experiments = [
        ExperimentContract(
            id=1,
            experiment_id="exp_001",
            run_id="run_001",
            status="COMPLETED",
            dataset_version="v1.0.0",
            feature_version="v1.0.0",
            model_version="v1.0.0",
            hyperparameters="{}",
            train_loss=0.5,
            validation_loss=0.6,
            started_at="2026-07-11T10:00:00",
            completed_at="2026-07-11T11:00:00",
            created_at="2026-07-11T10:00:00",
            updated_at="2026-07-11T11:00:00",
            notes=None
        ),
        ExperimentContract(
            id=2,
            experiment_id="exp_001",
            run_id="run_002",
            status="COMPLETED",
            dataset_version="v1.0.0",
            feature_version="v1.0.0",
            model_version="v1.0.0",
            hyperparameters="{}",
            train_loss=0.4,
            validation_loss=0.5,
            started_at="2026-07-11T12:00:00",
            completed_at="2026-07-11T13:00:00",
            created_at="2026-07-11T12:00:00",
            updated_at="2026-07-11T13:00:00",
            notes=None
        ),
        ExperimentContract(
            id=3,
            experiment_id="exp_001",
            run_id="run_003",
            status="FAILED",
            dataset_version="v1.0.0",
            feature_version="v1.0.0",
            model_version="v1.0.0",
            hyperparameters="{}",
            train_loss=None,
            validation_loss=None,
            started_at="2026-07-11T14:00:00",
            completed_at=None,
            created_at="2026-07-11T14:00:00",
            updated_at="2026-07-11T14:00:00",
            notes=None
        )
    ]

    result = calculate_experiment_analytics(experiments)

    assert result.total_experiments == 3
    assert result.completed_experiments == 2
    assert result.failed_experiments == 1
    assert result.completion_rate == 2 / 3
    assert result.failure_rate == 1 / 3
    assert result.avg_validation_loss == 0.55
    assert result.best_validation_loss_run_id == "run_002"
    assert result.worst_validation_loss_run_id == "run_001"


def test_experiments_with_training_status():
    """Test analytics counts training status correctly."""
    experiments = [
        ExperimentContract(
            id=1,
            experiment_id="exp_001",
            run_id="run_001",
            status="TRAINING",
            dataset_version="v1.0.0",
            feature_version="v1.0.0",
            model_version="v1.0.0",
            hyperparameters="{}",
            train_loss=None,
            validation_loss=None,
            started_at="2026-07-11T10:00:00",
            completed_at=None,
            created_at="2026-07-11T10:00:00",
            updated_at="2026-07-11T10:00:00",
            notes=None
        )
    ]

    result = calculate_experiment_analytics(experiments)

    assert result.total_experiments == 1
    assert result.training_experiments == 1
    assert result.completed_experiments == 0


def test_experiments_with_none_metrics():
    """Test analytics handles None metrics correctly."""
    experiments = [
        ExperimentContract(
            id=1,
            experiment_id="exp_001",
            run_id="run_001",
            status="COMPLETED",
            dataset_version="v1.0.0",
            feature_version="v1.0.0",
            model_version="v1.0.0",
            hyperparameters="{}",
            train_loss=None,
            validation_loss=None,
            started_at="2026-07-11T10:00:00",
            completed_at="2026-07-11T11:00:00",
            created_at="2026-07-11T10:00:00",
            updated_at="2026-07-11T11:00:00",
            notes=None
        )
    ]

    result = calculate_experiment_analytics(experiments)

    assert result.total_experiments == 1
    assert result.completed_experiments == 1
    assert result.avg_train_loss == 0.0
    assert result.avg_validation_loss == 0.0
    assert result.best_validation_loss_run_id == ""
