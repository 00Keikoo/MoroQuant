import pytest
from dataclasses import FrozenInstanceError
from ml_service.research.models import ResearchExperiment, ResearchRun
from ml_service.research.research_experiment import ResearchExperimentManager

def test_experiment_creation():
    manager = ResearchExperimentManager()
    hypothesis_config = {
        "learning_rate": 0.01,
        "optimizer": "adam",
        "parameters": {
            "layers": [64, 32],
            "dropout": 0.2
        }
    }
    
    experiment = manager.create_experiment(
        session_id="sess_123",
        hypothesis_config=hypothesis_config,
        experiment_id="exp_999"
    )
    
    assert experiment.experiment_id == "exp_999"
    assert experiment.session_id == "sess_123"
    assert experiment.status == "INITIALIZED"
    assert experiment.runs == ()
    assert experiment.created_at != ""
    assert experiment.completed_at is None
    
    # Retrieve and verify
    retrieved = manager.get_experiment(experiment.experiment_id)
    assert retrieved == experiment

def test_valid_lifecycle_transitions():
    manager = ResearchExperimentManager()
    experiment = manager.create_experiment(session_id="sess_123", hypothesis_config={"lr": 0.1})
    experiment_id = experiment.experiment_id
    
    # INITIALIZED -> ACTIVE
    experiment = manager.start_experiment(experiment_id)
    assert experiment.status == "ACTIVE"
    
    # ACTIVE -> EVALUATED
    run = ResearchRun(run_id="run_1", experiment_id=experiment_id, status="COMPLETED")
    experiment = manager.complete_experiment(
        experiment_id,
        runs=(run,),
        completed_at="2026-07-31T14:00:00Z"
    )
    assert experiment.status == "EVALUATED"
    assert len(experiment.runs) == 1
    assert experiment.runs[0].run_id == "run_1"
    assert experiment.completed_at == "2026-07-31T14:00:00Z"

def test_invalid_lifecycle_transitions():
    manager = ResearchExperimentManager()
    experiment = manager.create_experiment(session_id="sess_123", hypothesis_config={"lr": 0.1})
    experiment_id = experiment.experiment_id
    
    # Cannot complete before starting
    with pytest.raises(ValueError):
        manager.complete_experiment(experiment_id)
        
    # Cannot fail before starting
    with pytest.raises(ValueError):
        manager.fail_experiment(experiment_id)
        
    # INITIALIZED -> ACTIVE
    manager.start_experiment(experiment_id)
    
    # Cannot start again
    with pytest.raises(ValueError):
        manager.start_experiment(experiment_id)
        
    # Fail the experiment (ACTIVE -> FAILED)
    manager.fail_experiment(experiment_id)
    
    # Cannot start or complete a FAILED experiment
    with pytest.raises(ValueError):
        manager.start_experiment(experiment_id)
    with pytest.raises(ValueError):
        manager.complete_experiment(experiment_id)

def test_experiment_cancellation_pre_run():
    manager = ResearchExperimentManager()
    experiment = manager.create_experiment(session_id="sess_123", hypothesis_config={"lr": 0.1})
    experiment_id = experiment.experiment_id
    
    # INITIALIZED -> CANCELLED
    experiment = manager.cancel_experiment(experiment_id)
    assert experiment.status == "CANCELLED"
    assert experiment.completed_at is not None

def test_experiment_cancellation_active():
    manager = ResearchExperimentManager()
    experiment = manager.create_experiment(session_id="sess_123", hypothesis_config={"lr": 0.1})
    experiment_id = experiment.experiment_id
    
    # INITIALIZED -> ACTIVE -> CANCELLED
    manager.start_experiment(experiment_id)
    experiment = manager.cancel_experiment(experiment_id)
    assert experiment.status == "CANCELLED"
    assert experiment.completed_at is not None

def test_deterministic_behavior():
    manager = ResearchExperimentManager()
    config1 = {
        "lr": 0.05,
        "batch_size": 32,
        "optimizer": "sgd"
    }
    config2 = {
        "optimizer": "sgd",
        "batch_size": 32,
        "lr": 0.05
    }
    
    exp1 = manager.create_experiment(session_id="sess_1", hypothesis_config=config1)
    exp2 = manager.create_experiment(session_id="sess_1", hypothesis_config=config2)
    
    # Hypothesis config snapshot should be sorted alphabetically by key and be identical
    assert exp1.hypothesis_config == exp2.hypothesis_config
    
    # With same fields, serialized dictionary or structures must be deterministic
    assert exp1.to_dict()["hypothesis_config"] == exp2.to_dict()["hypothesis_config"]

def test_immutability_preservation():
    manager = ResearchExperimentManager()
    experiment = manager.create_experiment(session_id="sess_123", hypothesis_config={"lr": 0.1})
    
    with pytest.raises(FrozenInstanceError):
        experiment.status = "ACTIVE"  # type: ignore

def test_metadata_propagation():
    manager = ResearchExperimentManager()
    experiment = manager.create_experiment(session_id="sess_abc", hypothesis_config={"lr": 0.1})
    assert experiment.session_id == "sess_abc"
    
    experiment = manager.start_experiment(experiment.experiment_id)
    assert experiment.session_id == "sess_abc"  # persists through transition
    
    run = ResearchRun(run_id="run_xyz", experiment_id=experiment.experiment_id, status="COMPLETED")
    experiment = manager.complete_experiment(
        experiment.experiment_id,
        runs=(run,),
        completed_at="2026-07-31T15:00:00Z"
    )
    assert experiment.session_id == "sess_abc"
    assert len(experiment.runs) == 1
    assert experiment.runs[0].run_id == "run_xyz"

def test_empty_default_values():
    manager = ResearchExperimentManager()
    experiment = manager.create_experiment(session_id="sess_123", hypothesis_config={})
    assert experiment.hypothesis_config == ()
    assert experiment.runs == ()
