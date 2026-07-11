"""Unit tests for ExperimentRepository."""

import pytest
import sqlite3
from pathlib import Path
from ml_service.lab.experiments.repository import ExperimentRepository
from ml_service.lab.experiments.types import ExperimentContract


@pytest.fixture
def test_db(tmp_path):
    """Create a temporary test database with cleaned schema."""
    db_path = tmp_path / "test_experiments.db"
    conn = sqlite3.connect(str(db_path))

    # Create experiments table with cleaned schema (no coupled metrics)
    conn.execute("""
        CREATE TABLE experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id TEXT NOT NULL,
            run_id TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            dataset_version TEXT,
            feature_version TEXT,
            model_version TEXT,
            hyperparameters TEXT,
            train_loss REAL,
            validation_loss REAL,
            notes TEXT,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

    return str(db_path)


@pytest.fixture
def repository(test_db):
    """Create a repository instance with test database."""
    return ExperimentRepository(db_path=test_db)


@pytest.fixture
def sample_experiment():
    """Create a sample experiment contract with cleaned domain model."""
    return ExperimentContract(
        id=None,
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
        created_at=None,
        updated_at=None,
        notes=None
    )


def test_create_experiment(repository, sample_experiment):
    """Test creating an experiment."""
    experiment_id = repository.create(sample_experiment)

    assert experiment_id > 0

    retrieved = repository.get_by_id(experiment_id)
    assert retrieved is not None
    assert retrieved.experiment_id == "exp_test_001"
    assert retrieved.run_id == "run_abc123"
    assert retrieved.status == "CREATED"


def test_get_by_run_id(repository, sample_experiment):
    """Test retrieving experiment by run_id."""
    repository.create(sample_experiment)

    retrieved = repository.get_by_run_id("run_abc123")
    assert retrieved is not None
    assert retrieved.experiment_id == "exp_test_001"


def test_get_by_experiment_id(repository, sample_experiment):
    """Test retrieving all runs for an experiment."""
    repository.create(sample_experiment)

    sample_experiment2 = ExperimentContract(
        id=None,
        experiment_id="exp_test_001",
        run_id="run_def456",
        status="TRAINING",
        dataset_version="v1.0.0",
        feature_version="v1.1.0",
        model_version="v2.0.0",
        hyperparameters='{"learning_rate": 0.02}',
        train_loss=None,
        validation_loss=None,
        started_at="2026-07-11T11:00:00",
        completed_at=None,
        created_at=None,
        updated_at=None,
        notes=None
    )
    repository.create(sample_experiment2)

    runs = repository.get_by_experiment_id("exp_test_001")
    assert len(runs) == 2


def test_list_all(repository, sample_experiment):
    """Test listing all experiments with pagination."""
    repository.create(sample_experiment)

    experiments = repository.list_all(limit=10, offset=0)
    assert len(experiments) == 1


def test_list_by_status(repository, sample_experiment):
    """Test filtering experiments by status."""
    repository.create(sample_experiment)

    created_experiments = repository.list_by_status("CREATED")
    assert len(created_experiments) == 1

    training_experiments = repository.list_by_status("TRAINING")
    assert len(training_experiments) == 0


def test_update_status(repository, sample_experiment):
    """Test updating experiment status with flexible state machine."""
    repository.create(sample_experiment)

    success = repository.update_status("run_abc123", "TRAINING")
    assert success

    retrieved = repository.get_by_run_id("run_abc123")
    assert retrieved.status == "TRAINING"

    # Test flexible transitions
    success = repository.update_status("run_abc123", "VALIDATING")
    assert success

    retrieved = repository.get_by_run_id("run_abc123")
    assert retrieved.status == "VALIDATING"


def test_update_metrics(repository, sample_experiment):
    """Test updating training metrics only."""
    repository.create(sample_experiment)

    success = repository.update_metrics(
        run_id="run_abc123",
        train_loss=0.5,
        validation_loss=0.6
    )
    assert success

    retrieved = repository.get_by_run_id("run_abc123")
    assert retrieved.train_loss == 0.5
    assert retrieved.validation_loss == 0.6


def test_delete(repository, sample_experiment):
    """Test deleting an experiment."""
    repository.create(sample_experiment)

    success = repository.delete("run_abc123")
    assert success

    retrieved = repository.get_by_run_id("run_abc123")
    assert retrieved is None


def test_count_all(repository, sample_experiment):
    """Test counting all experiments."""
    repository.create(sample_experiment)

    count = repository.count_all()
    assert count == 1


def test_count_by_status(repository, sample_experiment):
    """Test counting experiments by status."""
    repository.create(sample_experiment)

    created_count = repository.count_by_status("CREATED")
    assert created_count == 1

    training_count = repository.count_by_status("TRAINING")
    assert training_count == 0


def test_transaction_support(test_db):
    """Test that repository can work with injected connection for transactions."""
    conn = sqlite3.connect(test_db)
    conn.row_factory = sqlite3.Row

    repo = ExperimentRepository(conn=conn)

    exp = ExperimentContract(
        id=None,
        experiment_id="exp_txn_001",
        run_id="run_txn_123",
        status="CREATED",
        dataset_version="v1.0.0",
        feature_version=None,
        model_version=None,
        hyperparameters=None,
        train_loss=None,
        validation_loss=None,
        started_at="2026-07-11T10:00:00",
        completed_at=None,
        created_at=None,
        updated_at=None,
        notes=None
    )

    # Should not auto-commit when using injected connection
    exp_id = repo.create(exp)
    assert exp_id > 0

    # Manual commit
    conn.commit()
    conn.close()

    # Verify it persisted
    repo2 = ExperimentRepository(db_path=test_db)
    retrieved = repo2.get_by_run_id("run_txn_123")
    assert retrieved is not None
