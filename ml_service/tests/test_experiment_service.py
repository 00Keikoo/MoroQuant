"""Unit tests for ExperimentService."""

import pytest
from unittest.mock import Mock
from ml_service.lab.experiments.service import ExperimentService
from ml_service.lab.experiments.types import ExperimentContract


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    return Mock()


@pytest.fixture
def service(mock_repository):
    """Create a service instance with mock repository."""
    return ExperimentService(repository=mock_repository)


@pytest.fixture
def sample_experiment():
    """Create a sample experiment contract with cleaned domain model."""
    return ExperimentContract(
        id=1,
        experiment_id="exp_test_001",
        run_id="run_abc123",
        status="CREATED",
        dataset_version="v1.0.0",
        feature_version="v1.1.0",
        model_version="v2.0.0",
        hyperparameters='{"learning_rate": 0.01}',
        train_loss=None,
        validation_loss=None,
        started_at="2026-07-11T10:00:00",
        completed_at=None,
        created_at="2026-07-11T10:00:00",
        updated_at="2026-07-11T10:00:00",
        notes=None
    )


def test_create_experiment(service, mock_repository, sample_experiment):
    """Test creating an experiment."""
    mock_repository.create.return_value = 1
    mock_repository.get_by_id.return_value = sample_experiment

    result = service.create_experiment(
        experiment_id="exp_test_001",
        dataset_version="v1.0.0",
        feature_version="v1.1.0",
        model_version="v2.0.0",
        hyperparameters='{"learning_rate": 0.01}'
    )

    assert result is not None
    assert result.experiment_id == "exp_test_001"
    mock_repository.create.assert_called_once()
    mock_repository.get_by_id.assert_called_once_with(1)


def test_start_training(service, mock_repository):
    """Test starting training phase."""
    mock_repository.update_status.return_value = True

    success = service.start_training("run_abc123")

    assert success
    mock_repository.update_status.assert_called_once_with("run_abc123", "TRAINING")


def test_transition_to(service, mock_repository):
    """Test flexible state transitions."""
    mock_repository.update_status.return_value = True

    success = service.transition_to("run_abc123", "VALIDATING")

    assert success
    mock_repository.update_status.assert_called_once_with("run_abc123", "VALIDATING")


def test_complete_training(service, mock_repository):
    """Test completing training with metrics."""
    mock_repository.update_metrics.return_value = True
    mock_repository.update_status.return_value = True

    success = service.complete_training(
        run_id="run_abc123",
        train_loss=0.5,
        validation_loss=0.6
    )

    assert success
    mock_repository.update_status.assert_called_once_with("run_abc123", "COMPLETED")


def test_fail_run(service, mock_repository):
    """Test failing a run."""
    mock_repository.update_status.return_value = True

    success = service.fail_run("run_abc123")

    assert success
    mock_repository.update_status.assert_called_once_with("run_abc123", "FAILED")


def test_update_training_metrics(service, mock_repository):
    """Test updating training metrics."""
    mock_repository.update_metrics.return_value = True

    success = service.update_training_metrics(
        run_id="run_abc123",
        train_loss=0.5,
        validation_loss=0.6
    )

    assert success
    mock_repository.update_metrics.assert_called_once()


def test_get_run(service, mock_repository, sample_experiment):
    """Test getting a run by run_id."""
    mock_repository.get_by_run_id.return_value = sample_experiment

    result = service.get_run("run_abc123")

    assert result is not None
    assert result.run_id == "run_abc123"
    mock_repository.get_by_run_id.assert_called_once_with("run_abc123")


def test_get_experiment_runs(service, mock_repository, sample_experiment):
    """Test getting all runs for an experiment."""
    mock_repository.get_by_experiment_id.return_value = [sample_experiment]

    results = service.get_experiment_runs("exp_test_001")

    assert len(results) == 1
    mock_repository.get_by_experiment_id.assert_called_once_with("exp_test_001")


def test_list_all_runs(service, mock_repository, sample_experiment):
    """Test listing all runs."""
    mock_repository.list_all.return_value = [sample_experiment]

    results = service.list_all_runs(limit=100, offset=0)

    assert len(results) == 1
    mock_repository.list_all.assert_called_once_with(limit=100, offset=0)


def test_list_by_status(service, mock_repository, sample_experiment):
    """Test listing runs by status."""
    mock_repository.list_by_status.return_value = [sample_experiment]

    results = service.list_by_status("CREATED")

    assert len(results) == 1
    mock_repository.list_by_status.assert_called_once_with("CREATED")


def test_delete_run(service, mock_repository):
    """Test deleting a run."""
    mock_repository.delete.return_value = True

    success = service.delete_run("run_abc123")

    assert success
    mock_repository.delete.assert_called_once_with("run_abc123")


def test_get_run_count(service, mock_repository):
    """Test getting run count."""
    mock_repository.count_all.return_value = 5

    count = service.get_run_count()

    assert count == 5
    mock_repository.count_all.assert_called_once()


def test_get_status_count(service, mock_repository):
    """Test getting status count."""
    mock_repository.count_by_status.return_value = 3

    count = service.get_status_count("COMPLETED")

    assert count == 3
    mock_repository.count_by_status.assert_called_once_with("COMPLETED")
