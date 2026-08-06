import pytest
from dataclasses import FrozenInstanceError
from ml_service.research.experiment import ExperimentRun, DefaultExperimentTracker

def test_experiment_run_immutability():
    """Verify that ExperimentRun is strictly immutable."""
    run = ExperimentRun(
        experiment_id="exp-1",
        model_version_id="model-1",
        dataset_snapshot_id="ds-1",
        strategy_id="strat-1",
        feature_schema_version="1.0.0",
        evaluation_summary=(("sharpe", 2.1), ("drawdown", -0.15))
    )
    
    with pytest.raises(FrozenInstanceError):
        run.strategy_id = "strat-2"  # type: ignore
        
    with pytest.raises(FrozenInstanceError):
        run.evaluation_summary = (("sharpe", 2.5),)  # type: ignore

def test_deterministic_serialization():
    """Verify that serialization is deterministic regardless of initialization order of evaluation_summary."""
    run1 = ExperimentRun(
        experiment_id="exp-1",
        model_version_id="model-1",
        dataset_snapshot_id="ds-1",
        strategy_id="strat-1",
        feature_schema_version="1.0.0",
        evaluation_summary=(("sharpe", 2.1), ("drawdown", -0.15))
    )
    
    run2 = ExperimentRun(
        experiment_id="exp-1",
        model_version_id="model-1",
        dataset_snapshot_id="ds-1",
        strategy_id="strat-1",
        feature_schema_version="1.0.0",
        evaluation_summary=(("drawdown", -0.15), ("sharpe", 2.1))
    )
    
    assert run1.serialize() == run2.serialize()

def test_reproducible_experiment_identity():
    """Verify that reproducible identity keys (hashes) are generated deterministically."""
    run1 = ExperimentRun(
        experiment_id="exp-1",
        model_version_id="model-1",
        dataset_snapshot_id="ds-1",
        strategy_id="strat-1",
        feature_schema_version="1.0.0",
        evaluation_summary=(("sharpe", 2.1), ("drawdown", -0.15))
    )
    
    run2 = ExperimentRun(
        experiment_id="exp-1",
        model_version_id="model-1",
        dataset_snapshot_id="ds-1",
        strategy_id="strat-1",
        feature_schema_version="1.0.0",
        evaluation_summary=(("drawdown", -0.15), ("sharpe", 2.1))
    )
    
    run3 = ExperimentRun(
        experiment_id="exp-1",
        model_version_id="model-1",
        dataset_snapshot_id="ds-1",
        strategy_id="strat-1",
        feature_schema_version="1.0.0",
        evaluation_summary=(("sharpe", 2.2), ("drawdown", -0.15))
    )
    
    assert run1.get_identity() == run2.get_identity()
    assert run1.get_identity() != run3.get_identity()
    assert len(run1.get_identity()) == 64

def test_default_tracker_isolation_and_immutability():
    """Verify in-memory tracker isolation and tracking logic."""
    tracker1 = DefaultExperimentTracker()
    run = ExperimentRun(
        experiment_id="exp-1",
        model_version_id="model-1",
        dataset_snapshot_id="ds-1",
        strategy_id="strat-1",
        feature_schema_version="1.0.0",
        evaluation_summary=(("sharpe", 2.1),)
    )
    
    tracker1.log_run(run)
    assert tracker1.get_run("exp-1") == run
    
    # Ensure duplicates raise ValueError (immutability)
    with pytest.raises(ValueError, match="already been tracked"):
        tracker1.log_run(run)
        
    # Ensure isolation across tracker instances
    tracker2 = DefaultExperimentTracker()
    assert tracker2.get_run("exp-1") is None
    
    # Ensure sorting/list runs is deterministic
    run2 = ExperimentRun(
        experiment_id="exp-2",
        model_version_id="model-2",
        dataset_snapshot_id="ds-1",
        strategy_id="strat-1",
        feature_schema_version="1.0.0",
        evaluation_summary=(("sharpe", 1.8),)
    )
    tracker1.log_run(run2)
    runs = tracker1.list_runs()
    assert len(runs) == 2
    assert runs[0].experiment_id == "exp-1"
    assert runs[1].experiment_id == "exp-2"

def test_no_database_writes():
    """Verify that tracker is database-free (ADR-024 compliance)."""
    import inspect
    from ml_service.research.experiment import tracker
    
    source = inspect.getsource(tracker)
    assert "sqlite" not in source.lower()
    assert "db" not in source.lower()
    assert "insert" not in source.lower()
    assert "update" not in source.lower()
    assert "delete" not in source.lower()
