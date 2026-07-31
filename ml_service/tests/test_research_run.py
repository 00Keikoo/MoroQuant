import pytest
from dataclasses import FrozenInstanceError
from ml_service.research.models import ResearchRun
from ml_service.research.research_run import ResearchRunManager

def test_create_run():
    manager = ResearchRunManager()
    hyperparameters = {
        "learning_rate": 0.001,
        "batch_size": 64,
        "optimizer": {
            "type": "adamw",
            "weight_decay": 0.01
        }
    }
    
    run = manager.create_run(
        experiment_id="exp_001",
        hyperparameters=hyperparameters,
        run_id="run_001"
    )
    
    assert run.run_id == "run_001"
    assert run.experiment_id == "exp_001"
    assert run.status == "CREATED"
    assert run.metrics == ()
    assert run.model_binary_path is None
    assert run.created_at != ""
    assert run.completed_at is None
    
    # Retrieve and verify
    assert manager.exists("run_001") is True
    retrieved = manager.get_run("run_001")
    assert retrieved == run

def test_valid_lifecycle():
    manager = ResearchRunManager()
    run = manager.create_run(experiment_id="exp_001", hyperparameters={"lr": 0.01})
    run_id = run.run_id
    
    # CREATED -> RUNNING
    run = manager.start_run(run_id)
    assert run.status == "RUNNING"
    
    # RUNNING -> COMPLETED
    metrics = {"sharpe": 1.8, "drawdown": 0.12}
    run = manager.complete_run(
        run_id,
        metrics=metrics,
        model_binary_path="/storage/models/run_001.bin",
        completed_at="2026-07-31T21:00:00Z"
    )
    assert run.status == "COMPLETED"
    assert len(run.metrics) == 2
    assert dict(run.metrics) == {"sharpe": 1.8, "drawdown": 0.12}
    assert run.model_binary_path == "/storage/models/run_001.bin"
    assert run.completed_at == "2026-07-31T21:00:00Z"

def test_invalid_lifecycle():
    manager = ResearchRunManager()
    run = manager.create_run(experiment_id="exp_001", hyperparameters={"lr": 0.01})
    run_id = run.run_id
    
    # Cannot complete before starting
    with pytest.raises(ValueError):
        manager.complete_run(run_id)
        
    # Cannot fail before starting
    with pytest.raises(ValueError):
        manager.fail_run(run_id)
        
    # CREATED -> RUNNING
    manager.start_run(run_id)
    
    # Cannot start again
    with pytest.raises(ValueError):
        manager.start_run(run_id)
        
    # Transition to FAILED (RUNNING -> FAILED)
    manager.fail_run(run_id)
    
    # Cannot start, complete, or cancel a FAILED run
    with pytest.raises(ValueError):
        manager.start_run(run_id)
    with pytest.raises(ValueError):
        manager.complete_run(run_id)
    with pytest.raises(ValueError):
        manager.cancel_run(run_id)

def test_cancel_before_run():
    manager = ResearchRunManager()
    run = manager.create_run(experiment_id="exp_001", hyperparameters={"lr": 0.01})
    run_id = run.run_id
    
    # CREATED -> CANCELLED
    run = manager.cancel_run(run_id)
    assert run.status == "CANCELLED"
    assert run.completed_at is not None

def test_cancel_during_run():
    manager = ResearchRunManager()
    run = manager.create_run(experiment_id="exp_001", hyperparameters={"lr": 0.01})
    run_id = run.run_id
    
    # CREATED -> RUNNING -> CANCELLED
    manager.start_run(run_id)
    run = manager.cancel_run(run_id)
    assert run.status == "CANCELLED"
    assert run.completed_at is not None

def test_deterministic_ordering():
    manager = ResearchRunManager()
    hparams1 = {"lr": 0.01, "batch_size": 32, "epochs": 10}
    hparams2 = {"epochs": 10, "batch_size": 32, "lr": 0.01}
    
    run1 = manager.create_run(experiment_id="exp_1", hyperparameters=hparams1)
    run2 = manager.create_run(experiment_id="exp_1", hyperparameters=hparams2)
    
    # Hyperparameters should be sorted alphabetically by key and be identical
    assert run1.hyperparameters == run2.hyperparameters
    assert run1.to_dict()["hyperparameters"] == run2.to_dict()["hyperparameters"]
    
    # Check that list_runs returns them sorted by run_id
    runs = manager.list_runs()
    assert len(runs) == 2
    assert runs == sorted(runs, key=lambda r: r.run_id)

def test_immutability():
    manager = ResearchRunManager()
    run = manager.create_run(experiment_id="exp_001", hyperparameters={"lr": 0.01})
    
    with pytest.raises(FrozenInstanceError):
        run.status = "RUNNING"  # type: ignore

def test_metadata_propagation():
    manager = ResearchRunManager()
    run = manager.create_run(experiment_id="exp_abc", hyperparameters={"lr": 0.01}, run_id="run_xyz")
    assert run.experiment_id == "exp_abc"
    assert run.run_id == "run_xyz"
    
    run = manager.start_run(run.run_id)
    assert run.experiment_id == "exp_abc"
    assert run.run_id == "run_xyz"
    
    run = manager.complete_run(run.run_id, metrics={"sharpe": 2.0}, model_binary_path="/path/to/binary")
    assert run.experiment_id == "exp_abc"
    assert run.run_id == "run_xyz"
    assert dict(run.metrics) == {"sharpe": 2.0}
    assert run.model_binary_path == "/path/to/binary"

def test_empty_defaults():
    manager = ResearchRunManager()
    run = manager.create_run(experiment_id="exp_001")
    assert run.hyperparameters == ()
    assert run.metrics == ()
    assert run.model_binary_path is None

def test_exists_and_list_runs():
    manager = ResearchRunManager()
    assert manager.exists("non_existent") is False
    
    run1 = manager.create_run(experiment_id="exp_001", run_id="b_run")
    run2 = manager.create_run(experiment_id="exp_001", run_id="a_run")
    
    assert manager.exists("a_run") is True
    assert manager.exists("b_run") is True
    
    runs = manager.list_runs()
    assert len(runs) == 2
    assert runs[0].run_id == "a_run"
    assert runs[1].run_id == "b_run"
